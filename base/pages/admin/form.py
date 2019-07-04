from flask_wtf import Form
from wtforms import StringField, BooleanField, HiddenField, SelectMultipleField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email
from base.pages.project.magic import list_of_projects


class SelectMultipleProjects(SelectMultipleField):
    def pre_validate(self, form):
        projects = list_of_projects()
        projects.append("None")
        for i in form.project.data:
            if i not in projects:
                raise ValueError("Project %s doesn't register in the DB" % i)


class UserEditForm(Form):
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
