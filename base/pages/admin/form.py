"""WTForms for the admin blueprint: registration, user management,
pending requests, and task editing.
"""

from logging import error
from string import ascii_letters as ascii

from flask import g, request
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    Field,
    HiddenField,
    IntegerField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
)
from wtforms.fields import EmailField
from wtforms.validators import (
    DataRequired,
    Email,
    NumberRange,
)

from base.functions import full_name, process_register_user
from base.pages import generate_login, user_by_details
from base.pages.login.form import MessageForm
from base.pages.project.form import UserForm
from base.pages.project.magic import list_of_projects

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class CreateForm(FlaskForm):
    """Form for creating a new project from a registration request."""

    user = HiddenField()
    prenom = HiddenField()
    surname = HiddenField()
    email = HiddenField()
    responsible = HiddenField()
    login = RadioField("Login", choices=[])
    exist = StringField()

    def validate(self, extra_validators=None):
        """Validate that CSRF token and user field are present.

        Args:
            extra_validators: Not used.

        Returns:
            True if valid.
        """
        if not self.csrf_token.validate(self):
            return False
        if not self.user.validate(self, [DataRequired()]):
            return False
        return True


def create_pending(register):
    """Build a list of CreateForm instances for users in a registration record.

    Parses the user list from the registration, generates login suggestions,
    and checks for existing users.

    Args:
        register: Register record.

    Returns:
        List of CreateForm instances.
    """
    result = []
    raw = register.users.split("\n")
    if register.responsible_email not in register.users:
        name = register.responsible_first_name.lower()
        sname = register.responsible_last_name.lower()
        email = register.responsible_email
        raw.append("First Name: %s; Last Name: %s; E-mail: %s; Login:" % (
            name, sname, email))
    users = [x for x in raw if x]
    for num, user in enumerate(users):
        form = CreateForm(prefix=str(num))
        name, surname, email, login = process_register_user(user)
        if None in (name, surname, email, login):
            error(
                f"Function process_register_user({user}) returned:"
                f"name: {name}, surname: {surname}, email: {email}, "
                f"login: {login}. Skipping processing of this record"
            )
            continue
        form.uid = "".join(filter(lambda x: x in ascii, email)).lower()
        form.user.data = "%s <%s>" % (full_name(name, surname), email)
        form.prenom.data = name
        form.surname.data = surname
        form.email.data = email
        direct = generate_login(name, surname)
        invert = generate_login(surname, name)
        form.login.choices = [
            (direct, "Create a new user: %s" % direct),
            (invert, "Create a new user: %s" % invert),
            ("select", ""),
        ]
        already = user_by_details(name, surname, email, login)
        if already:
            form.exist = already[0].login
            form.login.data = "select"
        else:
            form.exist = ""
            form.login.data = direct
        if email in register.responsible_email:
            form.admin = True
        else:
            form.admin = False
            form.login.choices.append(("none", "Skip user creation"))
        result.append(form)
    return result


def contact_pending(register):
    """Create a MessageForm for contacting the responsible about a pending request.

    Args:
        register: Register record.

    Returns:
        A MessageForm instance.
    """
    form = MessageForm()
    form.id = register.id
    form.meso = register.project_id()
    form.title_value = "[%s] %s" % (form.meso, register.title)
    form.responsible = register.responsible_full_name()
    form.destination.value = register.responsible_email
    form.message_holder = "Write a message to %s" % form.responsible
    form.css_class = "pending_message_submit"
    return form


def contact_user(user):
    """Create a MessageForm for contacting a user.

    Args:
        user: User instance.

    Returns:
        A MessageForm instance.
    """
    form = MessageForm()
    form.id = user.login
    form.message_holder = "Write message to " + user.full()
    form.destination.value = user.email
    return form


class VisaPendingForm(FlaskForm):
    """Form for visa-related actions (skip if exception)."""

    exception = BooleanField()


def visa_pending(register):
    """Create a VisaPendingForm for a registration record.

    Args:
        register: Register record.

    Returns:
        A VisaPendingForm instance.
    """
    form = VisaPendingForm()
    form.id = register.id
    form.meso = register.project_id()
    form.name = "'%s' (%s)" % (register.title, form.meso)
    form.status = register.status
    return form


