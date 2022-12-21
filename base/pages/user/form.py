from flask_wtf import FlaskForm
from wtforms import StringField, EmailField


class InfoForm(FlaskForm):
    prenom = StringField("Name")
    surname = StringField("Surname")
    email = EmailField("E-mail")


class KeyForm(FlaskForm):
    key = StringField("Key")


def edit_info(user):
    form = InfoForm()
    form.username = user.login
    form.prenom.data = user.name
    form.surname.data = user.surname
    form.email.data = user.email
    return form
