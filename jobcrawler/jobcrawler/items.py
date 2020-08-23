# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class JobcrawlerItem(scrapy.Item):
    # define the fields for your item here like:
    title = scrapy.Field()
    company = scrapy.Field()
    salary = scrapy.Field()
    rating = scrapy.Field()
    link = scrapy.Field()
    description = scrapy.Field()
