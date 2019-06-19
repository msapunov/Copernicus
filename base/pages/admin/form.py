from flask_wtf import Form
from wtforms import StringField, BooleanField, HiddenField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email


class UserEditForm(Form):
    uid = HiddenField(validators=[DataRequired()])
    login = StringField("Login", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    surname = StringField("Surname", validators=[DataRequired()])
    email = EmailField("Surname", validators=[DataRequired(), Email()])
    active = BooleanField("Surname", default=True, validators=[DataRequired()])
    is_user = BooleanField("User", default=True, validators=[DataRequired()])
    is_responsible = BooleanField("Responsible", validators=[DataRequired()])
    is_manager = BooleanField("Manager", validators=[DataRequired()])
    is_tech = BooleanField("Tech", validators=[DataRequired()])
    is_committee = BooleanField("Committee", validators=[DataRequired()])
    is_admin = BooleanField("Admin", validators=[DataRequired()])
