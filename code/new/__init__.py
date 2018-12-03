from flask import Blueprint

bp = Blueprint("new", __name__)

from code.new import process