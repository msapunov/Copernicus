from flask import request, g
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, HiddenField, SelectMultipleField
from wtforms import IntegerField, TextAreaField, FieldList, DateField, RadioField, SelectField
from wtforms.widgets import TextInput
from wtforms.validators import DataRequired, NumberRange, ValidationError, Email, InputRequired
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Email
from base.pages.project.magic import list_of_projects
from base.pages.login.form import MessageForm
from base.pages import process_new_user

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class RegForm(FlaskForm):
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
#    ttl = DateField("Valid", format='%d/%m/%y',
#                    render_kw={"data-uk-datepicker": "{format:'DD/MM/YYYY'}"})
    ttl = StringField(render_kw={"data-uk-datepicker": "{format:'DD/MM/YYYY'}"})
    title = StringField("Title", validators=[DataRequired(
        message="Project title is empty")])
    types = RadioField(choices=[], validators=[DataRequired(
        message="Project type is empty")])
    users = RadioField(choices=[('select', 'Select'), ('skip', 'Skip user creation')])
    exists = SelectField(choices=[], validators=[InputRequired()])

    def __init__(self, *args, **kwargs):
        super(RegForm, self).__init__(*args, **kwargs)
        types = g.project_config.keys()
        self.types.choices = [(project, project.upper()) for project in types]
        self.types.uk_length = len(self.types.choices)


def create_pending(register):
    form = RegForm()
    form.id = register.id
    form.meso = register.project_id()
    form.title_value = register.title
    form.cpu_value = register.cpu
    form.type_value = register.type
    users = register.users.split("\n")
    if register.responsible_email not in register.users:
        name = register.responsible_first_name.lower()
        sname = register.responsible_last_name.lower()
        email = register.responsible_email
        users.append("First Name: %s; Last Name: %s; E-mail: %s; Login:" % (
            name, sname, email))
    form.users = []
    for user in users:
        if not user:
            continue
        new_user = process_new_user(user)
        if not new_user:
            continue
        if register.responsible_email in new_user.email:
            new_user.admin = True
        else:
            new_user.admin = False
        form.users.append(new_user)
    form.process(formdata=request.form)
    return form


def contact_pending(register):
    form = MessageForm()
    form.id = register.id
    form.meso = register.project_id()
    form.title_value = "[%s] %s" % (form.meso, register.title)
    form.responsible = register.responsible_full_name()
    form.destination.value = register.responsible_email
    form.message_holder = "Write a message to %s" % form.responsible
    return form


def contact_user(user):
    form = MessageForm()
    form.id = user.login
    form.message_holder = "Write message to " + user.full()
    form.destination.value = user.email
    return form


class VisaPendingForm(FlaskForm):
    exception = BooleanField()


def visa_pending(register):
    form = VisaPendingForm()
    form.id = register.id
    form.meso = register.project_id()
    form.name = "'%s' (%s)" % (register.title, form.meso)
    form.status = register.status
    return form


class PendingActionForm(FlaskForm):
    note = TextAreaField("Note", validators=[DataRequired(
        message="Note field is empty")])


def action_pending(register):
    form = PendingActionForm()
    form.id = register.id
    form.meso = register.project_id()
    form.name = "'%s' (%s)" % (register.title, form.meso)
    return form


class EditProjectForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    cpu = IntegerField("CPU", validators=[DataRequired()])
    type = StringField("Type", validators=[DataRequired()])
    responsible_first_name = StringField("Responsible name", validators=[DataRequired()])
    responsible_last_name = StringField("Responsible surname", validators=[DataRequired()])
    responsible_email = EmailField("Responsible e-mail", validators=[DataRequired(), Email()])
    responsible_position = StringField("Responsible position", validators=[DataRequired()])
    responsible_lab = StringField("Responsible lab", validators=[DataRequired()])
    responsible_phone = StringField("Responsible phone", validators=[DataRequired()])


class AddUserForm(FlaskForm):
    prenom = StringField("Name", validators=[DataRequired()])
    surname = StringField("Surname", validators=[DataRequired()])
    email = EmailField("E-mail", validators=[DataRequired(), Email()])
    login = StringField("Login")


class SelectMultipleProjects(SelectMultipleField):
    def pre_validate(self, form):
        projects = list_of_projects()
        projects.append("None")
        for i in form.project.data:
            if i not in projects:
                raise ValueError("Project %s doesn't register in the DB" % i)


