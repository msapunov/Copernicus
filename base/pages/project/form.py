from flask_wtf import Form
from wtforms import HiddenField, IntegerField, BooleanField
from wtforms import TextAreaField, SelectField, StringField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Email
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


def get_transformation_options(project_type=None):
    config = project_config()
    options = []
    for name in config.keys():
        desc = config[name].get("description", None)
        options.append((name.lower(), desc if desc else name))

    if (not project_type) or (project_type not in config.keys()):
        return options

    trans = config[project_type].get("transform", None)
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
    form.new.choices = get_transformation_options(project.type)
    return form


class ExtendForm(Form):
    end_date = None
    eval_date = None
    eval_note = None
    pid_err = "Project id is missing"
    cpu_err = "CPU value must be 0 or any other positive number"
    err = "Motivation field is empty"

    pid = HiddenField(validators=[DataRequired(message=pid_err)])
    exception = BooleanField()
    cpu = IntegerField("CPU", validators=[NumberRange(min=0, message=cpu_err)])
    note = TextAreaField("Motivation", validators=[DataRequired(message=err)])


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
