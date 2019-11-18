from paramiko import SSHClient, AutoAddPolicy, AuthenticationException, RSAKey
from flask import current_app, request, flash, redirect, url_for, g
from flask_login import current_user, logout_user
from flask_mail import Message
from logging import debug, error
from re import compile
from functools import wraps
from base import mail
from base.database.schema import LogDB, User
from base.utils import normalize_word


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


def generate_login(name, surname):
    users = User.query.all()
    logins = list(map(lambda x: x.login, users))

    name = name.split(" ")[0]
    name = name.split("-")[0]
    surname = surname.split(" ")[0]
    surname = surname.split("-")[0]
    name = normalize_word(name)
    surname = normalize_word(surname)

    i = 1
    guess = None
    while i < len(name):
        guess = name[0:i] + surname
        if guess not in logins:
            return guess
        i += 1
    raise ValueError("Seems that user with login '%s' has been already"
                     " registered in our database" % guess)


def send_message(to_who, by_who=None, cc=None, title=None, message=None):
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

    title = "[TEST MODE] "+title
    tech = current_app.config["EMAIL_TECH"]
    msg = Message(title, sender=by_who, recipients=to_who, cc=cc)
    postfix = "If this email has been sent to you by mistake, please report " \
              "to: %s" % tech
    msg.body = message + "\n" + postfix
    if current_app.config["MAIL_SEND"]:
        mail.send(msg)
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

    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.readlines()
    errors = stderr.readlines()
    client.close()

    return output, errors


def check_json():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    return data


def check_mail(raw_mail):
    email_regex = compile("[^@]+@[^@]+\.[^@]+")
    if not email_regex.match(raw_mail):
        raise ValueError("Provided e-mail '%s' seems invalid" % raw_mail)
    return str(raw_mail)


def check_int(raw_int):
    if not str(raw_int).isdigit():
        raise ValueError("Number expected: %s" % raw_int)
    return int(raw_int)


def check_str(raw_note):
    note = str(raw_note).strip()
    if len(note) < 1:
        raise ValueError("Non empty string expected: %s" % raw_note)
    return note


def check_word(raw_input):
    if not str(raw_input).isalpha():
        raise ValueError("String expected: %s" % raw_input)
    return str(raw_input)


def check_alnum(raw_note):
    if not str(raw_note).isalnum():
        raise ValueError("Alphanumeric characters expected: %s" % raw_note)
    return str(raw_note)


class MailingList:

    def __init__(self, list):
        self.list = list

    def subscribe(self, email):
        pass

    def unsubscribe(self, email):
        pass

    def change(self, old_mail, new_mail):
        pass


class UserMailingList(MailingList):

    def __init__(self):
        list = current_app.config.get("USER_LIST")
        super().__init__(list)


class ResponsibleMailingList(MailingList):

    def __init__(self):
        list = current_app.config.get("RESPONSIBLE_LIST")
        super().__init__(list)


class Task:

    def __init__(self, tid):
        from base.database.schema import Tasks
        task = Tasks().query.filter_by(id=tid).first()
        if not task:
            raise ValueError("No task with id %s found" % tid)
        self.task = task
        self.id = task.id

    def _update_user(self):
        from base import db
        from base.database.schema import User

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
        self.notify()
        return self._action()

    def ignore(self):
        self.task.decision = "ignore"
        return self._action()

    def reject(self):
        self.task.decision = "reject"
        self.notify()
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

    def notify(self):
        description = self.description()
        tid = self.id
        to = self.task.author.email
        action = self.task.decision
        title = "Task id '%s' has been %sed" % (tid, action)
        msg = "Task '%s' with id '%s' has been %s" % (description, tid, action)
        return send_message(to, title=title, message=msg)

    def _action(self):
        self.task.processed = True
        self.task.approve = current_user
        self._commit()
        return self.task

    @staticmethod
    def _commit():
        from base import db
        db.session.commit()


class TaskQueue:

    def __init__(self):
        from base.database.schema import Tasks
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
        from base import db
        db.session.add(self.task)
        db.session.commit()


class ProjectLog:

    def __init__(self, project):
        self.project = project
        self.log = LogDB(author=current_user, project=project)
        self.send = True

    def _send_email(self, message):
        email = current_app.config.get("EMAIL_PROJECT", None)
        if not email:
            raise ValueError("")
        sender = ("Automatic messaging system", email)
        cc = [email]
        if not self.project.responsible:
            raise ValueError("")
        if not self.project.responsible.email:
            raise ValueError("")
        to = [self.project.responsible.email]
        # full_name = self.project.responsible.full_name()
        tech = current_app.config.get("EMAIL_TECH", None)
        if tech:
            postfix = "If you believe that this email has been sent to you by" \
                      " mistake, please report to: %s" % tech
        else:
            postfix = "If you believe that this email has been sent to you by" \
                      " mistake, please delete it!"
        title = "[TEST MODE] Mesocentre reporting"
        email = Message(title, sender=sender, recipients=to, cc=cc)
        email.body = message + "\n" + postfix
        if not current_app.config.get("MAIL_SEND", None):
            return "E-mail submission has been blocked in configuration file"
        mail.send(email)
        return "E-mail has been sent successfully"

    def _commit(self):
        from base import db
        db.session.add(self.log)
        db.session.commit()
        message = "%s: %s" % (self.project.get_name(), self.log.event)
        if self.send:
            self._send_email(message)
        return message

    def _commit_user(self, user):
        self.log.user = user
        return self._commit()

    def responsible_added(self, user):
        self.log.event = "Added a new project responsible %s with login %s" % (
            user.full_name(), user.login)
        return self._commit_user(user)

    def responsible_assign(self, user):
        self.log.event = "Made a request to assign new responsible %s"\
                         % user.full_name()
        return self._commit_user(user)

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

    def extend(self, extension):
        self.log.event = "Made a request to extend project for %s hour(s)"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def extended(self, extension):
        self.log.event = "Extension request for %s hour(s) has been processed"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def activate(self, extension):
        self.log.event = "Activation request has been registered"
        self.log.extension = extension
        return self._commit()

    def transform(self, extension):
        self.log.event = "Request to transform the project from type A to " \
                         "type B has been registered"
        self.log.extension = extension
        return self._commit()

    def accept(self, extension):
        self.log.event = "Extension request for %s hours is accepted"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def ignore(self, extension):
        self.log.event = "Extension request for %s hours is ignored"\
                         % extension.hours
        self.log.extension = extension
        self.send = False
        return self._commit()

    def reject(self, extension):
        self.log.event = "Extension request for %s hours is rejected"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def event(self, message):
        self.log.event = message.lower()
        return self._commit()
