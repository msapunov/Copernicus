from flask import Blueprint

bp = Blueprint("board", __name__)

from code.pages.board import url