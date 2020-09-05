from app import db
from datetime import datetime
from dataclasses import dataclass


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable =False)
    queries = db.relationship('Query', backref='author', lazy=True)
    favorites =  db.relationship('Favorite', backref='author', lazy=True)

@dataclass
class Query(db.Model):
    __tablename__ = 'query'
    id:int
    site:str
    job_type:str
    date:datetime
    city:str
    country:str
    province:str
    user_id:int


    id = db.Column(db.Integer, primary_key=True)
    site = db.Column(db.String(100), nullable=False)
    job_type = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    city = db.Column(db.String(100), nullable=False)
    country =db.Column(db.String(100), nullable=False)
    province = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    jobs = db.relationship('Job', backref='author', lazy=True)

@dataclass
class Job(db.Model):
    __tablename__ = 'job'
    id:int
    title:str
    company:str
    rating:str
    description:str
    link:str
    salary:str
    query_id:int

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False) 
    company = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.String(50))
    description = db.Column(db.Text)
    link = db.Column(db.Text)
    salary = db.Column(db.String(200))
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'), nullable=False)
    
@dataclass
class Favorite(db.Model):
    __tablename__ = 'favorite'
    id:int
    title:str
    company:str
    rating:str
    description:str
    link:str
    salary:str
    user_id = int

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False) 
    company = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.String(50))
    description = db.Column(db.Text)
    link = db.Column(db.Text)
    salary = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)