import overpass
import pandas as pd
import requests
import json
import warnings

url = "http://localhost:11434/api/generate"

headers = {
    "content-type": "application/json",
}

prompt = f"""
    You are an AI assistant that translates user input into valid Overpass QL queries.
    Your task is to find the tags that the user is trying to search for in Overpass and return the wanted search query in a format that can be utilized in making Overpass API calls.

    1) Translate the user's input into English (i.e., `İstanbul eczane` would be translated into `pharmacy in İstanbul`).
    2) Identify the tags that the user is trying to search for. (i.e., for `clinics in Kocaeli` the tags would be "clinic" and "Kocaeli".) DO NOT invent tags.
    3) Identify the type of tag that the user is searching for. (i.e., `İstanbul` is an area tag in OpenStreetMap with the value `[name="İstanbul"]`.)
    4) Identify the matching OpenStreetMap node tag that the user is trying to search for. (i.e., `clinics` can be `["amenity" = "clinic"]`.)
    5) Use the format `area[name="İstanbul"]->.a; (node(area.a)["amenity"="clinic"];)`. Do not alter the positions of the semicolons and do not add any punctuation marks.
    6) ONLY return the Overpass QL code without any additional text or comments.
    7) Do not add your own comments or explanations to the output.

    Examples:
    Input: `clinics in Kocaeli`
    Output: `area[name="Kocaeli"]->.a; (node(area.a)["amenity"="clinic"];)`

    Input: `hospitals in Istanbul`
    Output: `area[name="İstanbul"]->.a; (node(area.a)["amenity"="hospital"];)`

    """

def getOverpassQL(query):
    try:
        data = {
        "model": "gemma3n:e4b",
        "prompt": prompt + f"""User Query: '{query}'""",
        "stream": False,
        "temperature": 0.2,
        }
        
        response = requests.post(url=url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            result = response.text
            data = json.loads(result)
            print(f"Gemma API Response: {data['response']}")
            actual_response = data["response"].replace("`", "").replace("ql", "").replace("?", "").replace("])", "];)") #güvenlik için, gereksiz olabilir
            print(f"Overpass QL Query: {actual_response}")
            return actual_response
        else:
            raise Exception("Error in Gemma API response.")
        
    except Exception as e:
        print(f"Error in getOverpassQL: {e}")
        return None

def get_OSM_data(user_query):
    warnings.filterwarnings("ignore", category=ResourceWarning)
    overpass_query = getOverpassQL(user_query)
    api = overpass.API(timeout=60) # Increase timeout for potentially larger queries
    print("Executing Overpass query...")
    try:
        response = api.get(overpass_query).get("features")
        print("Query executed. Processing results...")
        organizations = []

        for element in response:
            coords = element.get("geometry")
            props = element.get("properties")
            if props.get("name") is not None:
                org_data = {
                    "name": props.get("name", "N/A"),
                    "amenity": props.get("amenity", "N/A"),
                    "lat": coords.get("coordinates")[1],
                    "lon": coords.get("coordinates")[0]
                }
                organizations.append(org_data)

        print(f"Found {len(organizations)} potential organizations.")
        #file_name = f"output_{user_query.replace(' ', '_')}.xlsx"
        df = pd.DataFrame(organizations)
        #df.to_excel(file_name, index=False)
        #print(f"Data saved to {file_name} successfully.")
        return df

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please check your Overpass QL query and ensure you have an active internet connection.")
        return None