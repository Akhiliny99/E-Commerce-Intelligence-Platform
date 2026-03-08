"""
SQLAlchemy ORM Models for E-Commerce Intelligence Platform
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean,
    DateTime, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


def get_db_url():
    return (
        f"postgresql://{os.getenv('DB_USER', 'scraper_user')}:"
        f"{os.getenv('DB_PASSWORD', 'scraper_pass')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'ecommerce_db')}"
    )


def get_engine():
    return create_engine(get_db_url(), poolclass=NullPool, echo=False)


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    product_id = Column(String(255), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    category = Column(String(255))
    url = Column(Text)
    source = Column(String(100))
    image_url = Column(Text)
    content_hash = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prices = relationship("PriceHistory", back_populates="product", cascade="all, delete")
    alerts = relationship("PriceAlert", back_populates="product", cascade="all, delete")

    def __repr__(self):
        return f"<Product(id={self.product_id}, title={self.title[:40]})>"


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(String(255), ForeignKey("products.product_id"), nullable=False)
    price = Column(Numeric(10, 2))
    original_price = Column(Numeric(10, 2))
    discount_pct = Column(Numeric(5, 2))
    rating = Column(Numeric(3, 2))
    review_count = Column(Integer)
    availability = Column(String(100))
    scraped_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="prices")

    def __repr__(self):
        return f"<PriceHistory(product={self.product_id}, price={self.price}, at={self.scraped_at})>"


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True)
    product_id = Column(String(255), ForeignKey("products.product_id"), nullable=False)
    alert_type = Column(String(50))
    old_price = Column(Numeric(10, 2))
    new_price = Column(Numeric(10, 2))
    change_pct = Column(Numeric(5, 2))
    triggered_at = Column(DateTime, default=datetime.utcnow)
    is_notified = Column(Boolean, default=False)

    product = relationship("Product", back_populates="alerts")

    def __repr__(self):
        return f"<PriceAlert(type={self.alert_type}, product={self.product_id}, change={self.change_pct}%)>"


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True)
    spider_name = Column(String(100))
    items_scraped = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    items_dropped = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)
    status = Column(String(50), default="RUNNING")

    def __repr__(self):
        return f"<ScrapeRun(spider={self.spider_name}, status={self.status}, scraped={self.items_scraped})>"
