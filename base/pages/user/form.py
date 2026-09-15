"""WTForms for user information editing and SSH key upload."""

from flask_wtf import FlaskForm
from wtforms import EmailField, HiddenField, StringField


class InfoForm(FlaskForm):
    """Form for editing user personal information."""

    prenom = StringField("Name")
    surname = StringField("Surname")
    email = EmailField("E-mail")


class KeyForm(FlaskForm):
    """Form for uploading an SSH public key."""

    key = StringField("Key")
    login = HiddenField()


def edit_info(user):
    """Create an InfoForm pre-populated with a user's current data.

    Args:
        user: User instance.

    Returns:
        An InfoForm instance.
    """
    form = InfoForm()
    form.username = user.login
    form.prenom.data = user.name
    form.surname.data = user.surname
    form.email.data = user.email
    return form


class PassForm(FlaskForm):
    """Form for manually setting a user's password."""

    password = StringField("Password")


def set_password(user):
    """Create a PassForm for a given user.

    Args:
        user: User instance.

    Returns:
        A PassForm instance.
    """
    form = PassForm()
    form.id = user.id
    form.login = user.login
    form.fullname = user.full_name()
    return form
