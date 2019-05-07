from flask import Blueprint

bp = Blueprint("login", __name__)

from base.pages.login import url
