"""
Selenium Dynamic Spider - quotes.toscrape.com/js/
Handles JavaScript-rendered pages that Scrapy alone cannot scrape.
Uses headless Chrome with rotating user agents.
"""

import hashlib
import logging
import random
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]


def get_chrome_driver(headless: bool = True) -> webdriver.Chrome:
    """Initialize headless Chrome - forces win64 driver on Windows."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")

    # Force win64 driver to fix [WinError 193] on Windows
    driver_path = ChromeDriverManager().install()

    # Fix: webdriver-manager sometimes returns wrong path pointing to THIRD_PARTY_NOTICES
    # Get the actual chromedriver.exe path
    import os
    driver_dir = os.path.dirname(driver_path)
    for f in os.listdir(driver_dir):
        if f.lower() == "chromedriver.exe" or f.lower() == "chromedriver":
            driver_path = os.path.join(driver_dir, f)
            break

    logger.info(f"Using ChromeDriver at: {driver_path}")
    # Ensure chromedriver is executable (fixes permissions error on Linux/Docker)
    import stat
    os.chmod(driver_path, os.stat(driver_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    # Mask selenium detection
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


class DynamicProductScraper:
    """
    Selenium scraper for JavaScript-rendered e-commerce pages.
    Target: quotes.toscrape.com/js/ (legal JS scraping practice site)
    """

    BASE_URL = "https://quotes.toscrape.com/js/"
    SOURCE = "quotes.toscrape.com"

    def __init__(self, max_pages: int = 5, headless: bool = True):
        self.max_pages = max_pages
        self.headless = headless
        self.driver = None
        self.scraped_items = []

    def __enter__(self):
        logger.info("Starting Selenium Chrome driver...")
        self.driver = get_chrome_driver(self.headless)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver closed.")

    def scrape(self) -> list:
        logger.info(f"Starting dynamic scrape: {self.BASE_URL}")
        url = self.BASE_URL
        page = 1

        while url and page <= self.max_pages:
            logger.info(f"[PAGE {page}] Scraping JS page: {url}")
            items = self._scrape_page(url)
            self.scraped_items.extend(items)
            logger.info(f"  Got {len(items)} items (total: {len(self.scraped_items)})")

            url = self._get_next_page_url()
            page += 1

            delay = random.uniform(2, 4)
            logger.info(f"  Waiting {delay:.1f}s before next page...")
            time.sleep(delay)

        logger.info(f"Dynamic scrape complete. Total items: {len(self.scraped_items)}")
        return self.scraped_items

    def _scrape_page(self, url: str) -> list:
        items = []
        try:
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "quote")))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            quotes = self.driver.find_elements(By.CLASS_NAME, "quote")
            logger.info(f"  Found {len(quotes)} items on page")

            for quote in quotes:
                item = self._parse_quote_as_product(quote, url)
                if item:
                    items.append(item)

        except TimeoutException:
            logger.error(f"Timeout waiting for JS content at {url}")
        except Exception as e:
            logger.error(f"Error scraping page {url}: {e}")

        return items

    def _parse_quote_as_product(self, element, page_url: str):
        try:
            text = element.find_element(By.CLASS_NAME, "text").text.strip()
            author = element.find_element(By.CLASS_NAME, "author").text.strip()
            tags = [t.text for t in element.find_elements(By.CLASS_NAME, "tag")]

            simulated_price = round(random.uniform(5.0, 500.0), 2)
            simulated_rating = round(random.uniform(3.0, 5.0), 1)
            simulated_reviews = random.randint(10, 5000)

            product_id = hashlib.md5(f"{author}_{text[:30]}".encode()).hexdigest()[:16]

            return {
                "product_id": product_id,
                "title": f"{text[:80]} - {author}"[:200],
                "category": tags[0] if tags else "Uncategorized",
                "url": page_url,
                "source": self.SOURCE,
                "image_url": "",
                "price": simulated_price,
                "original_price": round(simulated_price * random.uniform(1.0, 1.5), 2),
                "discount_pct": round(random.uniform(0, 30), 2),
                "rating": simulated_rating,
                "review_count": simulated_reviews,
                "availability": random.choice(["In Stock", "In Stock", "In Stock", "Low Stock", "Out of Stock"]),
                "scraped_at": datetime.utcnow().isoformat(),
            }

        except NoSuchElementException as e:
            logger.warning(f"Missing element: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing item: {e}")
            return None

    def _get_next_page_url(self):
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "li.next a")
            return next_btn.get_attribute("href")
        except NoSuchElementException:
            return None


def run_dynamic_scraper(max_pages: int = 5) -> list:
    with DynamicProductScraper(max_pages=max_pages, headless=True) as scraper:
        return scraper.scrape()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    items = run_dynamic_scraper(max_pages=3)
    print(f"\nScraped {len(items)} items")
    for item in items[:3]:
        print(f"  - {item['title'][:60]} | ${item['price']} | {item['rating']}")