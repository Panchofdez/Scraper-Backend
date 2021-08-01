from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os


app = Flask(__name__)
CORS(app)
PRODUCTION = False
load_dotenv() 


if PRODUCTION:
    #database string needs to start with postgresql:// not postgres:// which is what heroku sets it to by default and is unchangeable
    app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE_URL').replace("://", "ql://", 1)
    app.debug = False
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:SpicyP#13@localhost/scraperdb'
    app.debug = True

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('MY_SECRET_KEY')


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
from routes import *



if __name__ == "__main__":
    app.run()
