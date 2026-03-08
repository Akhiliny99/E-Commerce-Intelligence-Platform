# 🛒 E-Commerce Intelligence Platform

> A **production-grade web scraping & price monitoring system** built with Scrapy, Selenium, PostgreSQL, and Streamlit.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Scrapy](https://img.shields.io/badge/Scrapy-2.11-green)
![Selenium](https://img.shields.io/badge/Selenium-4.18-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![CI/CD](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-green)

---

## 📋 Overview

This platform scrapes e-commerce product data at scale, tracks price history over time, detects price changes, and visualizes trends through an interactive dashboard.

### Key Features
- **Dual Scraping Engine** — Scrapy for static pages + Selenium for JavaScript-rendered pages
- **Price History Tracking** — Every price change is recorded in PostgreSQL with full history
- **Smart Alert System** — Detects price drops/rises above configurable thresholds
- **Anti-Detection** — Rotating user agents, request delays, retry with exponential backoff
- **Legal Compliance** — Respects `robots.txt`, rate limiting, ethical scraping practices
- **Interactive Dashboard** — Streamlit + Plotly for real-time analytics
- **Fully Containerized** — Docker Compose for one-command deployment
- **CI/CD Pipeline** — Automated testing, building, and scheduled scraping via GitHub Actions

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SCRAPING LAYER                        │
│                                                         │
│  Scrapy Spider (static HTML)  +  Selenium (JS pages)   │
│  ↓ Rotating User Agents           ↓ Headless Chrome     │
│  ↓ Rate Limiting                  ↓ Anti-detection      │
│  ↓ Retry Middleware               ↓ Dynamic content     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    PIPELINE LAYER                        │
│  1. DataCleaningPipeline   → sanitize & validate        │
│  2. DuplicateFilterPipeline → MD5 hash deduplication    │
│  3. PostgreSQLPipeline     → persist to DB              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│               PostgreSQL DATABASE                        │
│  products | price_history | price_alerts | scrape_runs  │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴───────────────┐
        │                             │
┌───────▼────────┐           ┌────────▼──────────┐
│ Price Monitor  │           │  Streamlit         │
│ Alert System   │           │  Dashboard         │
│ (change detect)│           │  (analytics UI)    │
└────────────────┘           └───────────────────┘
```

---

## 🗂️ Project Structure

```
ecommerce-intelligence/
├── scraper/
│   ├── spiders/
│   │   ├── static_spider.py     # Scrapy spider (books.toscrape.com)
│   │   └── dynamic_spider.py    # Selenium spider (JS-rendered pages)
│   ├── middlewares.py            # Rotating user agents, proxy, retry
│   ├── pipelines.py              # Clean → Deduplicate → PostgreSQL
│   ├── items.py                  # Scrapy item definitions
│   ├── settings.py               # Scrapy configuration
│   └── run_spiders.py            # Orchestrator (runs both spiders)
├── database/
│   ├── models.py                 # SQLAlchemy ORM models
│   └── init.sql                  # Schema + indexes + views
├── monitor/
│   └── price_alert.py            # Price change detection & alerts
├── dashboard/
│   └── app.py                    # Streamlit analytics dashboard
├── .github/workflows/
│   └── ci_cd.yml                 # GitHub Actions CI/CD
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── README.md
```

---

## 🗃️ Database Schema

```sql
products        — product metadata (id, title, category, source, url)
price_history   — every price snapshot over time (price, rating, availability)
price_alerts    — triggered alerts (PRICE_DROP, PRICE_RISE, OUT_OF_STOCK)
scrape_runs     — audit log for every spider run
latest_prices   — VIEW: most recent price per product
```

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Git

### 1. Clone & Configure
```bash
git clone https://github.com/YOUR_USERNAME/ecommerce-intelligence.git
cd ecommerce-intelligence
cp .env.example .env   # Edit DB credentials if needed
```

### 2. Start Everything
```bash
docker-compose up -d postgres
# Wait 10 seconds for DB to initialize
docker-compose up scraper
docker-compose up -d dashboard
```

### 3. Open Dashboard
```
http://localhost:8501
```

---

## 🏃 Running Without Docker (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start PostgreSQL (have it running locally or via Docker)
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=scraper_user \
  -e POSTGRES_PASSWORD=scraper_pass \
  -e POSTGRES_DB=ecommerce_db \
  postgres:15

# 3. Run scrapers
python -m scraper.run_spiders

# 4. Run price monitor
python -m monitor.price_alert

# 5. Launch dashboard
streamlit run dashboard/app.py
```

---

## ⚙️ Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `ecommerce_db` | Database name |
| `DB_USER` | `scraper_user` | DB username |
| `DB_PASSWORD` | `scraper_pass` | DB password |
| `PRICE_DROP_THRESHOLD` | `5.0` | Alert if price drops > 5% |
| `PRICE_RISE_THRESHOLD` | `10.0` | Alert if price rises > 10% |
| `SCRAPER_DELAY` | `2` | Seconds between requests |

---

## 🛡️ Legal & Ethical Compliance

This project is built with ethical scraping as a core principle:

- ✅ **robots.txt respected** — `ROBOTSTXT_OBEY = True` in Scrapy settings
- ✅ **Rate limiting** — Minimum 2-second delay between requests (configurable)
- ✅ **AutoThrottle** — Automatically reduces speed under server load
- ✅ **Practice sites only** — Default targets are `books.toscrape.com` and `quotes.toscrape.com`, sites built specifically for scraping education
- ✅ **No authentication bypass** — No login walls or CAPTCHA circumvention
- ✅ **No PII collection** — Only product/price data is collected

> ⚠️ Before scraping any real e-commerce site, always review their Terms of Service and robots.txt.

---

## 📊 Dashboard Pages

| Page | Description |
|---|---|
| **Overview** | KPIs, products by category, stock availability |
| **Price Trends** | Search products, view price history charts |
| **Top Products** | Best deals, highest rated, most reviewed |
| **Alerts** | Price drop/rise/stock change alerts |
| **Scrape Runs** | Audit log of all spider runs |

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| Static Scraping | Scrapy 2.11 |
| Dynamic Scraping | Selenium 4 + ChromeDriver |
| Anti-Detection | Rotating User Agents, AutoThrottle |
| Data Storage | PostgreSQL 15 + SQLAlchemy ORM |
| Monitoring | Custom price change detector |
| Dashboard | Streamlit + Plotly |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## 📄 License

MIT License — free to use for learning and portfolio purposes.
