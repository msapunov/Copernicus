from flask import Flask
from flask_login import LoginManager

from code.login import bp as blueprint_login
from code.project import bp as blueprint_project


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("copernicus.cfg")

login = LoginManager(app)
login.login_view = "login.html"

app.register_blueprint(blueprint_login)
app.register_blueprint(blueprint_project)
