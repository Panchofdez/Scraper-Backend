import scrapy
from ..items import JobcrawlerItem
import re
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError

class JobSpider(scrapy.Spider):
    name = "jobs"
    start = 0
    myBaseUrl = ''
    site = ''
    start_urls = []
    def __init__(self,url='', site='', **kwargs): 
        self.myBaseUrl = url 
        self.site = site
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
            yield scrapy.Request(joblink, callback=self.get_indeed_description, cb_kwargs=dict(item=item))
        self.start+=10
        next_p = self.myBaseUrl + f'&start={self.start}'
        if self.start <= 250:
            yield scrapy.Request(next_p, callback=self.parse)

    def get_indeed_description(self, response, item):
        description = response.css('div#jobDescriptionText ::text').getall()
        if len(description) == 0:
            item['description']=""
        else:
            item['description'] = self.format(description)
        return item

    def format(self, arr):
        string =  "".join(arr).replace("\n", "")
        return re.sub(r"[^\x00-\x7F]+", "", string)


    def errback_httpbin(self, failure):
        # log all failures
        self.logger.error(repr(failure))

        # in case you want to do something special for some errors,
        # you may need the failure's type:

        if failure.check(HttpError):
            # these exceptions come from HttpError spider middleware
            # you can get the non-200 response
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        elif failure.check(DNSLookupError):
            # this is the original request
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        elif failure.check(TimeoutError, TCPTimedOutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)