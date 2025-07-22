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
    You are an Overpass QL query generator. Your sole purpose is to convert user requests into valid Overpass QL code.

    Follow these steps precisely:

    1.  **Identify Location & Amenity:** Determine the **location** (e.g., "Kocaeli", "İstanbul") and the **amenity** (e.g., "clinic", "hospital", "pharmacy") the user is asking for.
    2.  **Map to OpenStreetMap Tags:**
        * **Location:** Map the identified location to `area[name="LOCATION_NAME"]`. Ensure the location name is capitalized correctly if it's a proper noun. For example, "Istanbul" becomes `İstanbul`.
        * **Amenity:** Map the identified amenity to its corresponding OpenStreetMap key-value pair.
            * "clinics" -> `["amenity"="clinic"]`
            * "hospitals" -> `["amenity"="hospital"]`
            * "pharmacy" / "eczaneler" -> `["amenity"="pharmacy"]`
            * DO NOT invent new tags. Only use exact matches.
    3.  **Construct Overpass QL:** Combine these into the exact format: `area[name="LOCATION_NAME"]->.a; (node(area.a)["AMENITY_TAG"];)`
        * Maintain the semicolons and parentheses exactly as shown.
        * Do not add any other punctuation.

    **Output Rules:**
    * **ONLY** output the Overpass QL code.
    * **NO** extra text, explanations, comments, or conversational filler.

    ---

    **Examples:**

    * **Input:** `clinics in Kocaeli`
    * **Output:** `area[name="Kocaeli"]->.a; (node(area.a)["amenity"="clinic"];)`

    * **Input:** `hospitals in Istanbul`
    * **Output:** `area[name="İstanbul"]->.a; (node(area.a)["amenity"="hospital"];)`

    * **Input:** `İstanbul eczane`
    * **Output:** `area[name="İstanbul"]->.a; (node(area.a)["amenity"="pharmacy"];)`
    """

def getOverpassQL(query):
    try:
        data = {
        "model": "gemma3n:e2b",
        "prompt": prompt + f"""User Query: '{query}'""",
        "stream": False,
        "temperature": 0.1,
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

def get_OSM_data_AI(user_query):
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