# coop_website_scrapeer

Coop Web Scraper

Description
This project is a web scraper designed to extract product information from the Coop UK website. The scraper gathers details such as product name, URL, brand name, description, ingredients, suggested use, SKU, and price.

Features
- Scrapes product data from the Coop website.
- Outputs data to an Excel file with auto-width columns.
- Uses Selenium for web scraping and ChromeDriver for browser automation.

Important Note
To access the Coop website from outside the UK, it is necessary to use a VPN that connects to a UK server. Ensure that your VPN is active before running the scraper to avoid access issues. One thing you have to do is manual bot verification; no need to add postcode or anything.

Installation Prerequisites
- Python 3.x installed on your machine.
- Basic knowledge of running commands in the terminal.

Clone the Repository
Clone the repository to your local machine:

```bash
git clone https://github.com/shome/coop_rebuild
cd coop_rebuild
```

Install Dependencies
Install the required Python packages:

```bash
pip install -r requirements.txt
```

Creating the Executable
Install PyInstaller:

```bash
pip install pyinstaller
```

Build the executable:

```bash
pyinstaller --onefile --add-data "chromedriver.exe;." coop.py
```

Locate the executable in the `dist` folder.

Code Overview
The main functionality of the scraper is encapsulated in the `CoopScraper` class. Below is a detailed breakdown of its components:

### Class: CoopScraper
#### Initialization
- `__init__`: Initializes the scraper, setting up necessary variables, including lists for products and categories, and initializing the Chrome driver.

#### Methods
- `initialize_driver(self)`: Initializes the Chrome driver with specific options to avoid detection.
- `add_category(self, url)`: Adds a new category URL to the scraper if it's valid and not already included.
- `set_categories(self, url_list)`: Sets multiple category URLs at once, filtering for valid URLs.
- `scrape_category(self, category_url)`: Scrapes all products from a given category URL, handling pagination and product extraction.
- `scrape_all_categories(self)`: Iterates through all added categories and scrapes products from each.

### Scraping Process
The scraper navigates to category pages, scrolls to load all products, and extracts product details using BeautifulSoup. It handles pagination to ensure all products are captured.

### Error Handling
The scraper includes error handling for various exceptions, ensuring that it can gracefully handle issues such as missing elements or navigation errors.

### Output
The scraped product data can be saved to a CSV or Excel file, allowing for easy access and analysis.

