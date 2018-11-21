from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired


class LoginForm(Form):
    login = StringField("Login", validators=[DataRequired()])
    passwd = StringField("Password", validators=[DataRequired()])
