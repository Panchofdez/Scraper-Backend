from flask import Flask, json, jsonify, request, redirect, url_for
import crochet
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.signalmanager import dispatcher
import os
from jobcrawler.jobcrawler.spiders.job_spider import JobSpider
import time 
import re
from collections import Counter
from models import User, Query, Job, Favorite
from app import app, db, bcrypt
import uuid
import jwt
from functools import wraps
from dataclasses import asdict
from datetime import datetime

crochet.setup()
crawl_runner = CrawlerRunner()

def get_user(func):
    '''Decorator that acts as a middleware to check if a user is signed before accessing route'''
    @wraps(func)
    def inner(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        user= None
        if auth_header:
            token = auth_header.replace("Bearer ", "")
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'],  algorithms=["HS256"])
                user = User.query.filter_by(public_id=data['public_id']).first()
            except Exception as e:
                print("ERROR in getting user: ", e)
                user= None
        return func(user, *args, **kwargs)
    return inner

@app.route("/", methods=["GET"])
def hello():
    return jsonify({"message":"Hello World"})

@app.route("/signup", methods=['POST'])
def signup():
    try:
        if request.method == 'POST':
            email = request.json['email']
            password = request.json['password']
            password2 = request.json['password2']
            print(email, password, password2)
            if not email or not password:
                return jsonify({"type":"Error", "message":"Email and password are required"}), 400

            if password != password2:
                return jsonify({"type":"Error", "message":"Password and confirm password do not match"}), 400
            check_user = User.query.filter_by(email=email).first()
        
            if check_user:
                return jsonify({"type":"Error", "message":"Email already taken. Sign in instead"}), 400
         
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8') # we don't store the passwords directly we hash them first

            user = User(public_id=str(uuid.uuid4()), email=email, password=hashed_password) #create the user
            
            #save to the db
            db.session.add(user)
            db.session.commit() 
            #get the user token which will be used in the frontend to determine if user is signed in or not
            token = jwt.encode({'public_id':user.public_id}, app.config['SECRET_KEY'],algorithm="HS256" )

            return jsonify({"token": token})
        

    except Exception as e:
        print("ERROR: ", e)
        return jsonify({"type":"Error", "message":"Error creating account, please try again"}), 400

@app.route('/login', methods=['POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.json['email']
            password = request.json['password']
            print(email, password)
            if not email or not password:
                return jsonify({"type":"Error", "message":"Email and password are required"}), 400
            user = User.query.filter_by(email=email).first()

            if user and bcrypt.check_password_hash(user.password, password): #if a valid user and the passwords match proceed with signing in and recieving the token
                token = jwt.encode({'public_id':user.public_id}, app.config['SECRET_KEY'], algorithm="HS256")

                return jsonify({"token": token})
            return jsonify({"type":"Error", "message":"User not found"}), 400

    except Exception as e:    
        print("ERROR: ", e)    
        return jsonify({"type":"Error", "message":"Email not found. Sign up instead"}), 400

@app.route('/queries', methods=['GET'])
@get_user
def get_job_queries(user):
    '''Retrieves all job queries that a user has searched'''
    try:
        if user:
            user_query_history = Query.query.filter_by(user_id=user.id).all()
            return jsonify(user_query_history)
        return jsonify({"type":"Error", "message":"No user found"}), 400
    except Exception as e:
        print("ERROR: ", e)
        return jsonify({"type":"Error", "message":"Error fetching your search history"}), 400

@app.route('/queries/<query_id>', methods=['GET'])
@get_user
def get_job_data(user, query_id):
    '''Retrieves the results from a given query'''
    try:
        if user and request.method == 'GET':
            
            query = Query.query.get(query_id)
            technologies = query.technologies.split()
            print("Technologies", technologies)
            data = []
            for job in query.jobs:
                data.append(asdict(job))

            output = analyse_description(data, technologies)
            output["query"] = query
            for job in output["jobs"]: #delete the description from the job object because we dont need that info on the frontend
                del job["description"]
            print(len(output["jobs"]))
            return jsonify(output)
        return jsonify({"type":"Error","message": "Error fetching job results"}), 400
    except Exception as e:
        print("ERROR: ", e)
        return jsonify({"type":"Error","message": "Error fetching job results"}), 400

@app.route('/queries/<query_id>', methods=['PUT'])
@get_user
def update_job_data(user, query_id):
    '''Refreshes or renews the job results for a given query'''
    try:
        if user:
            technologies = request.json["technologies"]
            query = Query.query.get(query_id)
            if user.id != query.user_id:
                return jsonify({"type":"Error", "message":"Unauthorized Request"}), 403
            url = create_url(query.site, query.job_type, query.country, query.city, query.province)

            #update the query information and save to db
            query.date = datetime.now()
            query.technologies = " ".join(technologies)
            for job in query.jobs:
                db.session.delete(job)
            db.session.commit()
            
            #do the scraping again
            output =  scrape(url, technologies, query.site)
            save_to_db(query.id, output["jobs"])
            output["query"] = query
            print(len(output["jobs"]))
            return jsonify(output)
        else:
            return jsonify({"type":"Error", "message":"Must be signed in"}), 400
    except Exception as e:
        print("ERROR: ", e)
        return jsonify({"type":"Error", "message": "Error scraping job data"}), 400

@app.route('/queries/<query_id>', methods=['DELETE'])
@get_user
def delete_query(user, query_id):
    '''Delete a query from a user's search history'''
    try:
        if user:
            query = Query.query.get(query_id)
            if user.id != query.user_id:
                return jsonify({"type": "Error", "message":"Unauthorized Request"}), 403  
            #delete all the jobs in the db that was part of the given query
            for job in query.jobs:
                db.session.delete(job)

            db.session.delete(query) #then delete the query itself
            db.session.commit()
            return jsonify({"type":"Success", "message": "Successfuly deleted search query"})
        else:
            return jsonify({"type":"Error","message": "Must be signed in!"}), 400
    except Exception as e:
        print("ERROR: ", e)
        return jsonify({"type":"Error","message":"Unable to process request"}), 400

       


@app.route('/analyse/<query_id>',methods=['POST'])
@get_user
def analyse(user, query_id):
    '''Given a new list of technologies it will analyse the descriptions of each job post of the given query again and return the results'''
    try:
        if user and request.method == 'POST':
            
            technologies = request.json["technologies"]
            query = Query.query.get(query_id)

            #update the query information to the recent technologies
            query.technologies = " ".join(technologies)
            db.session.commit()

            
            print("Technologies", technologies)
            data = []
            for job in query.jobs:
                data.append(asdict(job))

            output = analyse_description(data, technologies)
            output["query"] = query

            for job in output["jobs"]: #delete the description from the job object because we dont need that info on the frontend
                del job["description"]
            print(len(output["jobs"]))
            return jsonify(output)
        return jsonify({"type":"Error","message": "Error fetching job results"}), 400
    except Exception as e:
        print("ERROR: ", e)
        return jsonify({"type":"Error","message": "Error fetching job results"}), 400


@app.route('/favorites' , methods=['GET'])
@get_user
def fetch_favorite_jobs(user):
    '''Retrieves the saved/favorited jobs of a user'''
    try:
        if user:  
            return jsonify(user.favorites)
        else:
            return jsonify({"type":"Error", "message": "Must be signed in"}), 400
    except Exception as e:
        return jsonify({"type":"Error", "message": "Unable to fetch results, please try again"}), 400

@app.route('/favorites', methods=['POST'])
@get_user
def favorite_job(user):
    '''Saves or favorites a job post to a user's profile'''
    try:
        if user and request.method == 'POST':
            job= request.json["job"]
            f_job = Favorite(title=job['title'], company=job['company'], rating=job['rating'], description=job['description'],link=job['link'], salary=job['salary'], user_id=user.id)
            db.session.add(f_job)
            db.session.commit()

            return jsonify({"type":"Success", "message":"Successfully saved job to your profile"})
        else:
            return jsonify({"type":"Error", "message": "You must be signed in to access this feature"}), 400
    except Exception as e:
        return jsonify({"type":"Error","message": "Unable to save job to your profile, please try again"}), 400

@app.route('/favorites/<favorite_id>', methods=['DELETE'])
@get_user
def delete_favorite_job(user, favorite_id):
    '''Deletes a favorited job post from the user's saved jobs'''
    try:
        if user and favorite_id and request.method == 'DELETE':
            favorite = Favorite.query.get(favorite_id)
            db.session.delete(favorite)
            db.commit()

            return jsonify({"type":"Success", "message":"Successfully deleted job from your profile"})
        
        else:
            return jsonify({"type":"Error", "message": "You must be signed in to access this feature"}), 400
    except Exception as e:
        print("Error", e)
        return jsonify({"type":"Error","message": "Unable to delete job from profile, please try again"}), 400

@app.route('/scrape', methods=['POST'])
@get_user
def scrape_job_data(user):
    '''Scrapes job posts from a given site and analyses the description of each job post to match and count certain technologies provided by the user'''
    try:
        if request.method == 'POST':
            site = request.json["site"]
            job_type = request.json["type"]
            city = request.json["city"]
            country = request.json["country"]
            province = request.json["province"]
            technologies = request.json["technologies"]
            url = create_url(site, job_type, country, city, province)

            if url == "":
                return jsonify({"type": "Error", "message": "Error fetching job results, please try again"}),400

            output =  scrape(url, technologies , site) # Passing to the Scrape function
            if len(output["jobs"]) == 0:
                return jsonify({"type": "Error", "message": "No results found..."}),400


            query = {}
            
            if user:
                technology_string = " ".join(technologies)
                query = Query(site=site, job_type=job_type,city=city, country=country, province=province, technologies=technology_string, user_id=user.id)
                db.session.add(query)
                db.session.commit()
                save_to_db(query.id, output["jobs"])
            output["query"] = query
            print(len(output["jobs"]))

            for job in output["jobs"]: #delete the description from the job object because we dont need that info on the frontend
                del job["description"]
            return jsonify(output)
    except Exception as e:
        print("ERROR: ", e)
        return jsonify({"type": "Error", "message": "Error fetching job results, please try again"}),400


def scrape(url, tech, site):
    global output_data
    output_data=[]
    scrape_with_crochet(baseUrl=url,site=site) # Passing that URL to our Scraping Function

    time.sleep(20) # Pause the function while the scrapy spider is running

    return analyse_description(output_data, tech)

@crochet.run_in_reactor
def scrape_with_crochet(baseUrl, site):
    
    # This will connect to the dispatcher that will kind of loop the code between these two functions.
    dispatcher.connect(_crawler_result, signal=signals.item_scraped)
    
    # This will connect to the Spider function in our scrapy file and after each yield will pass to the crawler_result function.
    eventual = crawl_runner.crawl(JobSpider, url=baseUrl, site=site)
    dispatcher.connect(_crawler_Stop, signals.engine_stopped)
    return eventual

#This will append the data to the output data list.
def _crawler_result(item, response, spider):
    output_data.append(dict(item))

def save_to_db(query_id, data):
    '''Saves a job to the database'''
    for job in data:
        j = Job(title=job['title'], company=job['company'], rating=job['rating'], description=job['description'],link=job['link'], salary=job['salary'], query_id = query_id)
        db.session.add(j)
    db.session.commit()
    return



def create_url(site, job_type, country, city, province):
    '''Based on the website and location and job information it will construct the url to scrape'''
    url = ""
    if site == "Indeed":
        city = "%20".join(city.lower().capitalize().split(" "))
        province=province.upper()
        if country =="Canada":
            job = "%20".join([word.lower() for word in job_type.split(" ")])
            if province in provinces:
                url = f"https://ca.indeed.com/jobs?q={job}&l={city},%20{province}"
        else:
            job = "+".join([word.lower() for word in job_type.split(" ")])
            if province in states: 
                url = f"https://indeed.com/jobs?q={job}&l={city}%2C+{province}"

    elif site == "Stack Overflow":
        job = "+".join([word.lower() for word in job_type.split(" ")])
        city = "+".join([word.lower() for word in city.split(" ")])
        country  = "+".join([word.lower() for word in country.split(" ")])
        url = f"https://stackoverflow.com/jobs?q={job}&l={city}%2C+{province}%2C+{country}&d=20&u=km"
    print(url)
    return url
   

def analyse_description(data, technologies):
    '''Uses regex to match keywords (technologies) and creates a counter storing how many times the words appear in the given description'''
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
    return {"jobs":data, "counter":counter}

def sort_by_tech(self, data):
    return sorted(data, key=lambda x:x["score"], reverse=True)



provinces = {
    "ON":"Ontario",
    "BC":"British Colombia",
    "QC":"Quebec",
    "AB":"Alberta",
    "NB":"New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS":"Nova Scotia",
    "PE":"Prince Edward Island",
    "MB":"Manitoba",
    "SK":"Saskatchewan",
    "YT":"Yukon",
    "NT":"Northwest Territories",
    "NU":"Nunavut"
}


states = {
    'AK': 'Alaska',
    'AL': 'Alabama',
    'AR': 'Arkansas',
    'AS': 'American Samoa',
    'AZ': 'Arizona',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DC': 'District of Columbia',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'GU': 'Guam',
    'HI': 'Hawaii',
    'IA': 'Iowa',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'MA': 'Massachusetts',
    'MD': 'Maryland',
    'ME': 'Maine',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MO': 'Missouri',
    'MP': 'Northern Mariana Islands',
    'MS': 'Mississippi',
    'MT': 'Montana',
    'NA': 'National',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'NE': 'Nebraska',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NV': 'Nevada',
    'NY': 'New York',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'PR': 'Puerto Rico',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VA': 'Virginia',
    'VI': 'Virgin Islands',
    'VT': 'Vermont',
    'WA': 'Washington',
    'WI': 'Wisconsin',
    'WV': 'West Virginia',
    'WY': 'Wyoming'
}



