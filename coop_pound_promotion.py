import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import csv
import os
import json
import requests
from selenium.common.exceptions import TimeoutException
from colorama import init, Fore, Back, Style
import sys
import pandas as pd
import urllib.parse
import tkinter as tk
from tkinter import filedialog

class CoopScraper:
    def __init__(self):
        init()  # Initialize colorama
        self.products = []
        self.categories = []  # Start with empty list
        self.driver = None  # Initialize driver as None
        self.saved_files = []  # Add this to track saved files
        self.save_dir = None  # Initialize save directory

    def initialize_driver(self):
        """Initialize the Chrome driver when needed"""
        options = uc.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        self.driver = uc.Chrome(options=options)

    def add_category(self, url):
        """Add a new category URL to scrape"""
        if self.is_valid_coop_url(url) and url not in self.categories:
            self.categories.append(url)
            print(f"Added new category URL: {url}")

    def set_categories(self, url_list):
        """Set multiple category URLs at once"""
        valid_urls = [url for url in url_list if self.is_valid_coop_url(url)]
        self.categories = valid_urls
        print(f"Updated category list with {len(valid_urls)} URLs")

    def scrape_category(self, category_url):
        # Attempt to extract category name from the page
        try:
            print(f"Navigating to category URL: {category_url}")
            self.driver.get(category_url)
            time.sleep(5)

            # New code to extract category name from the specified HTML structure
            category_name_elem = self.driver.find_element(By.CSS_SELECTOR, "div.mb-5 h1[data-component='H1']")
            self.current_category = category_name_elem.text.strip()
            print(f"\nScraping category: {self.current_category}")
        except Exception as e:
            print(f"Error extracting category name from page: {e}")
            
            # Fallback to extract category name from URL
            try:
                url_parts = category_url.split('/')[-1]
                category_with_id = url_parts.split('--')[0]
                self.current_category = category_with_id.replace('-', ' ').strip()
                print(f"Using category name from URL: {self.current_category}")
            except Exception as url_error:
                print(f"Error extracting category name from URL: {url_error}")
                self.current_category = "unknown"
        
        all_products = []
        page = 1
        
        try:
            # Navigate to category page
            print(f"Navigating to category URL: {category_url}")
            self.driver.get(category_url)
            time.sleep(5)
            
            # Scroll to load all products
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            while True:  # Continue until no more pages
                print(f"\nProcessing page {page}")
                
                # Wait for products to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='product-card-vertical']"))
                    )
                except Exception as e:
                    print(f"Error waiting for products: {e}")
                    break
                
                # Parse the page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                product_cards = soup.find_all('div', {'data-testid': 'product-card-vertical'})
                
                if not product_cards:
                    print("No products found. Ending pagination.")
                    break
                    
                print(f"Found {len(product_cards)} products on page {page}")
                
                # Process products
                for card in product_cards:
                    product = self.parse_product_card(card)
                    if product:
                        # Navigate to the product page to get additional info
                        product_url = product['product_url']  # Ensure you have the product URL
                        print(f"Navigating to product URL: {product_url}")
                        self.driver.get(product_url)
                        time.sleep(5)  # Wait for the product page to load
                        
                        # Call the method to scrape additional product info
                        pound_promotion = self.scrape_product_page()  # Get the pound promotion
                        
                        # Add pound promotion to the product dictionary
                        product['pound_promotion'] = pound_promotion
                        
                        all_products.append(product)
                        print(f"Added product: {product['title']}")
                
                # Try to go to next page
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 
                            "a.ais-Pagination-link[aria-label='Next Page']"))
                    )
                    
                    # Scroll the button into view before clicking
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    
                    # Try JavaScript click first
                    try:
                        self.driver.execute_script("arguments[0].click();", next_button)
                    except:
                        next_button.click()
                        
                    print(f"Moving to page {page + 1}")
                    time.sleep(3)  # Increased wait time after page change
                    page += 1
                    
                except Exception as e:
                    print(f"Could not find next page button: {e}")
                    print("Reached last page")
                    break
            
            print(f"\nFinished scraping category {self.current_category}. Total products: {len(all_products)}")
            return all_products
            
        except Exception as e:
            print(f"Error scraping category {self.current_category}: {e}")
            return all_products

    def scrape_all_categories(self):
        print("\nStarting to scrape all categories...")
        
        all_products = []  # Initialize a list to accumulate all products
        
        try:
            if not self.driver:
                print("\nInitializing Chrome driver...")
                self.initialize_driver()

            print("\nNavigating to main page...")
            self.driver.get("https://shop.coop.co.uk")
            time.sleep(5)
            
            try:
                print(Fore.RED + "\n⚠ Please complete the robot verification when you see it..." + Style.RESET_ALL)
                print(Fore.YELLOW + "⌛ Waiting for verification to be completed..." + Style.RESET_ALL)
                
                # Wait for verification to complete (checking every 2 seconds)
                while True:
                    if "Incapsula" not in self.driver.page_source and self.driver.find_elements(By.ID, "postcode"):
                        print(Fore.GREEN + "\n✓ Verification completed! Continuing automatically..." + Style.RESET_ALL)
                        time.sleep(2)
                        
                        # Automatically handle everything after verification
                        try:
                            # Direct postcode entry using JavaScript
                            js_code = """
                            let input = document.querySelector('#postcode');
                            if (input) {
                                input.value = 'B30 1LL';
                                input.dispatchEvent(new Event('change'));
                                document.querySelector('button[type="submit"]').click();
                                return true;
                            }
                            return false;
                            """
                            
                            if not self.driver.execute_script(js_code):
                                # Fallback to Selenium if JavaScript fails
                                postcode_input = WebDriverWait(self.driver, 5).until(
                                    EC.presence_of_element_located((By.ID, "postcode"))
                                )
                                postcode_input.send_keys("B30 1LL")
                                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                                submit_button.click()
                            
                            print(Fore.GREEN + "✓ Postcode entered automatically" + Style.RESET_ALL)
                            time.sleep(3)
                        except Exception as e:
                            print(f"Error during postcode entry: {e}")
                        break
                    time.sleep(2)
                
                # Track progress
                total_categories = len(self.categories)
                for index, category_url in enumerate(self.categories, 1):
                    print(f"\n{'='*50}")
                    print(f"Processing category {index} of {total_categories}")
                    print(f"URL: {category_url}")
                    print('='*50)
                    
                    products = self.scrape_category(category_url)
                    all_products.extend(products)  # Accumulate products
                    time.sleep(3)  # Brief pause between categories
                
                # After all categories are scraped, save all products
                if all_products:
                    self.save_to_csv(all_products, folder_path=self.save_dir)  # Save all products at once
                
                # After all categories are scraped, print summary
                print("\n" + "="*50)
                print("SCRAPING SUMMARY")
                print("="*50)
                for file_info in self.saved_files:
                    print(f"\nCategory: {file_info['category']}")
                    print(f"Products: {file_info['products']}")
                    print(f"Saved to: {file_info['filepath']}")
                print("\n" + "="*50)
                
            except Exception as e:
                print(f"Error during process: {e}")
                return

        finally:
            self.close()

    def parse_product_card(self, card):
        try:
            # Product Code (from data-product-id attribute)
            product_code = card.get('data-product-id', '')
            
            # Product Title and URL
            title_elem = card.select_one('h2 a, h3 a')
            title = title_elem.text.strip() if title_elem else ''
            product_url = 'https://shop.coop.co.uk' + title_elem['href'] if title_elem and 'href' in title_elem.attrs else ''
            
            # Regular Price - simplified selector
            price = ''
            price_elem = card.select_one('p.self-center.text-base.font-semibold')
            if not price_elem:
                # Try alternative price selector
                price_elem = card.select_one('[data-testid="product-price"]')
            if price_elem:
                price = price_elem.text.strip()
            
            # Price per unit
            price_per_unit = ''
            price_per_unit_elem = card.select_one('p.text-xs.text-text-alternative')
            if price_per_unit_elem:
                price_per_unit = price_per_unit_elem.text.strip()
            
            # Member Price - default to "No"
            member_price = 'No'
            member_price_elem = card.select_one('[data-testid="member-price"]')
            if not member_price_elem:
                member_price_elem = card.select_one('.text-member-deal-blue')
            if member_price_elem:
                member_text = member_price_elem.text.strip()
                if member_text:
                    member_price = member_text
            
            # Promotions - default all to "No"
            promotions = card.select('ul[aria-label="Product deals"] li span, .text-deal-red')
            
            pound_promotion = 'No'
            only_promotion = 'No'
            buy_any_x = 'No'
            
            for promo in promotions:
                promo_text = promo.text.strip()
                if promo_text:
                    if '£' in promo_text:
                        pound_promotion = promo_text
                    elif 'Buy any' in promo_text or 'Mix & Match' in promo_text:
                        buy_any_x = promo_text
                    else:
                        only_promotion = promo_text
            
            # Stock Status - updated selector
            stock = 'In Stock'  # default to in stock
            
            # Check for out of stock text
            out_of_stock_elem = card.select_one('p.text-lg.font-semibold')
            if out_of_stock_elem and 'Out of stock' in out_of_stock_elem.text:
                stock = 'Out of Stock'
            
            # Alternative out of stock check
            if not out_of_stock_elem:
                out_of_stock_div = card.select_one('div.flex.min-h-11.items-center')
                if out_of_stock_div and 'Out of stock' in out_of_stock_div.text:
                    stock = 'Out of Stock'
            
            # Category info
            category = self.current_category.replace('_', ' ').title()
            category_url = f"https://shop.coop.co.uk/category/{self.current_category}--17"
            
            # Print debug info
            print(f"\nProduct: {title}")
            print(f"Price: {price}")
            print(f"Price per unit: {price_per_unit}")
            print(f"Member Price: {member_price}")
            print(f"Promotions: {pound_promotion} | {only_promotion} | {buy_any_x}")
            print(f"Stock: {stock}")
            
            return {
                'product_code': product_code,
                'title': title,
                'price': price,
                'price_per_unit': price_per_unit,
                'member_price': member_price,
                'pound_promotion': pound_promotion,
                'only_promotion': only_promotion,
                'buy_any_x': buy_any_x,
                'stock': stock,
                'category': category,
                'category_url': category_url,
                'product_url': product_url
            }
            
        except Exception as e:
            print(f"Error parsing product card: {e}")
            return None

    def scrape_product_page(self):
        """Scrape additional information from the product page"""
        try:
            # Wait for the product details to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p.text-deal-red"))
            )
            
            # Extract pound promotion
            pound_promotion_elem = self.driver.find_element(By.CSS_SELECTOR, "p.text-deal-red")
            pound_promotion = pound_promotion_elem.text.strip() if pound_promotion_elem else 'No'
            
            print(f"Pound Promotion: {pound_promotion}")
            
            return pound_promotion  # Return the pound promotion value
            
        except Exception as e:
            print(f"An error occurred while scraping the product page: {e}")
            return 'No'  # Return 'No' if there was an error

    def scrape_all_pages(self):
        all_products = []
        page = 1
        category_url = "https://shop.coop.co.uk/category/chilled-beer-and-wine--465"
        
        try:
            print("\nNavigating to main page...")
            self.driver.get("https://shop.coop.co.uk")
            time.sleep(5)
            
            try:
                print("\nPlease complete the robot verification when you see it...")
                print("The script will automatically continue once verification is complete...")
                
                # Wait for verification to complete (checking every 2 seconds)
                while True:
                    if "Incapsula" not in self.driver.page_source and self.driver.find_elements(By.ID, "postcode"):
                        print("\nVerification completed! Continuing automatically...")
                        time.sleep(2)
                        break
                    time.sleep(2)
                
                # Immediately try to enter postcode
                try:
                    # Direct postcode entry using JavaScript
                    js_code = """
                    let input = document.querySelector('#postcode');
                    if (input) {
                        input.value = 'B30 1LL';
                        input.dispatchEvent(new Event('change'));
                        document.querySelector('button[type="submit"]').click();
                        return true;
                    }
                    return false;
                    """
                    
                    if not self.driver.execute_script(js_code):
                        # Fallback to Selenium if JavaScript fails
                        postcode_input = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, "postcode"))
                        )
                        postcode_input.send_keys("B30 1LL")
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                        submit_button.click()
                    
                    print("Postcode entered automatically")
                    time.sleep(3)
                    
                    # Navigate directly to category page
                    print("\nNavigating to category page...")
                    self.driver.get(category_url)
                    time.sleep(5)
                    
                    # Scroll to load all products
                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    while True:
                        # Scroll down
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        
                        # Calculate new scroll height
                        new_height = self.driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            break
                        last_height = new_height
                    
                    while True:  # Continue until no more pages
                        print(f"\nProcessing page {page}")
                        
                        # Wait for products to load
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='product-card-vertical']"))
                            )
                        except Exception as e:
                            print(f"Error waiting for products: {e}")
                            break
                        
                        # Parse the page
                        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        product_cards = soup.find_all('div', {'data-testid': 'product-card-vertical'})
                        
                        if not product_cards:
                            print("No products found. Ending pagination.")
                            break
                             
                        print(f"Found {len(product_cards)} products on page {page}")
                        
                        # Process products
                        for card in product_cards:
                            product = self.parse_product_card(card)
                            if product:
                                all_products.append(product)
                                print(f"Added product: {product['title']}")
                        
                        # Try to go to next page
                        try:
                            next_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                                    "a.ais-Pagination-link[aria-label='Next Page']"))
                            )
                             
                            # Scroll the button into view before clicking
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                            time.sleep(1)
                             
                            # Try JavaScript click first
                            try:
                                self.driver.execute_script("arguments[0].click();", next_button)
                            except:
                                next_button.click()
                                 
                            print(f"Moving to page {page + 1}")
                            time.sleep(3)  # Increased wait time after page change
                            page += 1
                             
                        except Exception as e:
                            print(f"Could not find next page button: {e}")
                            print("Reached last page or no more products")
                            break
                    
                    print(f"\nFinished scraping. Total products: {len(all_products)}")
                    return all_products
                    
                except Exception as e:
                    print(f"Error during scraping: {e}")
                    return all_products

            except Exception as e:
                print(f"Error during process: {e}")
                return

        except Exception as e:
            print(f"Error during scraping: {e}")
            return all_products

    def save_to_csv(self, products, folder_path=None, filename=None):
        if not products:
            print("No products to save")
            return
        
        # Generate filename from category if not provided
        if filename is None:
            filename = f"coop_all_products_{time.strftime('%Y%m%d')}.xlsx"  # Default filename for all products
        elif not filename.endswith('.xlsx'):
            filename = filename.rsplit('.', 1)[0] + '.xlsx'

        # Ensure the folder path is provided
        if folder_path is None:
            print("No folder path provided. Please select a folder to save the file.")
            return

        # Create the full file path
        filepath = os.path.join(folder_path, filename)

        # Check if the file already exists and modify the filename if necessary
        base, extension = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(filepath):
            filepath = f"{base}_{counter}{extension}"
            counter += 1

        try:
            # Convert to DataFrame and save as Excel
            df = pd.DataFrame(products)

            # Apply formatting
            writer = pd.ExcelWriter(filepath, engine='openpyxl')
            df.to_excel(writer, index=False, sheet_name='Products')

            # Get the workbook and the worksheet
            workbook = writer.book
            worksheet = writer.sheets['Products']

            # Auto-adjust columns width
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

            # Add filters to headers
            worksheet.auto_filter.ref = worksheet.dimensions

            # Save the file
            writer.close()

            print(f"\nSuccessfully saved {len(products)} products to: {filepath}")
            self.saved_files.append({
                'category': self.current_category,
                'products': len(products),
                'filepath': filepath
            })
            return True

        except Exception as e:
            print(f"Error saving file: {str(e)}")

            # Emergency save with timestamp
            try:
                emergency_filename = f"coop_products_{int(time.time())}.xlsx"
                emergency_path = os.path.join(folder_path, emergency_filename)

                # Convert to DataFrame and save as Excel
                df = pd.DataFrame(products)
                df.to_excel(emergency_path, index=False, sheet_name='Products')

                print(f"\nEmergency save successful: {emergency_path}")
                return True
            except Exception as e:
                print(f"Emergency save failed: {str(e)}")
                return False

    def close(self):
        if self.driver:
            self.driver.quit()

    def is_valid_coop_url(self, url):
        """
        Validate if the URL is a valid Co-op shop URL.
        
        Args:
            url (str): The URL to validate
        
        Returns:
            bool: True if the URL is valid, False otherwise
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            # Check domain and scheme
            return (
                parsed_url.scheme in ['http', 'https'] and 
                parsed_url.netloc.endswith('shop.coop.co.uk') and
                parsed_url.path  # Ensure there's a path component
            )
        except Exception:
            return False

    def read_urls_from_file(self, file_path):
        """
        Read URLs from a text file and add them to categories.
        
        Args:
            file_path (str): Path to the .txt file containing URLs
        
        Returns:
            int: Number of valid URLs added
        """
        try:
            # Validate file exists and is a .txt file
            if not os.path.exists(file_path):
                print(f"{Fore.RED}Error: File {file_path} does not exist.{Style.RESET_ALL}")
                return 0
            
            if not file_path.lower().endswith('.txt'):
                print(f"{Fore.RED}Error: File must be a .txt file.{Style.RESET_ALL}")
                return 0
            
            # Read URLs from file
            with open(file_path, 'r') as f:
                urls = f.read().splitlines()
            
            # Filter and add valid URLs
            valid_urls = [url.strip() for url in urls if self.is_valid_coop_url(url.strip())]
            
            # Add valid URLs to categories
            self.set_categories(valid_urls)
            
            print(f"{Fore.GREEN}Successfully read {len(valid_urls)} URLs from {file_path}{Style.RESET_ALL}")
            
            # Prompt user to select a folder to save scraped files
            print(Fore.CYAN + "\n╔══ Select Folder to Save Scraped Files ══╗" + Style.RESET_ALL)
            from tkinter import Tk, filedialog
            Tk().withdraw()  # We don't want a full GUI, so keep the root window from appearing
            folder_selected = filedialog.askdirectory(title="Select Folder to Save Scraped Files")
            if folder_selected:
                print(Fore.GREEN + f"\n✓ Folder selected: {folder_selected}" + Style.RESET_ALL)
                self.save_dir = folder_selected
            else:
                print(Fore.RED + "\n✗ No folder selected. Files will not be saved." + Style.RESET_ALL)
            
            return len(valid_urls)
        
        except Exception as e:
            print(f"{Fore.RED}Error reading URLs from file: {e}{Style.RESET_ALL}")
            return 0

if __name__ == "__main__":
    scraper = CoopScraper()
    
    while True:
        print("\n" + "="*50)
        print(Fore.CYAN + """
    ╔══════════════════════════════════╗
    ║        CO-OP WEB SCRAPER         ║
    ╚══════════════════════════════════╝
    """ + Style.RESET_ALL)
        
        print(Fore.YELLOW + """
    [1] """ + Fore.WHITE + """Add Single URL
    """ + Fore.YELLOW + """[2] """ + Fore.WHITE + """Add Multiple URLs
    """ + Fore.YELLOW + """[3] """ + Fore.WHITE + """Read URLs from File
    """ + Fore.YELLOW + """[4] """ + Fore.WHITE + """Start Scraping
    """ + Fore.YELLOW + """[5] """ + Fore.WHITE + """Exit Program
        """)
        print(Fore.CYAN + "="*50 + Style.RESET_ALL)
        
        choice = input(Fore.GREEN + "\nEnter your choice (1-5): " + Style.RESET_ALL)
        
        if choice == "1":
            print(Fore.CYAN + "\n╔══ URL Input ══╗" + Style.RESET_ALL)
            url = input("\nEnter the Co-op category URL to scrape:\n➜ ")
            if scraper.is_valid_coop_url(url):
                scraper.add_category(url)
                print(Fore.GREEN + "\n✓ URL added successfully!" + Style.RESET_ALL)
                print(Fore.YELLOW + "\n⚡ Initializing Chrome..." + Style.RESET_ALL)
                scraper.initialize_driver()
                print(Fore.BLUE + "\n➜ Navigating to main page..." + Style.RESET_ALL)
                scraper.driver.get("https://shop.coop.co.uk")
                print(Fore.CYAN + "\n╔══ Select Folder to Save Scraped Files ══╗" + Style.RESET_ALL)
                from tkinter import Tk, filedialog
                Tk().withdraw()  # We don't want a full GUI, so keep the root window from appearing
                folder_selected = filedialog.askdirectory(title="Select Folder to Save Scraped Files")
                if folder_selected:
                    print(Fore.GREEN + f"\n✓ Folder selected: {folder_selected}" + Style.RESET_ALL)
                    scraper.save_dir = folder_selected
                else:
                    print(Fore.RED + "\n✗ No folder selected. Files will not be saved." + Style.RESET_ALL)
                print(Fore.RED + "\n⚠ Please complete the robot verification when you see it..." + Style.RESET_ALL)
                print(Fore.YELLOW + "⌛ The script will automatically continue once verification is complete..." + Style.RESET_ALL)
                break
            else:
                print(Fore.RED + "\n✗ Invalid URL! Please enter a valid Co-op URL" + Style.RESET_ALL)
                
        elif choice == "2":
            print(Fore.CYAN + "\n╔══ Multiple URL Input ══╗" + Style.RESET_ALL)
            urls = input("\nEnter the Co-op category URLs to scrape (comma-separated):\n➜ ").split(",")
            valid_urls = [url.strip() for url in urls if scraper.is_valid_coop_url(url.strip())]
            if valid_urls:
                scraper.set_categories(valid_urls)
                print(Fore.GREEN + "\n✓ URLs added successfully!" + Style.RESET_ALL)
                print(Fore.YELLOW + "\n⚡ Initializing Chrome..." + Style.RESET_ALL)
                scraper.initialize_driver()
                print(Fore.BLUE + "\n➜ Navigating to main page..." + Style.RESET_ALL)
                scraper.driver.get("https://shop.coop.co.uk")
                print(Fore.CYAN + "\n╔══ Select Folder to Save Scraped Files ══╗" + Style.RESET_ALL)
                from tkinter import Tk, filedialog
                Tk().withdraw()  # We don't want a full GUI, so keep the root window from appearing
                folder_selected = filedialog.askdirectory(title="Select Folder to Save Scraped Files")
                if folder_selected:
                    print(Fore.GREEN + f"\n✓ Folder selected: {folder_selected}" + Style.RESET_ALL)
                    scraper.save_dir = folder_selected
                else:
                    print(Fore.RED + "\n✗ No folder selected. Files will not be saved." + Style.RESET_ALL)
                print(Fore.RED + "\n⚠ Please complete the robot verification when you see it..." + Style.RESET_ALL)
                print(Fore.YELLOW + "⌛ The script will automatically continue once verification is complete..." + Style.RESET_ALL)
                break
            
        elif choice == "3":
            print(Fore.CYAN + "\n╔══ Read URLs from File ══╗" + Style.RESET_ALL)
            try:
                root = tk.Tk()
                root.attributes('-topmost', True)  # Ensure window is on top
                root.withdraw()  # Hide the main window
                file_path = filedialog.askopenfilename(
                    title="Select a .txt file containing URLs", 
                    filetypes=[("Text Files", "*.txt")],
                    initialdir=os.path.expanduser('~\\Documents')  # Start in Documents folder
                )
                root.destroy()  # Explicitly destroy the Tkinter root window
                
                if file_path:
                    print(f"{Fore.GREEN}Selected file: {file_path}{Style.RESET_ALL}")
                    # Only proceed if URLs are successfully read
                    if scraper.read_urls_from_file(file_path) > 0:
                        input(Fore.YELLOW + "\nPress Enter to start scraping..." + Style.RESET_ALL)
                        print(Fore.YELLOW + "\n⚡ Initializing Chrome..." + Style.RESET_ALL)
                        scraper.initialize_driver()
                        print(Fore.BLUE + "\n➜ Navigating to main page..." + Style.RESET_ALL)
                        scraper.driver.get("https://shop.coop.co.uk")
                        print(Fore.RED + "\n⚠ Please complete the robot verification when you see it..." + Style.RESET_ALL)
                        print(Fore.YELLOW + "⌛ The script will automatically continue once verification is complete..." + Style.RESET_ALL)
                        break
                    else:
                        input(Fore.RED + "\nPress Enter to continue..." + Style.RESET_ALL)
                else:
                    print(Fore.YELLOW + "\nNo file selected." + Style.RESET_ALL)
                    input(Fore.RED + "Press Enter to continue..." + Style.RESET_ALL)
            except Exception as e:
                print(f"{Fore.RED}Error opening file dialog: {e}{Style.RESET_ALL}")
                input(Fore.RED + "Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == "4":
            if not scraper.categories:
                print(Fore.RED + "\n✗ No URLs added! Please add URLs before scraping." + Style.RESET_ALL)
                continue
            print(Fore.YELLOW + "\n⚡ Starting to scrape..." + Style.RESET_ALL)
            scraper.scrape_all_categories()
            break
            
        elif choice == "5":
            print(Fore.RED + "\n👋 Exiting..." + Style.RESET_ALL)
            if scraper.driver:
                scraper.close()
            time.sleep(1)
            break
            
        else:
            print(Fore.RED + "\n✗ Invalid choice! Please enter 1-5" + Style.RESET_ALL)

    # After getting URLs, continue with verification and scraping
    if scraper.categories and scraper.driver:
        # Wait for verification to complete
        while True:
            if "Incapsula" not in scraper.driver.page_source and scraper.driver.find_elements(By.ID, "postcode"):
                print(Fore.GREEN + "\n✓ Verification completed! Continuing automatically..." + Style.RESET_ALL)
                time.sleep(2)
                break
            time.sleep(2)
        
        # Start scraping process
        scraper.scrape_all_categories()
