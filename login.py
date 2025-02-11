import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from pathlib import Path

# Define user data directory for session persistence
USER_DIR = Path("user_data").absolute()
if not USER_DIR.exists():
    USER_DIR.mkdir()

profile = "marketplace"
CHROMEDRIVER_PATH = Path("chromedriver/chromedriver.exe").absolute()
SENT_MESSAGES_FILE = "sent_message.txt" # Define file for sent messages

def create_driver(profile_name):
    """Creates a WebDriver instance for a given profile name using absolute paths."""
    try:
        options = uc.ChromeOptions()
        profile_path = USER_DIR / profile_name
        options.add_argument(f"--user-data-dir={str(profile_path)}") # Use saved session
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--disable-gpu")
        # 🔽 Disable pop-up blocking 🔽
        options.add_argument("--disable-popup-blocking")

        driver = uc.Chrome(
            options=options,
            driver_executable_path=str(CHROMEDRIVER_PATH) # Use string format for path
        )
        driver.maximize_window()
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(e)
        return None

def manual_login_setup(profile_name):
    """Sets up the driver and allows the user to manually log in."""
    driver = create_driver(profile_name=profile_name)
    if driver is not None:
        print("Please log in manually in the opened browser window.")
        print("Once logged in, you can close the browser or leave it open.")
        print("After login, press Enter in the console to continue or just close the browser if only login is needed.")
        input("Press Enter to continue after login (or just close browser for login only)...")
        print("Login process completed or skipped.")
        return driver
    else:
        print("Failed to create driver instance for manual login.")
        return None

def check_if_there(listing_url, sent_message_urls): # Added sent_message_urls parameter
    index = listing_url.find("&tracking")
    if index != -1:
        listing_url = listing_url[:index]
    print(f"Checking if {listing_url} is in {sent_message_urls} {listing_url in sent_message_urls}")
    return listing_url in sent_message_urls

def marketplace_scraper(driver, product_name="used iphone", max_messages=5): # Added max_messages parameter
    """Scrapes Facebook Marketplace, messages sellers, with message limit and sent message tracking."""
    if driver is None:
        print("Driver is not initialized. Please ensure manual login setup is done correctly.")
        return

    sent_message_urls = set() # Initialize set to store sent message URLs
    try:
        with open(SENT_MESSAGES_FILE, "r") as f: # Read existing sent messages
            for line in f:
                sent_message_urls.add(line.strip())
        print(f"Loaded {len(sent_message_urls)} URLs from {SENT_MESSAGES_FILE}")
    except FileNotFoundError:
        print(f"{SENT_MESSAGES_FILE} not found, creating new file.")
        with open(SENT_MESSAGES_FILE, "w") as f: # Create new file
            pass # It's okay if the file doesn't exist yet

    messages_sent_count = 0 # Initialize message counter

    try:
        # Convert product name to URL-friendly format
        search_query = product_name.replace(" ", "%20")
        marketplace_url = f"https://www.facebook.com/marketplace/search/?query={search_query}"

        driver.get(marketplace_url)
        time.sleep(5)  # Wait for the page to load

        # # 🔹 Search for product
        # search_box = driver.find_element(By.XPATH, '//input[@placeholder="Search Marketplace"]')
        # search_box.send_keys(product_name) # Use product_name parameter here
        # search_box.send_keys(Keys.RETURN)

        # time.sleep(5)  # Wait for search results to load
        print("✅ Search completed!")

        # 🔹 Open listings -  STRUCTURE BASED FINDING (CONTAINING max-width and min-width in style)
        listings = driver.find_elements(By.XPATH, '//div[contains(@style, "max-width") and contains(@style, "min-width")]//a[contains(@href, "/marketplace/item/")]')
        print(f"Found {len(listings)} listings based on structure (containing max-width and min-width in style).") # Debug print
        if not listings:
            print("No listings found using structure-based XPath (containing max-width and min-width in style). Check HTML structure for changes.")
            return  # Exit if no listings found

        listings_to_process = [] # List to hold listings to process to ensure max_messages is respected

        for listing in listings:
            listing_url = listing.get_attribute("href")
            if not check_if_there(listing_url,sent_message_urls): # Check if already messaged
                listings_to_process.append(listing)
                if len(listings_to_process) >= max_messages: # Stop adding if max_messages reached for processing
                    break

        print(f"Processing {len(listings_to_process)} new listings (max {max_messages} messages).")

        for listing in listings_to_process:
            listing_url = listing.get_attribute("href")
            print("Processing listing:", listing_url)
            driver.execute_script("window.open(arguments[0]);", listing_url)
            time.sleep(5)

        # Switch to each tab and message the seller
        window_handles = driver.window_handles[1:] # Get handles of listing tabs
        for index, handle in enumerate(window_handles):
            if messages_sent_count >= max_messages: # Check message limit before processing each tab
                print(f"Reached max messages limit ({max_messages}). Stopping messaging process.")
                break

            driver.switch_to.window(handle)
            current_listing_url = driver.current_url # Get URL for tracking

            if current_listing_url in sent_message_urls: # Double check in case of race conditions
                print(f"Skipping already messaged URL: {current_listing_url}")
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                continue # Skip to the next listing

            try:
                # 1. Click "Send" button - Structure and aria-label based
                time.sleep(3)
                send_message_button = driver.find_element(By.XPATH, '//div[@aria-label="Send" and @role="button"]')
                print(send_message_button)
                if send_message_button:
                    print("Clicked 'Send' button on listing page.")
                    try:
                        driver.execute_script("arguments[0].click();", send_message_button)
                        # add the link to sent message txt
                    except Exception as e:
                        # print(e)
                        raise

                time.sleep(2) # Delay after clicking Send button

                # # 2. Wait for chat box to appear (Reusing existing chat box wait logic)
                # chat_box = WebDriverWait(driver, 10).until(
                #     EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Message']"))
                # )

                # # 3. Send an initial message (Reusing existing message sending logic)
                # chat_box.send_keys("Hi! I'm interested in your item. Is it still available? 😊")
                # chat_box.send_keys("\n")  # Simulate pressing Enter
                # print("Message sent successfully!")

                # ✅ Message sent successfully - Add URL to sent list and file
                sent_message_urls.add(current_listing_url[:current_listing_url.find("&tracking")])
                with open(SENT_MESSAGES_FILE, "a") as f:
                    f.write(current_listing_url + "\n")
                messages_sent_count += 1
                print(f"✅ Message sent to {current_listing_url}. Total messages sent: {messages_sent_count}/{max_messages}")


            except Exception as e:
                print(f"Error interacting with seller in listing tab for {current_listing_url}: {e}")
                raise e

            # Close the current tab and switch back
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print("Error during Marketplace search:", e)
        raise e
    finally:
        print(f"Marketplace scraping finished. Total messages sent: {messages_sent_count}/{max_messages}")