class RegistrationEditForm(FlaskForm):
    rid = HiddenField()
    cpu = IntegerField("CPU", validators=[NumberRange(
        min=0, message="CPU value must be 0 or any other positive number")])
    ttl = StringField(render_kw={"data-uk-datepicker": "{format:'DD/MM/YYYY'}"})
    title = StringField("Title", validators=[DataRequired(
        message="Project title is empty")])
    types = RadioField(choices=[], validators=[DataRequired(
        message="Project type is empty")])
    responsible_first_name = StringField("Responsible name", validators=[DataRequired()])
    responsible_last_name = StringField("Responsible surname", validators=[DataRequired()])
    responsible_email = EmailField("Responsible e-mail", validators=[DataRequired(), Email()])
    responsible_position = StringField("Responsible position", validators=[DataRequired()])
    responsible_lab = StringField("Responsible lab", validators=[DataRequired()])
    responsible_phone = StringField("Responsible phone", validators=[DataRequired()])
    description = TextAreaField()
    scientific = TextAreaField("Scientific fields")
    genci = TextAreaField("Genci")
    methods = TextAreaField()
    resources = TextAreaField()
    management = TextAreaField()
    motivation = TextAreaField()
    article_1 = StringField()
    article_2 = StringField()
    article_3 = StringField()
    article_4 = StringField()
    article_5 = StringField()

    def pre_validate(self, form):
        users = []
        for i in form.project.data:
            if i not in projects:
                raise ValueError("Project %s doesn't register in the DB" % i)

    def __init__(self, *args, **kwargs):
        super(RegistrationEditForm, self).__init__(*args, **kwargs)
        types = g.project_config.keys()
        self.types.choices = [(project, project.upper()) for project in types]
        self.types.uk_length = len(self.types.choices)


def edit_pending(register):
    form = RegistrationEditForm()
    form.id = register.id
    form.meso = register.project_id()
    form.title_value = register.title
    form.cpu_value = register.cpu
    form.type_value = register.type
    form.resp_first_value = register.responsible_first_name
    form.resp_last_value = register.responsible_last_name
    form.resp_mail_value = register.responsible_email
    form.resp_pos_value = register.responsible_position
    form.resp_lab_value = register.responsible_lab
    form.resp_phone_value = register.responsible_phone
    form.description.default = register.description
    form.resources.default = register.computing_resources
    form.management.default = register.project_management
    form.motivation.default = register.project_motivation
    form.methods.default = register.numerical_methods
    form.article_1.default = register.article_1
    form.article_2.default = register.article_2
    form.article_3.default = register.article_3
    form.article_4.default = register.article_4
    form.article_5.default = register.article_5
    users = register.users.split("\n")
    form.users = []
    for user in users:
        if not user:
            continue
        new_user = process_new_user(user)
        if not new_user:
            continue
        form.users.append(new_user)
    form.process(formdata=request.form)
    return form


class NewUserEditForm(FlaskForm):
    pid = HiddenField()
    uid = HiddenField()
    user_first_name = StringField("Name", validators=[DataRequired()])
    user_last_name = StringField("Surname", validators=[DataRequired()])
    user_email = EmailField("E-mail", validators=[DataRequired(), Email()])
    user_login = StringField("Login")


class UserEditForm(FlaskForm):
    uid = HiddenField()
    login = StringField("Login", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    surname = StringField("Surname", validators=[DataRequired()])
    email = EmailField("Surname", validators=[DataRequired(), Email()])
    project = SelectMultipleProjects("Project", choices=[])
    active = BooleanField("Active", default=True)
    is_user = BooleanField("User", default=True)
    is_responsible = BooleanField("Responsible", default=False)
    is_manager = BooleanField("Manager", default=False)
    is_tech = BooleanField("Tech", default=False)
    is_committee = BooleanField("Committee", default=False)
    is_admin = BooleanField("Admin", default=False)

    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        projects = list_of_projects()
        self.project.choices = [(project, project) for project in projects]


def activate_user(user):
    form = ActivateUserForm()
    form.id = user.id
    form.login = user.login
    form.full = user.full_name()
    form.complete = user.full()
    form.project = list(map(lambda x: x.get_name(), user.project))
    form.projects.process_data(form.project)
    return form


class ActivateUserForm(FlaskForm):
    exception = BooleanField()
    login = HiddenField()
    projects = SelectMultipleProjects("Project", choices=[])

    def __init__(self, *args, **kwargs):
        super(ActivateUserForm, self).__init__(*args, **kwargs)
        projects = list_of_projects()
        self.projects.choices = [(project, project) for project in projects]
