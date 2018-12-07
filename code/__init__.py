from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from code.pages.login import bp as blueprint_login
from code.pages.project import bp as blueprint_project
from code.pages.stat import bp as blueprint_stat


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("copernicus.cfg")

db = SQLAlchemy()
db.init_app(app)

login = LoginManager(app)
login.login_view = "login.login"
login.session_protection = "strong"

from code.database.schema import User
@login.user_loader
def load_user(userid):
    return User.query.filter(User.id == userid).first()

app.register_blueprint(blueprint_login)
app.register_blueprint(blueprint_project)
app.register_blueprint(blueprint_stat)