def main():
    """Main function to orchestrate user choice, manual login, and marketplace scraping."""

    while True: # Loop to allow user to choose again if needed
        print("\nChoose an option:")
        print("1. Manual Login Only")
        print("2. Marketplace Scraping (Assume already logged in)")
        print("3. Login then Scrape")
        print("4. Exit")

        choice = input("Enter your choice (1-4): ")

        if choice == '1':
            print("\n--- Manual Login Only ---")
            driver = manual_login_setup(profile_name=profile)
            if driver:
                input("Press Enter to exit after manual login setup...")
                driver.quit()
            else:
                print("Manual login setup failed.")
            break # Exit loop after this option

        elif choice == '2':
            max_message_count = int(input("Enter max messages to send for scraping: ")) # Get max messages from user
            print(f"\n--- Marketplace Scraping (Assuming Logged In) - Max Messages: {max_message_count} ---")
            driver = create_driver(profile_name=profile) # Create driver assuming logged in session
            if driver:
                marketplace_scraper(driver, max_messages=max_message_count) # Pass max_messages
                input("Press Enter to exit after scraping...")
                driver.quit()
            else:
                print("Failed to create driver for scraping (logged in session may not exist).")
            break # Exit loop after this option

        elif choice == '3':
            max_message_count = int(input("Enter max messages to send for login and scrape: ")) # Get max messages from user
            print(f"\n--- Login then Scrape - Max Messages: {max_message_count} ---")
            driver = manual_login_setup(profile_name=profile)
            if driver:
                marketplace_scraper(driver, max_messages=max_message_count) # Pass max_messages
                input("Press Enter to exit after login and scraping...")
                driver.quit()
            else:
                print("Login then scrape failed.")
            break # Exit loop after this option

        elif choice == '4':
            print("Exiting program.")
            break # Exit loop and program

        else:
            print("Invalid choice. Please enter a number between 1 and 4.")


if __name__ == "__main__":
    main()