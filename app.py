from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from os import environ

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = environ.get('MY_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://wommclqmzcgqsj:21568b5c9f4ccbb2f2efa328e2ce2473b5df13f7b349dc8b50dde2299644dec2@ec2-34-195-115-225.compute-1.amazonaws.com:5432/dde6aqpmnh7uol'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

import routes



if __name__ == "__main__":
    app.run(debug=False)