class PendingActionForm(FlaskForm):
    """Form for rejection notes on pending registrations."""

    note = TextAreaField(
        "Note", validators=[DataRequired(message="Note field is empty")]
    )


def action_pending(register):
    """Create a PendingActionForm for a registration record.

    Args:
        register: Register record.

    Returns:
        A PendingActionForm instance.
    """
    form = PendingActionForm()
    form.id = register.id
    form.meso = register.project_id()
    form.name = "'%s' (%s)" % (register.title, form.meso)
    return form


class AddUserForm(FlaskForm):
    """Form for adding a new user directly (admin)."""

    prenom = StringField("Name", validators=[DataRequired()])
    surname = StringField("Surname", validators=[DataRequired()])
    email = EmailField("E-mail", validators=[DataRequired(), Email()])
    login = StringField("Login")


class SelectMultipleProjects(SelectMultipleField):
    """Multi-select field for project names with validation."""

    def pre_validate(self, form):
        """Validate that all selected projects exist.

        Args:
            form: The parent form.

        Raises:
            ValueError: If a selected project does not exist.
        """
        projects = list_of_projects()
        projects.append("None")
        for i in form.project.data:
            if i not in projects:
                raise ValueError("Project %s doesn't register in the DB" % i)


class RegistrationEditForm(FlaskForm):

    cpu = IntegerField(
        "CPU",
        validators=[
            NumberRange(
                min=0, message="CPU value must be 0 or any other positive number"
            )
        ],
    )
    ttl = StringField(render_kw={"data-uk-datepicker": "{format:'DD/MM/YYYY'}"})
    title = StringField(
        "Title", validators=[DataRequired(message="Project title is empty")]
    )
    type = RadioField(
        choices=[], validators=[DataRequired(message="Project type is empty")]
    )
    description = TextAreaField("Description")
    scientific_fields = StringField("Scientific fields")
    genci_committee = Field(
        "Genci", validators=[DataRequired(message="Genci field is empty")]
    )
    numerical_methods = TextAreaField("Methods")
    computing_resources = TextAreaField("Resources")
    project_management = TextAreaField("Management")
    project_motivation = TextAreaField("Motivation")
    article_1 = StringField("Article 1")
    article_2 = StringField("Article 2")
    article_3 = StringField("Article 3")
    article_4 = StringField("Article 4")
    article_5 = StringField("Article 5")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        types = g.project_config.keys()
        self.type.choices = [(project, project.upper()) for project in types]
        self.type.uk_length = len(self.type.choices)


def edit_pending(register):
    """Create a RegistrationEditForm pre-populated from a Register record.

    Args:
        register: Register record.

    Returns:
        A RegistrationEditForm instance.
    """
    form = RegistrationEditForm()
    form.id = register.id
    form.meso = register.project_id()
    form.title_value = register.title
    form.cpu_value = register.cpu
    form.type_value = register.type
    form.description.default = register.description
    form.computing_resources.default = register.computing_resources
    form.project_management.default = register.project_management
    form.project_motivation.default = register.project_motivation
    form.numerical_methods.default = register.numerical_methods
    form.scientific_fields.default = register.scientific_fields
    form.genci_committee.default = register.genci_committee.lower()
    form.article_1.default = register.article_1
    form.article_2.default = register.article_2
    form.article_3.default = register.article_3
    form.article_4.default = register.article_4
    form.article_5.default = register.article_5
    form.process(formdata=request.form)
    return form


class EditResponsibleForm(UserForm):

    position = StringField(
        "Position", validators=[DataRequired(message="Login field is empty")]
    )
    lab = StringField("Lab", validators=[DataRequired(message="Login field is empty")])
    phone = StringField(
        "Phone", validators=[DataRequired(message="Login field is empty")]
    )


def edit_responsible(register):
    """Create an EditResponsibleForm pre-populated from a Register record.

    Args:
        register: Register record.

    Returns:
        An EditResponsibleForm instance.
    """
    form = EditResponsibleForm()
    form.prenom.data = register.responsible_first_name
    form.surname.data = register.responsible_last_name
    form.email.data = register.responsible_email
    form.position.data = register.responsible_position
    form.lab.data = register.responsible_lab
    form.phone.data = register.responsible_phone
    form.name = register.project_id()
    form.pending_id = register.id
    return form


