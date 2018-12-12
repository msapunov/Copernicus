from flask import Blueprint

bp = Blueprint("admin", __name__)

from code.pages.admin import url