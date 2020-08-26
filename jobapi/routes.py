from flask import Flask, jsonify, request, redirect, url_for
import crochet
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.signalmanager import dispatcher
import os
from jobapi.jobcrawler.jobcrawler.spiders.job_spider import JobSpider
import time 
import re
from collections import Counter
from jobapi.models import User, Query, Job
from jobapi import app, db, bcrypt
import uuid
import jwt
from functools import wraps

crochet.setup()
output_data = []
crawl_runner = CrawlerRunner()

def get_user(func):
    #decorator to get the user that's signed in
    @wraps(func)
    def inner(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        user= None
        if auth_header:
            token = auth_header.replace("Bearer ", "")
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'])
                user = User.query.filter_by(public_id=data['public_id']).first()
            except:
                user= None
        return func(user, *args, **kwargs)
    return inner

@app.route("/")
def hello():
    return "Hello World"

@app.route("/signup", methods=['POST'])
def signup():
    try:
        if request.method == 'POST':
            email = request.json['email']
            password = request.json['password']
            if not email or not password:
                return jsonify({"error": "Email and password are required"})
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(public_id=str(uuid.uuid4()), email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            token = jwt.encode({'public_id':user.public_id}, app.config['SECRET_KEY'])

            return jsonify({"token": token.decode('UTF-8')})
    except:
        return jsonify({"error":"Error creating account. Already have an account? Sign in instead"}), 400

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.json['email']
        password = request.json['password']
        if not email or not password:
            return jsonify({"error": "Email and password are required"})
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            token = jwt.encode({'public_id':user.public_id}, app.config['SECRET_KEY'])

            return jsonify({"token": token.decode('UTF-8')})
            
        return jsonify({"error":"Email not found. Sign up instead"}), 400

@app.route('/queries', methods=['GET'])
@get_user
def get_job_queries(user):
    if user:
        user_query_history = Query.query.filter_by(user_id=user.id).all()
        return jsonify(user_query_history)
    return jsonify({"error":"Error fetching your search history"}), 400

@app.route('/queries/<id>', methods=['GET'])
@get_user
def get_job_data(user, id):
    if user:
        query = Query.query.get(id)
        print(len(query.jobs))
        return jsonify(query.jobs)
    return jsonify({"error": "Error fetching job results"}), 400

@app.route('/scrape', methods=['POST'])
@get_user
def scrape_job_data(user):
    try:
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
            
            (data, counter) =  scrape(url, technologies) # Passing to the Scrape function
            if user:
                print(user.id)
                query = Query(site=site, job_type=job_type,city=city, country=country, province=province, user_id=user.id)
                db.session.add(query)
                db.session.commit()
                print(query.id)
                save_to_db(query.id, data)
            return jsonify({"jobs":data, "counter":counter})
    except:
        return jsonify({"error":"Error getting job data. Please try again"}), 400

def scrape(url, tech):
    scrape_with_crochet(baseUrl=url) # Passing that URL to our Scraping Function

    time.sleep(30) # Pause the function while the scrapy spider is running

    return analyse_description(output_data, tech)

@crochet.run_in_reactor
def scrape_with_crochet(baseUrl):
    # This will connect to the dispatcher that will kind of loop the code between these two functions.
    dispatcher.connect(_crawler_result, signal=signals.item_scraped)
    
    # This will connect to the ReviewspiderSpider function in our scrapy file and after each yield will pass to the crawler_result function.
    eventual = crawl_runner.crawl(JobSpider, category=baseUrl)
    dispatcher.connect(_crawler_Stop, signals.engine_stopped)
    return eventual

#This will append the data to the output data list.
def _crawler_result(item, response, spider):
    output_data.append(dict(item))

def save_to_db(query_id, data):
    for job in data:
        j = Job(title=job['title'], company=job['company'], rating=job['rating'], description=job['description'],link=job['link'], salary=job['salary'], query_id = query_id)
        db.session.add(j)
    db.session.commit()



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


