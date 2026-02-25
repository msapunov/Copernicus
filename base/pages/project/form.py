from flask import g
from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, BooleanField
from wtforms import TextAreaField, SelectField, StringField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Email
from wtforms.validators import Optional
from base.classes import BaseForm
from base.pages.project.magic import (
    get_transformation_options,
    get_project_option,
    get_users)
from logging import error

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class ActivateForm(FlaskForm):
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    note = TextAreaField("Motivation", validators=[DataRequired(
        message="Motivation field is empty")])


def activate(project):
    form = ActivateForm()
    form.name = project.name
    return form


class TransForm(FlaskForm):
    new = SelectField("New type", validators=[DataRequired(
        message="New type is missing")])
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    note = TextAreaField("Motivation", validators=[DataRequired(
        message="Motivation field is empty")])


def transform(project):
    form = TransForm()
    form.name = project.name
    form.new.choices = get_transformation_options(project.type)
    return form


class RenewForm(FlaskForm):
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    note = TextAreaField("Motivation", validators=[DataRequired(
        message="Motivation field is empty")])


def renew(project):
    config = g.project_config
    project_type = project.type.lower()
    if project_type not in config.keys():
        error(f"Type {project_type} is not found in config")
        return None
    if not get_project_option(project, "renewable"):
        error(f"Project of type {project_type} is not renewable")
        return None
    form = RenewForm()
    form.name = project.name
    end = config[project_type].get("finish_dt", None)
    if not end:
        error("Type %s has no end option and not renewable" % project_type)
        return None
    return form


class ExtendForm(FlaskForm):
    end_date = None
    eval_date = None
    eval_note = None

    exception = BooleanField()
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    note = TextAreaField("Motivation", validators=[DataRequired(
        message="Motivation field is empty")])


def extend(project):
    config = g.project_config
    project_type = project.type.lower()
    if project_type not in config.keys():
        return  # TODO: Check what to return in this case
    form = ExtendForm()
    form.name = project.name
    end = config[project_type].get("finish_dt", None)
    if end:
        form.end_date = end
    evaluation = config[project_type].get("evaluation_dt", None)
    if evaluation is None:
        form.eval_date = None
    elif isinstance(evaluation, list):
        form.eval_date = sorted(evaluation)[0] if evaluation else None
    else:
        form.eval_date = evaluation
    notice = config[project_type].get("evaluation_notice_dt", None)
    if notice is None:
        form.eval_note = None
    elif isinstance(notice, list):
        form.eval_note = sorted(notice)[0] if notice else None
    else:
        form.eval_note = notice
    return form


class ResponsibleForm(FlaskForm):
    login = SelectField("Login", choices=[("", "---")], default=0)
    send = BooleanField(default="checked")

    def validate(self, extra_validators=None):
        if self.login.data:
            self.login.validate(self, [DataRequired()])
            return True


def new_responsible(project, is_admin):
    form = ResponsibleForm()
    form.name = project.name
    form.responsible = project.responsible.full()
    if is_admin:
        users = get_users()
    else:
        users = get_users(project)
        if project.responsible in users:
            users.remove(project.responsible)
    for u in users:
        form.login.choices.append((u.id, u.full()))
    return form


class UserForm(BaseForm):
    prenom = StringField("Name", validators=[DataRequired()])  # Can't use "name" cause it causes conflict
    surname = StringField("Surname", validators=[DataRequired()])
    email = EmailField("E-mail", validators=[DataRequired(), Email()])
    login = SelectField("Login", choices=[], coerce=int, default=0,
                        validate_choice=False)
    create_user = False
    key = StringField("Key", validators=[Optional()])

    def validate(self, extra_validators=None):
        """
        Method which replaces standard validate method because of usage custom
        select2 field
        :return: Boolean
        """
        required = (self.prenom, self.surname, self.email)
        select_old = bool(self.login.data)
        create_new = any(field.data for field in required)
        msg = "existing user or fill name, surname and email to create new user"
        if select_old and create_new:
            raise ValidationError(f"Choose either {msg}")
        if not select_old and not create_new:
            raise ValidationError(f"You must select {msg}")

        if select_old:
            return self.login.validate(self)

        for field in required:
            if not field.validate(self):
                return False
        if self.key.data:
            if not self.key.validate(self):
                return False
        self.create_user = True
        return True


def new_user(project):
    form = UserForm()
    form.name = project.name
    form.ssh = getattr(project, "ssh_upload", False)
    return form


class ActivityForm(FlaskForm):
    report = TextAreaField("report", validators=[DataRequired(
        message="Report field is empty")])
    doi = TextAreaField("list_of_publications")
    training = TextAreaField("training_activity")
    hiring = TextAreaField("Hiring")
    image_1 = HiddenField("image_1")
    image_2 = HiddenField("image_2")
    image_3 = HiddenField("image_3")


def activity(project):
    form = ActivityForm()
    form.name = project.name
    return form
