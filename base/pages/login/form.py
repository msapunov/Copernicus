from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, HiddenField
from wtforms.validators import DataRequired


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class ResetForm(FlaskForm):
    old = PasswordField("OldPassword", validators=[DataRequired()])
    new_passw = PasswordField("NewPassword", validators=[DataRequired()])
    conf_passw = PasswordField("ConfirmPassword", validators=[DataRequired()])


class LoginForm(FlaskForm):
    login = StringField("Login", validators=[DataRequired()])
    passw = PasswordField("Password", validators=[DataRequired()])
