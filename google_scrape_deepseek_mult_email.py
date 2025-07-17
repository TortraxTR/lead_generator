from playwright.sync_api import sync_playwright
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import re

# Thread-local storage for Playwright instances
thread_local = threading.local()

def get_browser_instance():
    if not hasattr(thread_local, "browser"):
        p = sync_playwright().start()
        thread_local.playwright = p
        thread_local.browser = p.chromium.launch(headless=True)
    return thread_local.browser

def close_browser_instances():
    if hasattr(thread_local, "browser"):
        thread_local.browser.close()
    if hasattr(thread_local, "playwright"):
        thread_local.playwright.stop()

def extract_email(text):
    """Helper function to extract email addresses from text"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    return matches[0] if matches else None

def search_places_near_coordinates(query, latitude, longitude, email_extraction_enabled, review_extraction_enabled):
    search_time = time.time()
    try:
        browser = get_browser_instance()
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        page = context.new_page()
        search_url = f"https://www.google.com/maps/search/\"{query}\"/@{latitude},{longitude},15z"
        page.goto(search_url, timeout=60000)
        time.sleep(3)  # Wait for the search results to appear

        try:
            # Accept cookies if the popup appears
            accept_button = page.get_by_role("button", name="Accept all", exact=False)
            if accept_button.is_visible():
                accept_button.click()
                time.sleep(2)
      
            try:  
                name_attribute = 'h1.DUwDvf'
                address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                website_xpath = '//a[contains(@data-item-id, "authority")]'
                
                if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() > 1:
                    card = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').first
                    card.click()
                    page.wait_for_timeout(2000)
                
                name = page.locator(name_attribute).inner_text()
                address = page.locator(address_xpath).inner_text()
                phone_number = page.locator(phone_number_xpath).inner_text() if page.locator(phone_number_xpath).count() > 0 else None
                
                # Try to get website URL
                website_url = None
                if page.locator(website_xpath).count() > 0:
                    website_url = page.locator(website_xpath).get_attribute('href')
                
                if email_extraction_enabled:
                    # Attempt to extract email from the card
                    email = None
                    page_content = page.content()
                    email = extract_email(page_content)
                    
                    # If we have a website but no email, try visiting the website to find email
                    if website_url and not email:
                        try:
                            # Open new tab for website
                            with context.expect_page() as new_page_info:
                                page.locator(website_xpath).click()
                            new_page = new_page_info.value
                            new_page.wait_for_load_state()
                            time.sleep(3)  # Wait for website to load

                            # Try to find email on website
                            website_content = new_page.content()
                            email = extract_email(website_content)
                            new_page.close()
                        except Exception as e:
                            print(f"Error visiting website for email extraction: {e}")
                
                result = {
                    'name': name.strip() if name else None,
                    'address': address.strip() if address else None,
                    'phone_number': phone_number.strip() if phone_number else None,
                    'website': website_url if website_url else None,
                    'coordinates': f"{latitude},{longitude}"
                }
                if email_extraction_enabled:
                    result['email'] = email if email else None
                print(f"Search for {query} completed in {time.time() - search_time:.2f} seconds.") 
                
                return result
            
            except Exception as e:
                print(f"Error processing card for {query}: {e}")
                return None
            
        except Exception as e:
            print(f"Error during search for {query}: {e}")
            return None
        
        finally:
            context.close()

        

    except Exception as e:
        print(f"Browser error for {query}: {e}")
        return None

def process_batch(rows, max_workers, email_extraction_enabled, review_extraction_enabled):
    places = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for row in rows:
            futures.append(executor.submit(
            search_places_near_coordinates,
            row.name, row.lat, row.lon, email_extraction_enabled, review_extraction_enabled
            ))
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    places.append(result)
            except Exception as e:
                print(f"Error in future: {e}")
    
    return places

def get_data_from_Google(df, batch_size, max_workers, email_extraction_enabled):
    try:
        # Process in batches (you can adjust batch size based on memory constraints)
        all_places = []
        
        for i in range(0, len(df), batch_size):
            batch_time = time.time()
            batch = df.iloc[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(df)-1)//batch_size + 1}")
            batch_results = process_batch(batch.itertuples(), max_workers=max_workers, email_extraction_enabled=email_extraction_enabled)
            all_places.extend(batch_results)
            print(f"Batch {i//batch_size + 1} processed in {time.time() - batch_time:.2f} seconds")
        # Save final combined results
        if all_places:
            return all_places
        else:
            print("No results found or an error occurred.")
            
    finally:
        # Clean up browser instances
        close_browser_instances()