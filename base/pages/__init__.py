from flask import current_app, request, flash, redirect, url_for, g
from flask_login import current_user, logout_user
from pathlib import Path
from logging import debug, error
from functools import wraps
from base import db
from base.email import Mail
from base.database.schema import User, Tasks
from base.utils import normalize_word
from base.functions import generate_password, full_name
from string import ascii_letters

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import formatdate


def grant_access(*roles):
    def log_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            url = request.full_path
            for role in roles:
                if role in g.permissions:
                    return f(*args, **kwargs)
            if request.is_json:
                return "Permissions denied based on user role", 403
            error("Available user roles doesn't permit to access URL: %s" % url)
            flash("Permissions denied to access URL: %s" % url)
            logout_user()
            return redirect(url_for("login.login"))
        return decorated_function
    return log_required


def check_str(raw_note):
    note = str(raw_note)
    if (not note) or (len(note) < 1):
        raise ValueError("Provided string can't be empty")
    return note


def calculate_usage(use, total):
    try:
        use = "{0:.1%}".format(float(use) / float(total))
        return float(use.replace("%", ""))
    except TypeError as err:
        error("Failed to calculate project usage: %s" % err)
        return ""


def generate_login(name, surname):
    users = User.query.all()
    logins = list(map(lambda x: x.login, users))

    name = normalize_word(name)
    name = "".join(filter(lambda x: x in ascii_letters, name)).lower()
    surname = normalize_word(surname)
    surname = "".join(filter(lambda x: x in ascii_letters, surname)).lower()

    i = 1
    guess = None
    while i < len(name):
        guess = name[0:i] + surname
        if guess not in logins:
            return guess
        i += 1
    raise ValueError("Seems that user with login '%s' has been already"
                     " registered in our database" % guess)


def send_message(to_who, by_who=None, cc=None, title=None, message=None,
                 attach=None):  # TODO: replace by mail class
    if isinstance(to_who, str):
        to_who = to_who.split(";")
    if not by_who:
        by_who = current_app.config["EMAIL_TECH"]
    if not title:
        title = "Mesocentre reporting"
    if not cc:
        cc = [current_app.config["EMAIL_TECH"]]
    if isinstance(cc, str):
        cc = cc.split(";")
    if not message:
        debug("Message body is empty")
    if isinstance(attach, str):
        attach = attach.split(";")

    msg = MIMEMultipart()
    msg["Subject"] = title
    msg["From"] = by_who
    msg["To"] = ", ".join(to_who)
    msg["Date"] = formatdate(localtime=True)
    msg["Cc"] = ", ".join(cc)
    if message:
        msg.attach(MIMEText(message))

    for path in attach or []:
        attach_file = Path(path)
        if not attach_file.exists():
            raise ValueError("Failed to attach %s to the mail. "
                             "File doesn't exists" % path)
        if not attach_file.is_file():
            raise ValueError("Failed to attach %s to the mail. It's not a file"
                             % path)
        with open(path, "rb") as fd:
            part = MIMEApplication(fd.read(), Name=str(attach_file.name))
        part['Content-Disposition'] = 'attachment; filename="%s"' % str(attach_file.name)
        msg.attach(part)

    server = current_app.config.get("MAIL_SERVER", "localhost")
    port = current_app.config.get("MAIL_PORT", 25)
    use_tls = current_app.config.get("MAIL_USE_TLS", False)
    use_ssl = current_app.config.get("MAIL_USE_SSL", False)
    username = current_app.config.get("MAIL_USERNAME", None)
    password = current_app.config.get("MAIL_PASSWORD", None)

    if use_ssl:
        smtp = smtplib.SMTP_SSL(server, port)
    else:
        smtp = smtplib.SMTP(server, port)
    if use_tls:
        smtp.starttls()
    if username and password:
        smtp.login(username, password)

    to = ", ".join(to_who) + ", ".join(cc)
    if current_app.config.get("MAIL_SEND", False):
        smtp.send_message(msg)
    smtp.quit()
    return "Message was sent to %s successfully" % ", ".join(to_who)


def check_json():  # TODO: remove - replace
    if not request.is_json:
        raise ValueError("Expecting application/json requests")
    data = request.get_json()
    if not data:
        raise ValueError("Empty JSON request received")
    debug("Incoming JSON: %s" % data)
    return data


