"""
Spider Orchestrator
Runs both Scrapy (static) and Selenium (dynamic) spiders,
then triggers the price monitor.
"""

import logging
import os
import sys
from datetime import datetime

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Fix Windows emoji encoding issue
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/scraper.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

os.makedirs("logs", exist_ok=True)
os.makedirs("output", exist_ok=True)


def run_scrapy_spiders():
    logger.info("=" * 60)
    logger.info("SCRAPY SPIDERS STARTING")
    logger.info("=" * 60)

    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "scraper.settings")
    settings = get_project_settings()
    settings.setmodule("scraper.settings")

    process = CrawlerProcess(settings)
    process.crawl("books_spider", max_pages=5)
    process.start()
    logger.info("Scrapy spiders finished")


def run_selenium_spiders():
    logger.info("=" * 60)
    logger.info("SELENIUM SPIDER STARTING")
    logger.info("=" * 60)

    try:
        from scraper.spiders.dynamic_spider import run_dynamic_scraper
        from database.models import Product, PriceHistory, get_session

        items = run_dynamic_scraper(max_pages=3)
        logger.info(f"  Selenium scraped {len(items)} items - saving to DB...")

        session = get_session()
        saved = 0
        for item in items:
            try:
                existing = session.query(Product).filter_by(product_id=item["product_id"]).first()
                if not existing:
                    product = Product(
                        product_id=item["product_id"],
                        title=item["title"],
                        category=item.get("category", "Uncategorized"),
                        url=item.get("url", ""),
                        source=item.get("source", "selenium"),
                        image_url=item.get("image_url", ""),
                    )
                    session.add(product)

                ph = PriceHistory(
                    product_id=item["product_id"],
                    price=item.get("price"),
                    original_price=item.get("original_price"),
                    discount_pct=item.get("discount_pct", 0),
                    rating=item.get("rating", 0),
                    review_count=item.get("review_count", 0),
                    availability=item.get("availability", "Unknown"),
                    scraped_at=datetime.utcnow(),
                )
                session.add(ph)
                saved += 1
            except Exception as e:
                session.rollback()
                logger.warning(f"  Skipped item: {e}")

        session.commit()
        session.close()
        logger.info(f"Selenium: saved {saved} items to PostgreSQL")

    except Exception as e:
        logger.error(f"Selenium spider failed: {e}")


def run_price_monitor():
    logger.info("=" * 60)
    logger.info("PRICE MONITOR STARTING")
    logger.info("=" * 60)
    try:
        from monitor.price_alert import run_monitor
        summary = run_monitor()
        logger.info(f"Monitor complete: {summary}")
    except Exception as e:
        logger.error(f"Price monitor failed: {e}")


if __name__ == "__main__":
    start = datetime.utcnow()
    logger.info(f"\nE-Commerce Intelligence Platform - Run started at {start.strftime('%Y-%m-%d %H:%M:%S')} UTC\n")

    run_scrapy_spiders()
    run_selenium_spiders()
    run_price_monitor()

    duration = (datetime.utcnow() - start).total_seconds()
    logger.info(f"\nAll tasks complete in {duration:.1f}s\n")
