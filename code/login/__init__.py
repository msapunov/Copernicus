from flask import Blueprint

bp = Blueprint("login", __name__)

from code.login import url
