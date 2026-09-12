"""Board blueprint initialization."""

from flask import Blueprint

bp = Blueprint("board", __name__)

from base.pages.board import url