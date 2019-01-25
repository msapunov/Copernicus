from flask import Flask, g, jsonify
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.contrib.cache import SimpleCache
from code.pages.login import bp as blueprint_login
from code.pages.project import bp as blueprint_project
from code.pages.user import bp as blueprint_user
from code.pages.board import bp as blueprint_board
from code.pages.admin import bp as blueprint_admin
from datetime import datetime as dt
from flask_mail import Mail
from werkzeug.exceptions import HTTPException
from logging import error


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("copernicus.cfg")


@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    error(str(e))
    return str(e), code


mail = Mail(app)

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

    url_list = cache.get("url_list")
    if not url_list:
        url_list = ["%s" % rule for rule in app.url_map.iter_rules()]
        cache.set("url_list", url_list, 600)
    g.url_list = url_list


@app.template_filter("menu_item")
def menu_item(obj):
    line = str(obj)
    line = line.replace("<TemplateReference '", "")
    line = line.replace(".html'>", "")
    return line

app.register_blueprint(blueprint_login)
app.register_blueprint(blueprint_project)
app.register_blueprint(blueprint_user)
app.register_blueprint(blueprint_board)
app.register_blueprint(blueprint_admin, url_prefix="/admin")
