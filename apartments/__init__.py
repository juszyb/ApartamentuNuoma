from flask import Flask
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_googlemaps import GoogleMaps
import stripe
import os

app = Flask(__name__)

SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GOOGLEMAPS_KEY'] = ""
db = SQLAlchemy(app)
ckeditor = CKEditor(app)
Bootstrap(app)
GoogleMaps(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

stripe.api_key = os.environ.get("STRIPE_API_KEY")

from apartments import routes

with app.app_context():
    db.create_all()
    pass