from flask_wtf import FlaskForm
from wtforms import TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Email
from base.pages.login.form import MessageForm


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


def contact(ext):
    form = MessageForm()
    form.id = ext.id
    form.project_title = "%s %s request created %s" % (
        ext.project.get_name(), ext.about(), ext.created.strftime("%Y-%m-%d %X"))
    form.responsible = ext.project.responsible.full_name()
    form.destination.value = ext.project.responsible.email
    return form
