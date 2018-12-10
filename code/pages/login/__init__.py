from flask import Blueprint

bp = Blueprint("login", __name__)

from code.pages.login import url
