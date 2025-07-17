import requests
import json

url = "http://localhost:11434/api/generate"

headers = {
    "content-type": "application/json",
}

def main():

    user_query = input("Enter your query here, e.g., 'clinics in Kocaeli': ")
    if not user_query:
        print("No query provided. Exiting.")
        return
    data = {
    "model": "llama3.1:8b",
    "prompt": 
        """Convert the following user query into an OverpassAPI query.
            Rules:
            1. Use ONLY valid OpenStreetMap tags (e.g., 'vegan' → 'diet:vegan=yes').
            2. Always include an area filter (e.g., 'area["name"="Berlin"]').
            3. Always put the area filter before the node tags.
            4. Always use the format 'area[name="Kocaeli"]->.a; (node(area.a)["amenity"="clinic"]; );' for the query's structure.
            5. Remove any additional text other than the output, including your own additions. """ + f" Query: '{user_query}'",
    "stream": False,
    "temperature": 0.4,
    }
       
    response = requests.post(url=url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        result = response.text
        data = json.loads(result)
        actual_response = data["response"]

        print("Generated Overpass QL query:")
        print(actual_response)
    else:
        print("Error:", response.status_code, response.text)

if __name__ == "__main__":
    main()
    