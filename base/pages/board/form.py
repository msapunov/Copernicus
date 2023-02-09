from flask_wtf import FlaskForm
from wtforms import TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Email


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class RejectForm(FlaskForm):
    note = TextAreaField("Note", validators=[DataRequired(
        message="Note field is empty")])


def rejection(project):
    form = RejectForm()
    form.name = project.name
    return form


class AcceptForm(FlaskForm):
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    note = TextAreaField("Note", validators=[DataRequired(
        message="Acceptance note field is empty")])
    send = BooleanField(default="checked")


def acceptance(record):
    form = AcceptForm()
    return form