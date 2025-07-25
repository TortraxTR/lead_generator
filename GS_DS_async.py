import asyncio
from playwright.async_api import async_playwright
import time
import warnings

# Global storage for Playwright instances
playwright = None
browsers = {}

async def get_browser_instance(worker_id):
    global playwright, browsers
    
    if playwright is None:
        playwright = await async_playwright().start()
    
    if worker_id not in browsers:
        browsers[worker_id] = await playwright.chromium.launch(headless=True)
    
    return browsers[worker_id]

async def close_browser_instances():
    global playwright, browsers
    
    for browser in browsers.values():
        await browser.close()
    browsers.clear()
    
    if playwright is not None:
        await playwright.stop()
        playwright = None

async def search_places_near_coordinates(query, latitude, longitude, worker_id):
    search_time = time.time()
    try:
        browser = await get_browser_instance(worker_id)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 640, "height": 360}
        )
        
        page = await context.new_page()
        search_url = f"https://www.google.com/maps/search/\"{query}\"/@{latitude},{longitude},15z"
        await page.goto(search_url, timeout=60000)
        await asyncio.sleep(2)  # Wait for the search results to appear

        try:
            # Accept cookies if the popup appears
            accept_button = page.get_by_role("button", name="Accept all", exact=False)
            if await accept_button.is_visible():
                await accept_button.click()
                await asyncio.sleep(2)
      
            name_attribute = 'h1.DUwDvf'
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[contains(@data-item-id, "authority")]'
                
                # Click on the first link matching the locator
            links = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]')
            if await links.count() > 0:
                card = links.first
                await card.click()
                await page.wait_for_timeout(2000)
                
            name = await page.locator(name_attribute).inner_text()
            address = await page.locator(address_xpath).inner_text()
            phone_number = await page.locator(phone_number_xpath).inner_text() if await page.locator(phone_number_xpath).count() > 0 else None
            
            # Try to get website URL
            website_url = None
            if await page.locator(website_xpath).count() > 0:
                website_url = await page.locator(website_xpath).get_attribute('href')
                
            result = {
                'name': name.strip() if name else None,
                'address': address.strip() if address else None,
                'phone_number': phone_number.strip() if phone_number else None,
                'website': website_url if website_url else None,
                'coordinates': f"{latitude},{longitude}"
            }

            await context.close()
                
            print(f"Search for {query} completed in {time.time() - search_time:.2f} seconds.") 
                
            return result
            
        except Exception as e:
                print(f"Error processing card for {query}: {e}")
                return None
            
        except Exception as e:
            print(f"Error during search for {query}: {e}")
            return None
        


    except Exception as e:
        print(f"Browser error for {query}: {e}")
        return None

async def process_batch_async(rows, max_workers):
    places = []
    
    # Create tasks for each row
    tasks = []
    for i, row in enumerate(rows):
        worker_id = i % max_workers  # Distribute workers evenly
        tasks.append(
            search_places_near_coordinates(
                row.name, row.lat, row.lon, 
                worker_id
            )
        )
    
    # Run all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    for result in results:
        if result and not isinstance(result, Exception):
            places.append(result)
    
    return places

async def get_data_from_Google_async(df, batch_size, max_workers):
    warnings.filterwarnings("ignore", category=ResourceWarning)
    try:
        all_places = []
        
        for i in range(0, len(df), batch_size):
            batch_time = time.time()
            batch = df.iloc[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(df)-1)//batch_size + 1}")
            
            batch_results = await process_batch_async(
                batch.itertuples(), 
                max_workers=max_workers
            )
            
            all_places.extend(batch_results)
            print(f"Batch {i//batch_size + 1} processed in {time.time() - batch_time:.2f} seconds")
        
        if all_places:
            return all_places
        else:
            print("No results found or an error occurred.")
            
    finally:
        pass

# Wrapper function to run the async code from synchronous context
def get_data_from_Google(df, batch_size, max_workers):
    loop = asyncio.get_event_loop()
    try:
        return loop.run_until_complete(get_data_from_Google_async(df, batch_size, max_workers))
    finally:
        loop.run_until_complete(close_browser_instances())
        loop.close()