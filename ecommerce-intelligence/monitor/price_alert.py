"""
Price Change Monitor
- Detects price drops and rises
- Detects stock status changes
- Logs alerts to DB and console
- Ready to extend with email notifications
"""

import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import text

from database.models import PriceHistory, PriceAlert, Product, get_session

load_dotenv()
logger = logging.getLogger(__name__)

PRICE_DROP_THRESHOLD = float(os.getenv("PRICE_DROP_THRESHOLD", 5.0))
PRICE_RISE_THRESHOLD = float(os.getenv("PRICE_RISE_THRESHOLD", 10.0))


class PriceMonitor:

    def __init__(self):
        self.session = get_session()
        self.alerts_generated = 0

    def run(self):
        """Main monitor loop."""
        logger.info("[MONITOR] Starting price monitor...")
        products = self.session.query(Product).all()
        logger.info(f"  Monitoring {len(products)} products")

        for product in products:
            self._check_product(product)

        logger.info(f"[BACK] Monitor complete. Generated {self.alerts_generated} alerts.")
        self.session.close()

    def _check_product(self, product: Product):
        """Compare last 2 price records for this product."""
        records = (
            self.session.query(PriceHistory)
            .filter_by(product_id=product.product_id)
            .order_by(PriceHistory.scraped_at.desc())
            .limit(2)
            .all()
        )

        if len(records) < 2:
            return  # Not enough history yet

        latest, previous = records[0], records[1]

        if latest.price is None or previous.price is None:
            return

        old_price = float(previous.price)
        new_price = float(latest.price)

        if old_price == 0:
            return

        change_pct = ((new_price - old_price) / old_price) * 100

        # Price DROP alert
        if change_pct <= -PRICE_DROP_THRESHOLD:
            self._create_alert(product, "PRICE_DROP", old_price, new_price, change_pct)

        # Price RISE alert
        elif change_pct >= PRICE_RISE_THRESHOLD:
            self._create_alert(product, "PRICE_RISE", old_price, new_price, change_pct)

        # Stock change alerts
        if previous.availability != latest.availability:
            if "out of stock" in latest.availability.lower():
                self._create_alert(product, "OUT_OF_STOCK", old_price, new_price, 0)
            elif "in stock" in latest.availability.lower() and "out of stock" in previous.availability.lower():
                self._create_alert(product, "BACK_IN_STOCK", old_price, new_price, 0)

    def _create_alert(self, product, alert_type, old_price, new_price, change_pct):
        """Log alert to DB and console."""
        alert = PriceAlert(
            product_id=product.product_id,
            alert_type=alert_type,
            old_price=old_price,
            new_price=new_price,
            change_pct=round(change_pct, 2),
            triggered_at=datetime.utcnow(),
            is_notified=False,
        )
        self.session.add(alert)
        self.session.commit()
        self.alerts_generated += 1

        emoji = {"PRICE_DROP": "[DROP]", "PRICE_RISE": "[RISE]", "OUT_OF_STOCK": "[OUT]", "BACK_IN_STOCK": "[BACK]"}.get(alert_type, "[WARN]")
        logger.info(
            f"{emoji} ALERT [{alert_type}] | {product.title[:50]} | "
            f"£{old_price:.2f} → £{new_price:.2f} ({change_pct:+.1f}%)"
        )

    def get_summary(self) -> dict:
        """Return alert summary stats."""
        total = self.session.query(PriceAlert).count()
        drops = self.session.query(PriceAlert).filter_by(alert_type="PRICE_DROP").count()
        rises = self.session.query(PriceAlert).filter_by(alert_type="PRICE_RISE").count()
        out_of_stock = self.session.query(PriceAlert).filter_by(alert_type="OUT_OF_STOCK").count()
        return {
            "total_alerts": total,
            "price_drops": drops,
            "price_rises": rises,
            "out_of_stock": out_of_stock,
        }


def run_monitor():
    monitor = PriceMonitor()
    monitor.run()
    summary = monitor.get_summary()
    logger.info(f"[STATS] Alert Summary: {summary}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    run_monitor()
