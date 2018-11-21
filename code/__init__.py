from flask import Flask
from code.login.views import login_blueprint


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("copernicus.cfg")


app.register_blueprint(login_blueprint)