class NewUserForm(UserForm):
    """Form for adding a new user to a registration (login as free text)."""

    login = StringField("Login")

    def validate(self, extra_validators=None):
        """Validate that name, surname, email, and CSRF token are present.

        Args:
            extra_validators: Not used.

        Returns:
            True if valid.
        """
        if not self.csrf_token.validate(self):
            return False
        if not self.prenom.validate(self, [DataRequired()]):
            return False
        if not self.surname.validate(self, [DataRequired()]):
            return False
        if not self.email.validate(self, [DataRequired(), Email()]):
            return False
        return True


def new_user(register):
    """Create a NewUserForm for adding a user to a registration.

    Args:
        register: Register record.

    Returns:
        A NewUserForm instance.
    """
    form = NewUserForm()
    form.name = register.project_id()
    form.pending_id = register.id
    return form


def edit_user(users):
    """Create a list of NewUserForm instances from a registration's user list.

    Args:
        users: Newline-separated user string from the registration record.

    Returns:
        List of NewUserForm instances.
    """
    result = []
    if not users:
        return result
    for num, user in enumerate(users.strip().split("\n")):
        form = NewUserForm(prefix=str(num))
        name, surname, email, login = process_register_user(user)
        form.prenom.data = name
        form.surname.data = surname
        form.email.data = email
        form.login.data = login
        form.full = f"{name} {surname}"
        result.append(form)
    return result


class NewUserEditForm(FlaskForm):
    """Form for editing a single user in a registration."""

    pid = HiddenField()
    uid = HiddenField()
    user_first_name = StringField("Name", validators=[DataRequired()])
    user_last_name = StringField("Surname", validators=[DataRequired()])
    user_email = EmailField("E-mail", validators=[DataRequired(), Email()])
    user_login = StringField("Login")


class UserEditForm(FlaskForm):
    """Comprehensive form for editing all user properties."""

    uid = HiddenField()
    login = StringField("Login", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    surname = StringField("Surname", validators=[DataRequired()])
    email = EmailField("Surname", validators=[DataRequired(), Email()])
    project = SelectMultipleProjects("Project", choices=[])
    active = BooleanField("Active", default=True)
    is_user = BooleanField("User", default=True)
    is_responsible = BooleanField("Responsible", default=False)
    is_manager = BooleanField("Manager", default=False)
    is_tech = BooleanField("Tech", default=False)
    is_committee = BooleanField("Committee", default=False)
    is_admin = BooleanField("Admin", default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        projects = list_of_projects()
        self.project.choices = [(project, project) for project in projects]


def activate_user(user):
    """Create an ActivateUserForm for reactivating a user.

    Args:
        user: User instance.

    Returns:
        An ActivateUserForm instance.
    """
    form = ActivateUserForm()
    form.id = user.id
    form.login = user.login
    form.full = user.full_name()
    form.complete = user.full()
    form.project = list(map(lambda x: x.get_name(), user.project))
    form.projects.process_data(form.project)
    return form


class ActivateUserForm(FlaskForm):
    """Form for activating a user and selecting project membership."""

    exception = BooleanField()
    login = HiddenField()
    projects = SelectMultipleProjects("Project", choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        projects = list_of_projects()
        self.projects.choices = [(project, project) for project in projects]


class TaskEditForm(FlaskForm):

    processed = SelectField(
        "Processed",
        choices=[("true", "Processed: True"), ("false", "Processed: False")],
    )
    done = SelectField(
        "Done", choices=[("true", "Done: True"), ("false", "Done: False")]
    )
    decision = SelectField(
        "Decision",
        choices=[
            ("none", "Decision: None"),
            ("accept", "Decision: Accept"),
            ("ignore", "Decision: Ignore"),
            ("reject", "Decision: Reject"),
        ],
    )


def edit_task(task):
    """Create a TaskEditForm pre-populated from a Tasks record.

    Args:
        task: Tasks instance.

    Returns:
        A TaskEditForm instance.
    """
    processed = str(task.processed).lower()
    done = str(task.done).lower()
    decision = "none" if not task.decision else str(task.decision).lower()
    form = TaskEditForm(processed=processed, done=done, decision=decision)
    return form
