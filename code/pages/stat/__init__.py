from flask import Blueprint

bp = Blueprint("stat", __name__)

from code.pages.stat import main