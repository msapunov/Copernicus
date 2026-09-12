"""Project blueprint initialization."""

from flask import Blueprint

bp = Blueprint("project", __name__)


@bp.app_template_filter()
def datetime_format(value, representation="%H:%M %d-%m-%y"):
    """Format a datetime object for template display.

    Args:
        value: A datetime object or None.
        representation: strftime format string.

    Returns:
        Formatted date string or None.
    """
    if not value:
        return None
    return value.strftime(representation)


from base.pages.project import url
