from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from code.login import bp as blueprint_login
from code.project import bp as blueprint_project
from code.stat import bp as blueprint_stat


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("copernicus.cfg")

db = SQLAlchemy()
db.init_app(app)

login = LoginManager(app)
login.login_view = "login.login"
login.session_protection = "strong"

app.register_blueprint(blueprint_login)
app.register_blueprint(blueprint_project)
app.register_blueprint(blueprint_stat)
