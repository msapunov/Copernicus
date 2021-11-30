from flask import Blueprint

bp = Blueprint("project", __name__)


@bp.app_template_filter()
def datetime_format(value, representation="%H:%M %d-%m-%y"):
    if not value:
        return None
    return value.strftime(representation)

from base.pages.project import url
