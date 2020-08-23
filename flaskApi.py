from flask import Flask,render_template, jsonify, request, redirect, url_for
import crochet
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.signalmanager import dispatcher
import os
from jobcrawler.jobcrawler.spiders.job_spider import JobSpider
import time 
import re
from collections import Counter
from flask_cors import CORS


crochet.setup()
app = Flask(__name__)
CORS(app)

output_data = []
crawl_runner = CrawlerRunner()


@app.route("/")
def hello():
    return "Hello World"

@app.route('/scrape', methods=['POST'])
def submit():
    if request.method == 'POST':
        site = request.json["site"]
        job_type = request.json["type"]
        city = request.json["city"]
        country = request.json["country"]
        province = request.json["province"]
        technologies = request.json["technologies"]

        url = create_url(site, job_type, country, city, province)
        # This will remove any existing file with the same name so that the scrapy will not append the data to any previous file.
        # if os.path.exists("outputfile.json"): 
        # 	os.remove("outputfile.json")

        return scrape(url, technologies) # Passing to the Scrape function

def scrape(url, tech):
    scrape_with_crochet(baseUrl=url) # Passing that URL to our Scraping Function

    time.sleep(30) # Pause the function while the scrapy spider is running

    (data, counter) = analyse_description(output_data, tech)
    print(len(data))
    return jsonify({"jobs":data, "counter":counter}) # Returns the scraped data after being running for 20 seconds.


@crochet.run_in_reactor
def scrape_with_crochet(baseUrl):
    # This will connect to the dispatcher that will kind of loop the code between these two functions.
    dispatcher.connect(_crawler_result, signal=signals.item_scraped)
    
    # This will connect to the ReviewspiderSpider function in our scrapy file and after each yield will pass to the crawler_result function.
    eventual = crawl_runner.crawl(JobSpider, category=baseUrl)
    return eventual

#This will append the data to the output data list.
def _crawler_result(item, response, spider):
    output_data.append(dict(item))


def create_url(site, job_type, country, city, province):
    url = ""
    job = "+".join([word.lower() for word in job_type.split(" ")])
    print(job)
    province = province.upper()
    city = city.lower().capitalize()
    if site == "Indeed":
        if country =="Canada":
            url = f"https://ca.indeed.com/jobs?q={job}&l={city}%2C+{province}"
        else:
            url = f"https://indeed.com/jobs?q={job}&l={city}%2C+{province}"
    print(url)
    return url
def analyse_text(data):
        words = []
        for job in data:
            # res = re.findall(r"\b[a-z].*?\b", job["description"])
            res = re.findall(r"\b[a-zA-z/\-+#.]+\b", job["description"].lower())
            words.extend(res)
        counter = Counter(words)
        return counter

def analyse_description(data, technologies):
    string = r""
    for word in technologies:
        word = word.lower()
        if "+#".find(word[-1]) == -1:
            if len(word)<=2:
                string += rf"\b{re.escape(word)}\b|"
            else:
                string += rf"{re.escape(word)}|"
        else:
            string += rf"\b{re.escape(word)}|"
    words = []
    for job in data:
        matches = re.findall(string[:len(string)-1], job["description"].lower(), flags=re.IGNORECASE)
        words.extend(matches)
        tech = Counter(matches)
        job["technologies"] = tech
    counter = Counter(words)
    return (data, counter)

def sort_by_tech(self, data):
    return sorted(data, key=lambda x:x["score"], reverse=True)


if __name__ == "__main__":
    app.run(debug=True)