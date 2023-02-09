from flask_wtf import FlaskForm
from wtforms import TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Email


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class RejectForm(FlaskForm):
    note = TextAreaField(validators=[DataRequired(
        message="Please indicate a reason for rejection")])


def rejection(project):
    form = RejectForm()
    form.name = project.name
    return form


class AcceptForm(FlaskForm):
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    note = TextAreaField("Note", validators=[DataRequired(
        message="Acceptance note field is empty")])
    extend = BooleanField()


def acceptance(record):
    form = AcceptForm(active=True)
    form.note.data = "Renewal accepted by CCIAM"
    if record.transform != " ":
        form.ext_check = "checked = checked"
    elif record.activate:
        form.new_check = "checked = checked"
    else:
        if record.extend:
            form.ext_check = "checked = checked"
        else:
            form.new_check = "checked = checked"
    return form
