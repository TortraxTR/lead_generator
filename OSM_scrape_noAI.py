import overpass
import pandas as pd

def getOverpassQL(area, category):
    overpassQL_prompt = f"""area[name="{area}"]->.a; (node(area.a)["amenity"="{category}"];)"""
    return overpassQL_prompt

def get_OSM_data_noAI(area, category):
    overpass_query = getOverpassQL(area=area, category=category)
    
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