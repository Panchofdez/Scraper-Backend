import scrapy
from ..items import JobcrawlerItem
import re

class JobSpider(scrapy.Spider):
    name = "jobs"
    start = 0
    myBaseUrl = ''
    start_urls = []
    def __init__(self,category='', technologies = [], **kwargs): 
        self.myBaseUrl = category
        self.start_urls.append(self.myBaseUrl)
        super().__init__(**kwargs)

    # custom_settings = {'FEED_URI': 'jobcrawler/outputfile.json'}
    def parse(self, response):
        for job in response.css('div.jobsearch-SerpJobCard'):
            item = JobcrawlerItem()
            joblink = job.css('h2.title a::attr(href)').get()
            joblink = response.urljoin(joblink)
            title = job.css('a.jobtitle ::text').getall()
            company = job.css('span.company ::text').getall()
            salary = job.css('span.salaryText ::text').get(default='').replace("\n", "")
            ratings = job.css('span.ratingsContent ::text').get(default='').replace("\n", "")
            item['title'] = self.format(title) if title else ""
            item['company'] = self.format(company) if company else ""
            item['salary'] =  salary
            item['rating'] =  ratings
            item['link'] = joblink
            yield scrapy.Request(joblink, callback=self.get_description, cb_kwargs=dict(item=item))
        self.start+=10
        next_p = self.myBaseUrl + f'&start={self.start}'
        if self.start <= 250:
            yield scrapy.Request(next_p, callback=self.parse)
            
    def get_description(self, response, item):
        description = response.css('div#jobDescriptionText ::text').getall()
        if len(description) == 0:
            item['description']=""
        else:
            item['description'] = self.format(description)
        return item

    def format(self, arr):
        string =  "".join(arr).replace("\n", "")
        return re.sub(r"[^\x00-\x7F]+", "", string)
