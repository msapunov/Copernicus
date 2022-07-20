from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, HiddenField, SelectMultipleField
from wtforms import IntegerField, TextAreaField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email
from base.pages.project.magic import list_of_projects
from base.pages.login.form import MessageForm

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def contact_pending(register):
    form = MessageForm()
    form.id = register.id
    form.meso = register.project_id()
    form.project_title = register.title
    form.responsible = register.responsible_full_name()
    form.destination = register.responsible_email
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


class CreateProjectForm(FlaskForm):
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
    title = StringField("Title", validators=[DataRequired()])
    cpu = IntegerField("CPU", validators=[DataRequired()])
    type = StringField("Type", validators=[DataRequired()])
    responsible_first_name = StringField("Responsible name", validators=[DataRequired()])
    responsible_last_name = StringField("Responsible surname", validators=[DataRequired()])
    responsible_email = EmailField("Responsible e-mail", validators=[DataRequired(), Email()])
    responsible_position = StringField("Responsible position", validators=[DataRequired()])
    responsible_lab = StringField("Responsible lab", validators=[DataRequired()])
    responsible_phone = StringField("Responsible phone", validators=[DataRequired()])


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
