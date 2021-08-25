from flask_wtf import Form
from wtforms import HiddenField, IntegerField, BooleanField
from wtforms import TextAreaField, SelectField, StringField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Email
from base.pages.project.magic import project_config, get_transformation_options
from logging import error


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


def Transform(project):
    form = TransForm()
    form.name = project.name
    form.pid.data = project.id
    form.new.choices = get_transformation_options(project.type)
    return form


class RenewForm(Form):
    pid = HiddenField(validators=[DataRequired(
        message="Project id is missing")])
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    note = TextAreaField("Motivation", validators=[DataRequired(
        message="Motivation field is empty")])


def renew(project):
    config = project_config()
    project_type = project.type.lower()
    if project_type not in config.keys():
        error("Type %s is not found in config" % project_type)
        return None
    form = RenewForm()
    form.name = project.name
    form.pid.data = project.id
    end = config[project_type].get("finish_dt", None)
    if not end:
        error("Type %s has no end option and not renewable" % project_type)
        return None
    return form


class ExtendForm(Form):
    end_date = None
    eval_date = None
    eval_note = None

    pid = HiddenField(validators=[DataRequired(
        message="Project id is missing")])
    exception = BooleanField()
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    note = TextAreaField("Motivation", validators=[DataRequired(
        message="Motivation field is empty")])


def Allocate(project):
    config = project_config()
    project_type = project.type.lower()
    if project_type not in config.keys():
        return  # TODO: Check what to return in this case
    form = ExtendForm()
    form.name = project.name
    form.pid.data = project.id
    end = config[project_type].get("finish_dt", None)
    if end:
        form.end_date = end
    evaluation_date = config[project_type].get("evaluation_dt", None)
    if evaluation_date:
        evaluation_date.sort()
        form.eval_date = evaluation_date[0]
    evaluation_notice = config[project_type].get("evaluation_notice_dt", None)
    if evaluation_notice:
        evaluation_notice.sort()
        form.eval_note = evaluation_notice[0]
    return form


class UserForm(Form):
    pid_err = "Project id is missing"
    pid = HiddenField(validators=[DataRequired(message=pid_err)])
    prenom = StringField("Name")  # Can't use "name" cause it cause conflict
    surname = StringField("Surname")
    email = EmailField("E-mail")
    login = SelectField("Login", choices=[], coerce=int, default=0)
    create_user = False

    def validate(self):
        """
        Method which replaces standard validate method because of usage custom
        select2 field
        :return: Boolean
        """
        if not self.csrf_token.validate(self):
            return False
        if not self.pid.data:
            return ValidationError("Project ID expecting")
        if self.login.data:
            self.login.validate(self, [DataRequired()])
            return True
        if self.prenom.data and self.surname.data and self.email.data:
            self.prenom.validate(self, [DataRequired()])
            self.surname.validate(self, [DataRequired()])
            self.email.validate(self, [DataRequired(), Email()])
            self.create_user = True
            return True
        return ValidationError("Assign an existing user or add a new one")


def NewUser(project):
    form = UserForm()
    form.name = project.name
    form.pid.data = project.id
    return form
