from flask import Blueprint

bp = Blueprint("project", __name__)

from code.pages.project import magic