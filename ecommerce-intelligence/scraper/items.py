"""
Scrapy Item Definitions
"""
import scrapy


class ProductItem(scrapy.Item):
    product_id = scrapy.Field()
    title = scrapy.Field()
    category = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    image_url = scrapy.Field()
    price = scrapy.Field()
    original_price = scrapy.Field()
    discount_pct = scrapy.Field()
    rating = scrapy.Field()
    review_count = scrapy.Field()
    availability = scrapy.Field()
    scraped_at = scrapy.Field()
