from flask import Flask

from code.login import bp as blueprint_login


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("copernicus.cfg")


app.register_blueprint(blueprint_login)
