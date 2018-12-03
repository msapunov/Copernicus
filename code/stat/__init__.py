from flask import Blueprint

bp = Blueprint("stat", __name__)

from code.stat import main