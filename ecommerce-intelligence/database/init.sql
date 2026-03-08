-- ============================================
-- E-Commerce Intelligence Platform
-- Database Schema
-- ============================================

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category VARCHAR(255),
    url TEXT,
    source VARCHAR(100),
    image_url TEXT,
    content_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),
    discount_pct DECIMAL(5,2),
    rating DECIMAL(3,2),
    review_count INT,
    availability VARCHAR(100),
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    alert_type VARCHAR(50),         -- 'PRICE_DROP', 'PRICE_RISE', 'OUT_OF_STOCK', 'BACK_IN_STOCK'
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    change_pct DECIMAL(10,2),
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_notified BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id SERIAL PRIMARY KEY,
    spider_name VARCHAR(100),
    items_scraped INT DEFAULT 0,
    items_failed INT DEFAULT 0,
    items_dropped INT DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds INT,
    status VARCHAR(50) DEFAULT 'RUNNING'   -- RUNNING, SUCCESS, FAILED
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_scraped_at ON price_history(scraped_at);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_source ON products(source);
CREATE INDEX IF NOT EXISTS idx_alerts_product_id ON price_alerts(product_id);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered_at ON price_alerts(triggered_at);

-- View: latest price per product
CREATE OR REPLACE VIEW latest_prices AS
SELECT DISTINCT ON (ph.product_id)
    p.product_id,
    p.title,
    p.category,
    p.source,
    p.url,
    ph.price,
    ph.original_price,
    ph.discount_pct,
    ph.rating,
    ph.review_count,
    ph.availability,
    ph.scraped_at
FROM price_history ph
JOIN products p ON p.product_id = ph.product_id
ORDER BY ph.product_id, ph.scraped_at DESC;