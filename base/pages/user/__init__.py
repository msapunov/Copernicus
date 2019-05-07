from flask import Blueprint

bp = Blueprint("user", __name__)

from base.pages.user import url