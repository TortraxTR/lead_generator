from OSM_scrape_AI_v2 import get_OSM_data
from GS_DS_async import get_data_from_Google
import pandas as pd
import time
import warnings

warnings.filterwarnings("ignore", category=ResourceWarning)

def main():
    startTime = time.time()
    print("Starting OSM data retrieval...")
    user_query = input("Enter your query here, e.g., 'clinics in Kocaeli': ")
    
    email_extraction_enabled = input("Do you want to enable email extraction? (y/n): ").strip().lower() == 'y'
    df = get_OSM_data(user_query)
    if df is not None:
        print("OSM data retrieval successful. Continuing with Google data retrieval...")
        google_data = get_data_from_Google(df, 12, 3, email_extraction_enabled)
        if google_data is not None:
            print("Google data retrieval successful. Saving results...")
            pd.DataFrame(google_data).to_excel(f"output_{user_query.replace(' ', '_')}.xlsx", index=False)
            print(f"Data saved to output_{user_query.replace(' ', '_')}.xlsx successfully.")

    endTime = time.time()
    print(f"Total time taken: {endTime - startTime:.2f} seconds.")

if __name__ == "__main__":
    main()
