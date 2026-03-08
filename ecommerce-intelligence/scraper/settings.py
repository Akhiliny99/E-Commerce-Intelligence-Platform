

BOT_NAME = "ecommerce_intelligence"
SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"


ROBOTSTXT_OBEY = False                  
DOWNLOAD_DELAY = 2                      
RANDOMIZE_DOWNLOAD_DELAY = True          
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# ── Rotating User Agents ───────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scraper.middlewares.RotatingUserAgentMiddleware": 400,
    "scraper.middlewares.ProxyMiddleware": 410,
    "scraper.middlewares.RetryMiddleware": 550,
}

# ── Item Pipelines ─────────────────────────────────────────────────
ITEM_PIPELINES = {
    "scraper.pipelines.DataCleaningPipeline": 100,
    "scraper.pipelines.DuplicateFilterPipeline": 200,
    "scraper.pipelines.PostgreSQLPipeline": 300,
}

# ── Retry Settings ─────────────────────────────────────────────────
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# ── Cache (speeds up dev) ──────────────────────────────────────────
HTTPCACHE_ENABLED = False   # Set True during development

# ── Feeds ─────────────────────────────────────────────────────────
FEEDS = {
    "output/scraped_%(time)s.json": {
        "format": "json",
        "overwrite": False,
    },
}

# ── Logging ───────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FILE = "logs/scrapy.log"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"