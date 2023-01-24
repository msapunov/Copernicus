from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired


class MessageForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    message = TextAreaField("Message", validators=[DataRequired(
        message="Message field is empty")])


class ResetForm(FlaskForm):
    old = PasswordField("OldPassword", validators=[DataRequired()])
    new_passw = PasswordField("NewPassword", validators=[DataRequired()])
    conf_passw = PasswordField("ConfirmPassword", validators=[DataRequired()])


class LoginForm(FlaskForm):
    login = StringField("Login", validators=[DataRequired()])
    passw = PasswordField("Password", validators=[DataRequired()])
