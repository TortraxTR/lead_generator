import math
from OSM_scrape_AI_v2 import get_OSM_data_AI
from GS_DS_async import get_data_from_Google
from OSM_scrape_noAI import get_OSM_data_noAI
from googletrans import Translator
import pandas as pd
import time

def main():
    startTime = time.time()
    translator = Translator()
    print("Starting OSM data retrieval...")
    if (input("Would you like to use AI? (requires local Ollama with gemma3n:e2b) y/n: ") == "y"):
        user_query = input("Enter your query here, e.g., 'clinics in Kocaeli': ")
        translated_query = translator.translate(user_query, dest="en")
        print(f"The translated query that will be passed to the AI is: {translated_query.text}")
        df = get_OSM_data_AI(user_query)
    else:
        area = input("Enter area, e.g., 'Kocaeli': ")
        category = input("Enter category here, e.g., 'pharmacy': ")
        df = get_OSM_data_noAI(area, category)

    if df is not None:
        print("OSM data retrieval successful. Continuing with Google data retrieval...")
        # The second number is for the number of browsers that are open at the same time.
        # Since proxy changing isn't implemented yet I'm leaving it as is, but it'll be more time-efficient for 
        # low-numbered queries if they are all processed within the same browser.
        google_data = get_data_from_Google(df, math.ceil(len(df)/4), 4)
        if google_data is not None:
            print("Google data retrieval successful. Saving results...")
            today = pd.Timestamp.now().strftime("%Y-%m-%d")
            pd.DataFrame(google_data).to_excel(f"output_files/output_{user_query.replace(' ', '_')}_{today}.xlsx", index=False)
            print(f"Data saved to output_files/output_{user_query.replace(' ', '_')}_{today}.xlsx successfully.")

    endTime = time.time()
    print(f"Total time taken: {endTime - startTime:.2f} seconds.")

if __name__ == "__main__":
    main()
