from flask import g
from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, BooleanField
from wtforms import TextAreaField, SelectField, StringField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, NumberRange, ValidationError, Email
from base.classes import BaseForm
from base.pages.project.magic import (
    get_transformation_options,
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
        error("Type %s is not found in config" % project_type)
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


class UserForm(FlaskForm):
    prenom = StringField("Name")  # Can't use "name" cause it causes conflict
    surname = StringField("Surname")
    email = EmailField("E-mail")
    login = SelectField("Login", choices=[], coerce=int, default=0)
    create_user = False
    ssh = False
    key = StringField("Key")

    def validate(self, extra_validators=None):
        """
        Method which replaces standard validate method because of usage custom
        select2 field
        :return: Boolean
        """
        if not super().validate(extra_validators):
            return False
        if self.login.data:
            return True
        required = (self.prenom, self.surname, self.email)
        if any(f.data for f in required):
            missing = [f.label.text for f in required if not f.data]
            if self.key.data is not None and not self.key.data:
                missing.append(self.key.label.text)
            if missing:
                self.login.errors.append(
                    f"Please fill the following field(s): {', '.join(missing)}"
                )
                return False
            self.create_user = True
            return True

        self.login.errors.append(
            "You have to either assign an existing user or add a new one "
            "by providing values for fields Name, Surname, and Email."
        )
        return False


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
