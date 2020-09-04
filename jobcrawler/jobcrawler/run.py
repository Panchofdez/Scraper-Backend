import scrapy
from scrapy.crawler import CrawlerProcess
from spiders.job_spider import JobSpider


process = CrawlerProcess(settings={
    "FEEDS": {
        "items.json": {"format": "json"},
    },
})

process.crawl(JobSpider)
process.start()