class Task:

    def __init__(self, tid):
        task = Tasks().query.filter_by(id=tid).first()
        if not task:
            raise ValueError("No task with id %s found" % tid)
        self.task = task
        self.id = task.id

    def _update_user(self):
        limbo = self.task.limbo_user
        user = User().query.filter_by(id=limbo.ref_id).one()

        for key in db.inspect(User).columns.keys():
            if key in ["id", "login"]:
                continue
            if hasattr(limbo, key):
                val = getattr(limbo, key)
                setattr(user, key, val)
        db.session.delete(limbo)
        db.session.commit()
        return user

    def _execute(self):
        if "update" in self.task.action and self.task.limbo_user:
            return self._update_user()

    def is_processed(self):
        return self.task.processed

    def process(self):
        self.task.processed = True
        self._commit()
        return True

    def done(self):
        self.task.done = True
        self._commit()
        self._execute()
        return True

    def description(self):
        return self.task.description()

    def accept(self):
        self.task.decision = "accept"
        Mail().task_accepted(self.task).send()
        return self._action()

    def ignore(self):
        self.task.decision = "ignore"
        return self._action()

    def reject(self):
        self.task.decision = "reject"
        Mail().task_rejected(self.task).send()
        return self._action()

    def action(self):
        return self.task.action

    def update(self, data):
        for prop in ["pending", "processed", "done", "decision"]:
            value = str(data[prop])
            if value not in ["accept", "ignore", "reject", "true", "false"]:
                value = None
            else:
                if value == "true":
                    value = True
                elif value == "false":
                    value = False
            setattr(self.task, prop, value)
        self._commit()
        return self.task

    def _action(self):
        self.task.processed = True
        self.task.approve = current_user
        self._commit()
        return self.task

    @staticmethod
    def _commit():
        db.session.commit()


class TaskQueue:

    def __init__(self):
        self.task = Tasks(author=current_user, processed=False, done=False)
        self.u_name = None  # User login name. String
        self.p_name = None  # Project name. String

    def user(self, user_obj):
        self.u_name = user_obj.login
        self.task.user = user_obj
        return self

    def project(self, project_obj):
        self.p_name = project_obj.get_name()
        self.task.project = project_obj
        return self

    def key_upload(self, key):
        if not self.u_name:
            raise ValueError("User is  not set. Can't upload SSH key")
        self.task.action = "ssh|user|%s||%s" % (self.u_name, key)
        double = Tasks().query.filter_by(
            action=self.task.action
        ).filter_by(
            done=False, decision="accept"
        ).first()
        if double:
            raise ValueError("Same previous task found ID: %s" % double.id)
        return self._user_action()

    def user_create(self, user): #!!!
        if not self.p_name:
            raise ValueError("Can't add a user to none existent project")
        description = user.ready_task()
        self.task.action = "create|user|%s|%s|%s" % (user.login, self.p_name,
                                                     description)
        return self._user_action()

    def responsible_create(self, user):
        if not self.p_name:
            raise ValueError("Can't add a user to none existent project")
        description = user.ready_task()
        self.task.action = "create|resp|%s|%s|%s" % (user.login, self.p_name,
                                                     description)
        return self._user_action()

    def user_activate(self, user):
        if not self.project:
            raise ValueError("Can't activate user for none existent project")
        if not hasattr(user, "password"):
            user.password = generate_password()
        description = "login: %s and name: %s and surname: %s and email: %s" \
                      " AND PASSWORD %s" % (user.login, user.name, user.surname,
                                            user.email, user.password)
        self.task.action = "activate|user|%s|%s|%s" % (user.login, self.p_name,
                                                       description)
        self.task.user = user
        return self._user_action()

    def user_assign(self, user):
        if not self.project:
            raise ValueError("Can't assign a user to none existent project")
        login = user.login
        description = "Assign user %s to project %s" % (login, self.p_name)
        self.task.action = "assign|user|%s|%s|%s" % (login, self.p_name,
                                                     description)
        self.task.user = user
        return self._user_action()

    def responsible_assign(self, user):
        if not self.project:
            raise ValueError("Can't assign a new responsible to none existent"
                             " project")
        login = user.login
        description = "Assign responsible %s to project %s" % (login,
                                                               self.p_name)
        self.task.action = "assign|resp|%s|%s|%s" % (login, self.p_name,
                                                     description)
        self.task.user = user
        return self._user_action()

    def user_update(self, data):
        if not self.task.user:
            raise ValueError("Can't update information of unset user")
        tmp_user = self.task.user
        login = tmp_user.login
        act = []
        for key, value in data.items():
            if hasattr(tmp_user, key):
                act.append("%s: %s" % (key, value))
        act = " and ".join(act)
        self.task.action = "update|user|%s|%s|%s" % (login, "", act)
        return self._user_action()

    def user_remove(self, user):
        if not self.project:
            raise ValueError("Can't delete a user from none existent project")
        login = user.login
        description = "Remove user %s from project %s" % (login, self.p_name)
        self.task.action = "remove|user|%s|%s|%s" % (login, self.p_name,
                                                     description)
        self.task.user = user
        return self._user_action()

    def _user_action(self):
        self.processed = True
        self._commit()
        return self

    def _commit(self):
        double = Tasks().query.filter_by(
            action=self.task.action
        ).filter_by(
            processed=False
        ).first()
        if double:
            raise ValueError("Same previous task found ID: %s" % double.id)
        db.session.add(self.task)
        db.session.commit()
