"""
Scrapy Item Pipelines
1. DataCleaningPipeline   — sanitize & validate data
2. DuplicateFilterPipeline — MD5 hash deduplication
3. PostgreSQLPipeline      — persist to PostgreSQL
"""

import hashlib
import logging
import re
from datetime import datetime

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from sqlalchemy.exc import IntegrityError

from database.models import Product, PriceHistory, ScrapeRun, get_session

logger = logging.getLogger(__name__)


# ── Pipeline 1: Data Cleaning ──────────────────────────────────────────────
class DataCleaningPipeline:

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Clean title
        title = adapter.get("title", "")
        if not title or len(title.strip()) < 2:
            raise DropItem(f"Missing or invalid title: {title!r}")
        adapter["title"] = title.strip()

        # Clean & validate price
        price = adapter.get("price")
        try:
            price = float(str(price).replace("£", "").replace("$", "").replace(",", "").strip())
            if price < 0:
                raise ValueError("Negative price")
            adapter["price"] = round(price, 2)
        except (TypeError, ValueError):
            raise DropItem(f"Invalid price: {price!r} for item: {title}")

        # Clean original price
        orig_price = adapter.get("original_price", price)
        try:
            orig_price = float(str(orig_price).replace("£", "").replace("$", "").replace(",", "").strip())
            adapter["original_price"] = round(orig_price, 2)
        except (TypeError, ValueError):
            adapter["original_price"] = adapter["price"]

        # Calculate discount if not set
        if not adapter.get("discount_pct") and adapter["original_price"] > adapter["price"]:
            discount = ((adapter["original_price"] - adapter["price"]) / adapter["original_price"]) * 100
            adapter["discount_pct"] = round(discount, 2)
        else:
            adapter["discount_pct"] = adapter.get("discount_pct", 0.0) or 0.0

        # Clean rating
        rating = adapter.get("rating", 0.0)
        try:
            rating = float(rating)
            adapter["rating"] = max(0.0, min(5.0, round(rating, 2)))
        except (TypeError, ValueError):
            adapter["rating"] = 0.0

        # Clean review count
        review_count = adapter.get("review_count", 0)
        try:
            adapter["review_count"] = int(str(review_count).replace(",", "").strip())
        except (TypeError, ValueError):
            adapter["review_count"] = 0

        # Clean availability
        availability = str(adapter.get("availability", "Unknown")).strip()
        availability = re.sub(r"\s+", " ", availability)
        adapter["availability"] = availability[:100]

        # Clean category
        category = str(adapter.get("category", "Uncategorized")).strip()
        adapter["category"] = category[:255]

        # Ensure scraped_at
        if not adapter.get("scraped_at"):
            adapter["scraped_at"] = datetime.utcnow().isoformat()

        logger.debug(f"  [OK] Cleaned: {adapter['title'][:50]} | £{adapter['price']}")
        return item


# ── Pipeline 2: Duplicate Filter ──────────────────────────────────────────
class DuplicateFilterPipeline:

    def open_spider(self, spider):
        self.seen_hashes = set()
        self.dropped = 0

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # Hash on title + source to detect exact duplicates within a run
        content = f"{adapter.get('title','')}{adapter.get('source','')}{adapter.get('price',0)}"
        content_hash = hashlib.md5(content.encode()).hexdigest()

        if content_hash in self.seen_hashes:
            self.dropped += 1
            raise DropItem(f"Duplicate item dropped: {adapter.get('title','')[:50]}")

        self.seen_hashes.add(content_hash)
        adapter["content_hash"] = content_hash
        return item

    def close_spider(self, spider):
        logger.info(f"[DEL]  DuplicateFilter: dropped {self.dropped} duplicate items")


# ── Pipeline 3: PostgreSQL ─────────────────────────────────────────────────
class PostgreSQLPipeline:

    def open_spider(self, spider):
        self.session = get_session()
        self.items_saved = 0
        self.items_updated = 0
        self.items_failed = 0

        # Create a scrape run record
        self.scrape_run = ScrapeRun(
            spider_name=spider.name,
            started_at=datetime.utcnow(),
            status="RUNNING",
        )
        self.session.add(self.scrape_run)
        self.session.commit()
        logger.info(f"[DB] PostgreSQL pipeline ready | Run ID: {self.scrape_run.id}")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        session = self.session

        try:
            product_id = adapter.get("product_id")

            # Upsert product
            existing = session.query(Product).filter_by(product_id=product_id).first()
            if not existing:
                product = Product(
                    product_id=product_id,
                    title=adapter["title"],
                    category=adapter.get("category", "Uncategorized"),
                    url=adapter.get("url", ""),
                    source=adapter.get("source", ""),
                    image_url=adapter.get("image_url", ""),
                    content_hash=adapter.get("content_hash", ""),
                )
                session.add(product)
                self.items_saved += 1
            else:
                # Update metadata
                existing.title = adapter["title"]
                existing.updated_at = datetime.utcnow()
                self.items_updated += 1

            # Always insert new price record (price history tracking)
            price_record = PriceHistory(
                product_id=product_id,
                price=adapter.get("price"),
                original_price=adapter.get("original_price"),
                discount_pct=adapter.get("discount_pct", 0.0),
                rating=adapter.get("rating", 0.0),
                review_count=adapter.get("review_count", 0),
                availability=adapter.get("availability", "Unknown"),
                scraped_at=datetime.utcnow(),
            )
            session.add(price_record)
            session.commit()

        except IntegrityError:
            session.rollback()
            self.items_failed += 1
            logger.warning(f"DB integrity error for item: {adapter.get('title','')[:50]}")
        except Exception as e:
            session.rollback()
            self.items_failed += 1
            logger.error(f"DB error: {e} for item: {adapter.get('title','')[:50]}")

        return item

    def close_spider(self, spider):
        # Update scrape run stats
        try:
            self.scrape_run.ended_at = datetime.utcnow()
            self.scrape_run.items_scraped = self.items_saved + self.items_updated
            self.scrape_run.items_failed = self.items_failed
            self.scrape_run.duration_seconds = int(
                (self.scrape_run.ended_at - self.scrape_run.started_at).total_seconds()
            )
            self.scrape_run.status = "SUCCESS" if self.items_failed == 0 else "PARTIAL"
            self.session.commit()
        except Exception as e:
            logger.error(f"Failed to update scrape run: {e}")
        finally:
            self.session.close()

        logger.info(
            f"[OK] PostgreSQL Pipeline closed | "
            f"New: {self.items_saved} | Updated: {self.items_updated} | Failed: {self.items_failed}"
        )
