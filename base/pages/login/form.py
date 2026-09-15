"""WTForms for login, password reset, and simple messaging."""

from flask_wtf import FlaskForm
from wtforms import HiddenField, PasswordField, StringField, TextAreaField
from wtforms.validators import DataRequired

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class MessageForm(FlaskForm):
    """Form for sending a simple message to a user."""

    destination = HiddenField(validators=[DataRequired()])
    title = StringField("Title", validators=[DataRequired()])
    message = TextAreaField(
        "Message", validators=[DataRequired(message="Message field is empty")]
    )


class ResetForm(FlaskForm):
    """Form for changing the current user's password."""

    old = PasswordField("OldPassword", validators=[DataRequired()])
    new_passw = PasswordField("NewPassword", validators=[DataRequired()])
    conf_passw = PasswordField("ConfirmPassword", validators=[DataRequired()])


class LoginForm(FlaskForm):
    """Form for user login with username and password."""

    login = StringField("Login", validators=[DataRequired()])
    passw = PasswordField("Password", validators=[DataRequired()])
