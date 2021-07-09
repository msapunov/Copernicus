from flask_wtf import Form
from wtforms import HiddenField, IntegerField, BooleanField
from wtforms import TextAreaField, SelectField
from wtforms.validators import DataRequired, NumberRange
from base.pages.project.magic import project_config


class ActivateForm(Form):
    pid_err = "Project id is missing"
    cpu_err = "CPU value must be 0 or any other positive number"
    err = "Motivation field is empty"

    pid = HiddenField(validators=[DataRequired(message=pid_err)])
    cpu = IntegerField("CPU", validators=[NumberRange(min=0, message=cpu_err)])
    note = TextAreaField("Motivation", validators=[DataRequired(message=err)])


def Activate(project):
    form = ActivateForm()
    form.name = project.name
    form.pid.data = project.id
    return form


class TransForm(Form):

    pid_err = "Project id is missing"
    new_err = "New type is missing"
    cpu_err = "CPU value must be 0 or any other positive number"
    err = "Motivation field is empty"

    pid = HiddenField(validators=[DataRequired(message=pid_err)])
    new = SelectField("New type", validators=[DataRequired(message=new_err)])
    cpu = IntegerField("CPU", validators=[NumberRange(min=0, message=cpu_err)])
    note = TextAreaField("Motivation", validators=[DataRequired(message=err)])


def getTransformationOptions(type=None):
    config = project_config()
    options = []
    for name in config.keys():
        desc = config[name].get("description", None)
        options.append((name.lower(), desc if desc else name))

    if (not type) or (type not in config.keys()):
        return options

    trans = config[type].get("transform", None)
    if not trans:
        return options

    options_copy = options.copy()
    for option in options_copy:
        if option[0] not in trans:
            options.remove(option)
    return options


def Transform(project):
    form = TransForm()
    form.name = project.name
    form.pid.data = project.id
    form.new.choices = getTransformationOptions(project.type)
    return form


class ExtendForm(Form):
    pid_err = "Project id is missing"
    cpu_err = "CPU value must be 0 or any other positive number"
    err = "Motivation field is empty"

    pid = HiddenField(validators=[DataRequired(message=pid_err)])
    exception = BooleanField()
    cpu = IntegerField("CPU", validators=[NumberRange(min=0, message=cpu_err)])
    note = TextAreaField("Motivation", validators=[DataRequired(message=err)])

def Allocate(project):
    config = project_config()
    type = project.type.lower()
    if type not in config.keys():
        return
#    if not config[type].get("extendable", None):
#        return

    form = ExtendForm()
    form.name = project.name
    form.pid.data = project.id
    form.legend = "Test"
    return form
