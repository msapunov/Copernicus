from flask import Blueprint

bp = Blueprint("new", __name__)

from code.pages.new import process