from flask import Blueprint

bp = Blueprint("user", __name__)

from code.pages.user import url