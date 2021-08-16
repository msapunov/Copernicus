from flask_wtf import Form
from wtforms import HiddenField, StringField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired


class InfoForm(Form):
    login_err = "User login name is missing"
    name_err = "CPU value must be 0 or any other positive number"
    surname_err = ""
    mail_err = ""

    login = HiddenField(validators=[DataRequired(message=login_err)])
    prenom = StringField("Name")
    surname = StringField("Surname")
    email = EmailField("E-mail")


def EditInfo(user):
    form = InfoForm()
    form.username = user.login
    form.login.data = user.login
    form.prenom.data = user.name
    form.surname.data = user.surname
    form.email.data = user.email
    return form
