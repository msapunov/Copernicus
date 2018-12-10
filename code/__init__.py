from flask import Flask, g
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.contrib.cache import SimpleCache
from code.pages.login import bp as blueprint_login
from code.pages.project import bp as blueprint_project
from code.pages.stat import bp as blueprint_stat
#from code.pages.admin import bp as blueprint_admin
from datetime import datetime as dt


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("copernicus.cfg")

cache = SimpleCache()

db = SQLAlchemy()
db.init_app(app)

login = LoginManager(app)
login.login_view = "login.login"
login.session_protection = "strong"

from code.database.schema import User
@login.user_loader
def load_user(userid):
    return User.query.filter(User.id == userid).first()

@app.before_request
def first_request():
    user_list = cache.get("user_list")
    if not user_list:
        users_obj = User.query.all()
        users = map(lambda x: x.login, users_obj)
        user_list = sorted(list(users))
        cache.set("user_list", user_list, 600)
    g.user_list = user_list
    tmp = "%s" % dt.now()
    g.timestamp = tmp.split(".")[0]


app.register_blueprint(blueprint_login)
app.register_blueprint(blueprint_project)
app.register_blueprint(blueprint_stat)
#app.register_blueprint(blueprint_admin)#, url_prefix="/admin")
