import scrapy
from ..items import JobcrawlerItem
import re
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError

class JobSpider(scrapy.Spider):
    name = "jobs"   
   
    def __init__(self,url='', site='', **kwargs): 
        self.numJobs = 0
        self.numPages = 1
        self.myBaseUrl = url 
        self.site = site
        
        super().__init__(**kwargs)

    # custom_settings = {'FEED_URI': 'jobcrawler/outputfile.json'}
    def start_requests(self):
        if self.site == "Indeed":
            yield scrapy.Request(self.myBaseUrl, callback = self.indeed_parse)
        elif self.site == "Stack Overflow":
            yield scrapy.Request(self.myBaseUrl, callback=self.stackoverflow_parse)

    def indeed_parse(self, response):
        '''Handles all the scraping logic for scraping indeed.
         ***Currently does not work as Indeed is blocking attempts'''
  
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
        self.numJobs+=10
        next_p = self.myBaseUrl + f'&start={self.numJobs}'
        if self.numJobs <= 200:
            yield scrapy.Request(next_p, callback=self.parse)

    def stackoverflow_parse(self, response):
        url_prefix =  "https://stackoverflow.com/"
        jobs = response.css('div.-job')
        
        if len(jobs) == 0:
            return 

        for job in jobs:
            
            item = JobcrawlerItem()
            title = job.css('a.s-link ::text').get(default="")
            company  = job.xpath('.//h3/span/text()').get(default="")
            joblink  = url_prefix + job.xpath('.//h2/a/@href').get()
            item['title'] = title 
            item['company'] = company 
            item['salary'] =  ""
            item['rating'] =  ""
            item['link'] = joblink
            print(title)
            print(company)
            print(joblink)
            yield scrapy.Request(joblink, callback=self.get_stackoverflow_description, cb_kwargs=dict(item=item))

        self.numJobs += len(jobs)
        self.numPages += 1
        next_page_link = self.myBaseUrl + f"&pg={self.numPages}"

        print(next_page_link)
        if self.numJobs <= 200 or self.numPages == 10:
            print("Next Page!")
            yield scrapy.Request(next_page_link, callback=self.stackoverflow_parse)


    def get_indeed_description(self, response, item):
        description = response.css('div#jobDescriptionText ::text').getall()
        if len(description) == 0:
            item['description']=""
        else:
            item['description'] = self.format(description)
        print("Item")
        print(item)
        return item

    def get_stackoverflow_description(self, response, item):
        description = response.css('section.fs-body2 *::text').getall()
        formatted_description = ""
        for text in description:
            if text.find("\n") == -1:
                formatted_description += text 
                formatted_description += " "
        item["description"] = formatted_description
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