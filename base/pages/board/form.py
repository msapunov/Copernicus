"""WTForms for the board (admin extension/renewal approval)."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, NumberRange

from base.functions import calculate_ttl
from base.pages.login.form import MessageForm

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class RejectForm(FlaskForm):
    """Form for providing a rejection reason."""

    note = TextAreaField(
        validators=[DataRequired(message="Please indicate a reason for rejection")]
    )


def rejection(project):
    """Create a RejectForm for a given project.

    Args:
        project: Project instance.

    Returns:
        A RejectForm instance.
    """
    form = RejectForm()
    form.name = project.name
    return form


class AcceptForm(FlaskForm):
    """Form for accepting an extension/renewal request with optional overrides."""

    cpu = IntegerField(
        "CPU",
        validators=[
            NumberRange(
                min=0, message="CPU value must be 0 or any other positive number"
            )
        ],
    )
    note = TextAreaField(
        "Note", validators=[DataRequired(message="Acceptance note field is empty")]
    )
    ttl = DateField(
        "Until",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Resource validity field is empty")],
    )
    extend = BooleanField()


def acceptance(record):
    """Create an AcceptForm pre-populated from an Extend record.

    Args:
        record: Extend instance.

    Returns:
        An AcceptForm instance.
    """
    form = AcceptForm(active=True)
    if record.transform.strip():
        form.ext_check = "checked = checked"
    elif record.activate:
        form.new_check = "checked = checked"
    else:
        if record.extend:
            form.ext_check = "checked = checked"
        else:
            form.new_check = "checked = checked"
    if record.transform.strip():
        form.ttl.data = calculate_ttl(record.transform)
    else:
        form.ttl.data = record.project.resources.ttl
    return form


def contact(ext):
    """Create a MessageForm for contacting the project responsible.

    Args:
        ext: Extend instance.

    Returns:
        A MessageForm instance.
    """
    form = MessageForm()
    form.id = ext.id
    form.title_value = (
        f"{ext.project.get_name()} {ext.about()}"
        f" request created {ext.created.strftime('%Y-%m-%d %X')}"
    )
    form.message_holder = f"Write message to {ext.project.responsible.full()}"
    form.destination.value = ext.project.responsible.email
    return form
