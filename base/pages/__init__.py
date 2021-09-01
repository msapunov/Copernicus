from paramiko import SSHClient, AutoAddPolicy, AuthenticationException, RSAKey
from flask import current_app, request, flash, redirect, url_for, g
from flask_login import current_user, logout_user
from pathlib import Path
from logging import debug, error
from re import compile
from functools import wraps
from base import db
from base.email import Mail
from base.database.schema import LogDB, User, Tasks
from base.utils import normalize_word
from string import ascii_letters
from dateutil.relativedelta import relativedelta as rd
from datetime import datetime as dt
from calendar import monthrange

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
            flash("permissions denied to access URL: %s" % url)
            logout_user()
            return redirect(url_for("login.login"))
        return decorated_function
    return log_required


def calculate_ttl(project):
    now = dt.now()
    if project.type == "a":
        month = int(current_app.config.get("ACC_TYPE_A", 6))
        return now + rd(month=+month)
    if project.type == "h":
        month = int(current_app.config.get("ACC_TYPE_H", 6))
        return now + rd(month=+month)
    # For project type B
    year = now.year + 1
    month = int(current_app.config.get("ACC_START_MONTH", 3))
    if "ACC_START_DAY" in current_app.config:
        day = int(current_app.config.get("ACC_START_DAY", 1))
    else:
        day = monthrange(year, month)[1]
    return dt(year, month, day, 0, 0, 0)


def calculate_usage(use, total):
    use = "{0:.1%}".format(float(use) / float(total))
    return float(use.replace("%", ""))


def generate_login(name, surname):
    users = User.query.all()
    logins = list(map(lambda x: x.login, users))

    name = normalize_word(name)
    name = "".join(filter(lambda x: x in ascii_letters, name))
    surname = normalize_word(surname)
    surname = "".join(filter(lambda x: x in ascii_letters, surname))

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
                 attach=None):
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


def ssh_wrapper(cmd, host=None):
    debug("ssh_wrapper(%s)" % cmd)
    if not host:
        host = current_app.config["SSH_SERVER"]
    login = current_app.config["SSH_USERNAME"]
    key_file = current_app.config["SSH_KEY"]
    key = RSAKey.from_private_key_file(key_file)
    timeout = current_app.config.get("SSH_TIMEOUT", 60)

    debug("Connecting to %s with login %s and key %s" % (host, login, key_file))
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        client.connect(host, username=login, pkey=key, timeout=timeout)
    except AuthenticationException:
        error("Failed to connect to %s under using %s with key '%s'"
              % (host, login, key_file))
        client.close()
        return [], []
    except Exception as e:
        error("Failed to establish a connection to %s due following error: %s"
              % (host, e))
        client.close()
        return [], []
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.readlines()
    errors = stderr.readlines()
    client.close()
    debug("Out: %s" % output)
    debug("Err: %s" % errors)
    return output, errors


def check_json():
    if not request.is_json:
        raise ValueError("Expecting application/json requests")
    data = request.get_json()
    if not data:
        raise ValueError("Empty JSON request received")
    debug("Incoming JSON: %s" % data)
    return data


def check_int(raw_int):
    if not str(raw_int).isdigit():
        raise ValueError("Number expected: %s" % raw_int)
    return int(raw_int)


def check_str(raw_note):
    note = str(raw_note).strip()
    if len(note) < 1:
        raise ValueError("Non empty string expected: %s" % raw_note)
    return note


class MailingList:

    def __init__(self, list_name):
        email_list = current_app.config.get(list_name, None)
        if email_list:
            self.list = email_list
            debug("Found emailing list '%s' for %s" % (email_list, list_name))
        else:
            self.list = None
            debug("No emailing list found in configuration for %s" % list_name)

    def subscribe(self, email, name=None):
        if name:
            title = "SUBSCRIBE %s %s" % (self.list, name)
        else:
            title = "SUBSCRIBE %s" % self.list
        if self.list:
            return self._send(email, title)

    def unsubscribe(self, email):
        if self.list:
            return self._send(email, "UNSUBSCRIBE %s" % self.list)

    def change(self, old_mail, new_mail, name=None):
        if self.list:
            if self.unsubscribe(old_mail):
                return self.subscribe(new_mail, name=name)

    def _send(self, address, title):
        return send_message(self.list, by_who=address, title=title)


class UserMailingList(MailingList):

    def __init__(self):
        super().__init__("USER_LIST")


