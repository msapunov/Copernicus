from paramiko import SSHClient, AutoAddPolicy, AuthenticationException, RSAKey
from flask import current_app, request
from flask_login import current_user
from flask_mail import Message
from logging import debug, error
from re import compile
from unicodedata import normalize


def normalize_word(word):
    word = word.replace("'", "")
    word = normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")
    return word


def generate_login(name, surname):
    from base.database.schema import User
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
        raise ValueError("Message body is empty")
    from base import mail
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

    debug("Connecting to %s with login %s and key %s" % (host, login, key_file))
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        client.connect(host, username=login, pkey=key)
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


class Task:

    def __init__(self, id):
        from base.database.schema import Tasks
        task = Tasks().query.filter_by(id=id).first()
        if not task:
            raise ValueError("No task with id %s found" % id)
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

    def user(self, u_name):
        self.task.user = u_name
        return self

    def project(self, p_name):
        self.task.project = p_name
        return self

    def user_create(self, user):
        if not self.project:
            raise ValueError("Can't add a user to none existent project")
        self.task.limbo_user = user
        self.task.action = "create|%s||%s" % (self.task.limbo_user.login,
                                              self.task.project.get_name())
        self._user_action()

    def user_assign(self, user):
        if not self.project:
            raise ValueError("Can't assign a user to none existent project")
        self.task.limbo_user = self._copy_user(user)
        self.task.action = "assign|%s|%s" % (self.task.limbo_user.login,
                                             self.task.project.get_name())
        self._user_action()

    def responsible_assign(self, user):
        if not self.project:
            raise ValueError("Can't assign a new responsible to none existent"
                             " project")
        self.task.limbo_user = self._copy_user(user)
        self.task.action = "assign|%s|%s" % (self.task.limbo_user.login,
                                             self.task.project.get_name())
        self._user_action()

    def user_update(self, data):
        if not self.task.user:
            raise ValueError("Can't update information of unset user")
        self.task.limbo_user = self._copy_user(self.task.user)
        act = []
        for key, value in data.items():
            if hasattr(self.task.limbo_user, key):
                setattr(self.task.limbo_user, key, value)
                act.append("%s: %s" % (key, value))
        act = " and ".join(act)
        self.task.action = "update|%s|%s" % (self.task.user.login, act)
        self._user_action()

    def user_remove(self, user):
        if not self.project:
            raise ValueError("Can't delete a user from none existent project")
        self.task.limbo_user = self._copy_user(user)
        self.task.action = "remove|%s|%s" % (self.task.limbo_user.login,
                                             self.task.project.get_name())
        self._user_action()

    def _copy_user(self, user):
        from base import db
        from base.database.schema import LimboUser
        from base.database.schema import User

        data = {k: getattr(user, k) for k in db.inspect(User).columns.keys()}
        del data["id"], data["created"], data["modified"]

        limbo = LimboUser(**data)
        limbo.reference = user

        db.session.add(limbo)
        return limbo

    @staticmethod
    def _copy_project(project):
        from base import db
        from base.database.schema import LimboProject
        limbo = LimboProject(
            title=project.title,
            description=project.description,
            scientific_fields=project.scientific_fields,
            genci_committee=project.genci_committee,
            numerical_methods=project.numerical_methods,
            computing_resources=project.computing_resources,
            project_management=project.project_management,
            project_motivation=project.project_motivation,
            allocation_end=project.allocation_end,
            comment=project.comment,
            gid=project.gid,
            privileged=project.privileged,
            name=project.name,
            type=project.type,
            reference=project
        )
        db.session.add(limbo)
        return limbo

    def _user_action(self):
        self.processed = True
        self._commit()

    def _commit(self):
        from base import db
        db.session.add(self.task)
        db.session.commit()


class ProjectLog:

    def __init__(self, project):
        from base.database.schema import LogDB
        self.project = project
        self.log = LogDB(author=current_user, project=project)
        self.send = True

    def responsible_assign(self, user):
        self.log.event = "Made a request to assign new responsible %s"\
                         % user.full_name()
        self.log.user = user
        return self._commit()

    def user_assign(self, user):
        self.log.event = "Made a request to assign a new user %s"\
                         % user.full_name()
        self.log.user = user
        return self._commit()

    def user_del(self, user):
        self.log.event = "Made a request to delete user %s" % user.full_name()
        self.log.user = user
        return self._commit()

    def extend(self, extension):
        self.log.event = "Made a request to extend project for %s hour(s)"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def activate(self, extension):
        self.log.event = "Made an activation request"
        self.log.extension = extension
        return self._commit()

    def transform(self, extension):
        self.log.event = "Made a request to transform from type A to type B"
        self.log.extension = extension
        return self._commit()

    def accept(self, extension):
        self.log.event = "Extend request for %s hours is accepted"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def ignore(self, extension):
        self.log.event = "Extend request for %s hours is ignored"\
                         % extension.hours
        self.log.extension = extension
        self.send = False
        return self._commit()

    def reject(self, extension):
        self.log.event = "Extend request for %s hours is rejected"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def event(self, message):
        self.log.event = message.lower()
        return self._commit()

    def _commit(self):
        from base import db
        db.session.add(self.log)
        db.session.commit()
        message = "%s: %s" % (self.project.get_name(), self.log.event)
        if self.send:
            send_message(self.project.responsible.email, message=message)
        return message
