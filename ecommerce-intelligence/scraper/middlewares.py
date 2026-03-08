"""
Custom Scrapy Middlewares
- Rotating User Agents (anti-ban)
- Proxy Rotation
- Smart Retry with backoff
"""

import random
import time
import logging
from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

logger = logging.getLogger(__name__)

# Large pool of real browser user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

# Free proxies list (replace with real proxy service in production)
PROXY_LIST = [
    # Add proxies in format: "http://user:pass@ip:port"
    # Example: "http://103.152.112.162:80",
]


class RotatingUserAgentMiddleware:
    """Rotates user agent on every request to avoid detection."""

    def process_request(self, request, spider):
        user_agent = random.choice(USER_AGENTS)
        request.headers["User-Agent"] = user_agent
        # Add realistic browser headers
        request.headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        request.headers["Accept-Language"] = "en-US,en;q=0.5"
        request.headers["Accept-Encoding"] = "gzip, deflate, br"
        request.headers["DNT"] = "1"
        request.headers["Connection"] = "keep-alive"
        request.headers["Upgrade-Insecure-Requests"] = "1"
        logger.debug(f"Using User-Agent: {user_agent[:60]}...")


class ProxyMiddleware:
    """Rotates proxies for each request (if configured)."""

    def process_request(self, request, spider):
        if PROXY_LIST:
            proxy = random.choice(PROXY_LIST)
            request.meta["proxy"] = proxy
            logger.debug(f"Using proxy: {proxy}")


class RetryMiddleware(RetryMiddleware):
    """Enhanced retry with exponential backoff."""

    def process_response(self, request, response, spider):
        if response.status in self.retry_http_codes:
            retry_count = request.meta.get("retry_times", 0)
            wait_time = min(2 ** retry_count * 2, 30)   # exponential backoff, max 30s
            logger.warning(f"Got {response.status} for {request.url} — retrying in {wait_time}s (attempt {retry_count + 1})")
            time.sleep(wait_time)
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        retry_count = request.meta.get("retry_times", 0)
        wait_time = min(2 ** retry_count * 2, 30)
        logger.warning(f"Exception {exception.__class__.__name__} for {request.url} — retrying in {wait_time}s")
        time.sleep(wait_time)
        return super().process_exception(request, exception, spider)
