from flask import Blueprint

bp = Blueprint("statistic", __name__)

from base.pages.statistic import url