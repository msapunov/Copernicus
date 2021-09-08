from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    login = StringField("Login", validators=[DataRequired()])
    passw = PasswordField("Password", validators=[DataRequired()])
