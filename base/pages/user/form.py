from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.fields.html5 import EmailField


class InfoForm(FlaskForm):
    prenom = StringField("Name")
    surname = StringField("Surname")
    email = EmailField("E-mail")


def EditInfo(user):
    form = InfoForm()
    form.username = user.login
    form.prenom.data = user.name
    form.surname.data = user.surname
    form.email.data = user.email
    return form
