from flask import Blueprint

bp = Blueprint("admin", __name__)

from base.pages.admin import url