class ResponsibleMailingList(MailingList):

    def __init__(self):
        super().__init__("RESPONSIBLE_LIST")


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

    def password_reset(self):
        if not self.u_name:
            raise ValueError("User is  not set. Can't change the password")
        self.task.action = "change|user|%s||password" % self.u_name
        return self._user_action()

    def user_create(self, user):
        if not self.p_name:
            raise ValueError("Can't add a user to none existent project")
        description = user.task_ready()
        self.task.action = "create|user|%s|%s|%s" % (user.login, self.p_name,
                                                     description)
        return self._user_action()

    def responsible_create(self, user):
        if not self.p_name:
            raise ValueError("Can't add a user to none existent project")
        description = user.task_ready()
        self.task.action = "create|resp|%s|%s|%s" % (user.login, self.p_name,
                                                     description)
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
        print(data)
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


class ProjectLog:

    def __init__(self, project):
        self.project = project
        self.log = LogDB(author=current_user, project=project)
        self.send = True

    def __commit(self, mail=None):
        db.session.add(self.log)
        db.session.commit()
        message = "%s: %s" % (self.project.get_name(), self.log.event)
        try:
            if mail and self.send: mail.send()
        finally:
            return message

    def _commit_user(self, user):
        self.log.user = user
        return self.__commit()

    def created(self, date):
        self.log.event = "Project created"
        if date:
            self.log.created = date
        return self.__commit()

    def responsible_added(self, user):
        self.log.event = "Added a new project responsible %s with login %s" % (
            user.full_name(), user.login)
        return self._commit_user(user)

    def responsible_assign(self, user):
        self.log.event = "Made a request to assign new responsible %s"\
                         % user.full_name()
        return self._commit_user(user)

    def user_add(self, user):
        self.log.event = "Request to add a new user: %s %s <%s>" % (
            user.name, user.surname, user.email)
        return self.__commit()

    def user_added(self, user):
        self.log.event = "Added a new user %s with login %s" % (
            user.full_name(), user.login)
        return self._commit_user(user)

    def user_assign(self, user):
        self.log.event = "Made a request to assign a new user %s"\
                         % user.full_name()
        return self._commit_user(user)

    def user_assigned(self, user):
        self.log.event = "User %s has been attached" % user.full_name()
        return self._commit_user(user)

    def user_deleted(self, user):
        self.log.event = "User %s (%s) has been deleted" % (
            user.full_name(), user.login)
        return self._commit_user(user)

    def user_del(self, user):
        self.log.event = "Made a request to delete user %s" % user.full_name()
        return self._commit_user(user)

    def renew(self, extension):
        article = "an exceptional" if extension.exception else "a"
        self.log.event = "Made %s request to renew project for %s hour(s)"\
                         % (article, extension.hours)
        self.log.extension = extension
        return self.__commit(Mail().project_renew(extension))

    def renewed(self, extension):
        self.log.event = "Renewal request for %s hour(s) has been processed"\
                         % extension.hours
        self.log.extension = extension
        return self.__commit(Mail().project_renewed(extension))

    def extend(self, extension):
        article = "an exceptional" if extension.exception else "a"
        self.log.event = "Made %s request to extend project for %s hour(s)"\
                         % (article, extension.hours)
        self.log.extension = extension
        return self.__commit(Mail().project_extend(extension))

    def extended(self, extension):
        self.log.event = "Extension request for %s hour(s) has been processed"\
                         % extension.hours
        self.log.extension = extension
        return self.__commit(Mail().project_extended(extension))

    def transform(self, extension):
        self.log.event = "Transformation request has been registered"
        self.log.extension = extension
        return self.__commit(Mail().project_transform(extension))

    def transformed(self, extension):
        self.log.event = "Transformation to type %s finished successfully"\
                            % extension.transform
        self.log.extension = extension
        return self.__commit(Mail().project_transformed(extension))

    def activate(self, extension):
        self.log.event = "Activation request has been registered"
        self.log.extension = extension
        return self.__commit(Mail().project_activate(extension))

    def accept(self, extension):
        ext_or_new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is accepted"\
                         % (ext_or_new, extension.hours)
        self.log.extension = extension
        return self.__commit(Mail().allocation_accepted(extension, ext_or_new))

    def ignore(self, extension):
        new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is ignored"\
                         % (new, extension.hours)
        self.log.extension = extension
        self.send = False
        return self.__commit(Mail().allocation_ignored(extension, new))

    def reject(self, extension):
        ext_or_new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is rejected"\
                         % (ext_or_new, extension.hours)
        self.log.extension = extension
        return self.__commit(Mail().allocation_rejected(extension, ext_or_new))

    def activity_report(self, file_rec):
        file_name = file_rec.path
        self.log.event = "Activity report saved on the server in the file %s" \
                         % file_name
        mail = Mail().report_uploaded(file_rec).attach_file(file_name)
        return self.__commit(mail)

    def event(self, message):
        self.log.event = message.lower()
        return self.__commit()
