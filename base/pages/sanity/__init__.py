from flask import Blueprint

bp = Blueprint("sanity", __name__)

from base.pages.sanity import url