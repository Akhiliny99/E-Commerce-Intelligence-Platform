"""
Static Scrapy Spider - books.toscrape.com
Legal practice site built for scraping education.
"""

import scrapy
import hashlib
import logging
from datetime import datetime
from scraper.items import ProductItem

logger = logging.getLogger(__name__)

RATING_MAP = {"One": 1.0, "Two": 2.0, "Three": 3.0, "Four": 4.0, "Five": 5.0}


class BooksSpider(scrapy.Spider):
    name = "books_spider"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, max_pages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages) if max_pages else None
        self.pages_scraped = 0
        self.items_count = 0

    def parse(self, response):
        self.pages_scraped += 1
        logger.info(f"[PAGE {self.pages_scraped}] Scraping: {response.url}")

        books = response.css("article.product_pod")
        if not books:
            books = response.css("li article")
        logger.info(f"  Found {len(books)} books on this page")

        for book in books:
            item = self._parse_book_listing(book, response)
            if item:
                self.items_count += 1
                detail_url = response.urljoin(book.css("h3 a::attr(href)").get())
                yield response.follow(
                    detail_url,
                    callback=self._parse_book_detail,
                    meta={"item": dict(item)},
                    errback=self._handle_error,
                )

        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            if self.max_pages and self.pages_scraped >= self.max_pages:
                logger.info(f"Reached max_pages limit: {self.max_pages}")
                return
            yield response.follow(next_page, callback=self.parse, errback=self._handle_error)
        else:
            logger.info(f"[DONE] Finished all pages. Total items: {self.items_count}")

    def _parse_book_listing(self, book, response):
        try:
            title = book.css("h3 a::attr(title)").get("").strip()
            price_text = book.css("p.price_color::text").get("0").strip()
            # Remove pound sign safely (handles Windows encoding)
            for char in ["£", "Â", "\xa3"]:
                price_text = price_text.replace(char, "")
            price_text = price_text.replace(",", "").strip()
            try:
                price = float(price_text)
            except ValueError:
                price = 0.0

            rating_word = book.css("p.star-rating::attr(class)").get("").split()[-1]
            rating = RATING_MAP.get(rating_word, 0.0)
            availability = " ".join(book.css("p.availability::text").getall()).strip()
            full_url = response.urljoin(book.css("h3 a::attr(href)").get(""))
            image_url = response.urljoin(book.css("img::attr(src)").get(""))
            product_id = hashlib.md5(full_url.encode()).hexdigest()[:16]

            item = ProductItem()
            item["product_id"] = product_id
            item["title"] = title
            item["url"] = full_url
            item["source"] = "books.toscrape.com"
            item["price"] = price
            item["original_price"] = price
            item["discount_pct"] = 0.0
            item["rating"] = rating
            item["review_count"] = 0
            item["availability"] = availability
            item["image_url"] = image_url
            item["scraped_at"] = datetime.utcnow().isoformat()
            return item
        except Exception as e:
            logger.error(f"Error parsing book listing: {e}")
            return None

    def _parse_book_detail(self, response):
        item = response.meta["item"]
        try:
            breadcrumbs = response.css("ul.breadcrumb li a::text").getall()
            item["category"] = breadcrumbs[-1].strip() if len(breadcrumbs) >= 2 else "Unknown"
            review_text = response.css("table.table tr:last-child td::text").get("0")
            try:
                item["review_count"] = int(review_text.strip())
            except (ValueError, AttributeError):
                item["review_count"] = 0
            logger.info(f"  Scraped: {item['title'][:50]} | price={item['price']} | {item['category']}")
            yield item
        except Exception as e:
            logger.error(f"Error parsing detail page: {e}")
            yield item

    def _handle_error(self, failure):
        logger.error(f"Request failed: {failure.request.url}")