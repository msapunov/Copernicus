from paramiko import SSHClient, AutoAddPolicy, AuthenticationException, RSAKey
from flask import current_app
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
    from code.database.schema import User
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
    from code import mail
    title = "[TEST MODE] "+title
    tech = current_app.config["EMAIL_TECH"]
    msg = Message(title, sender=by_who, recipients=to_who, cc=cc)
    postfix = "If this email has been sent to you by mistake, please report " \
              "to: %s" % tech
    msg.body = message + "\n" + postfix
#    mail.send(msg)
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


def check_mail(raw_mail):
    email_regex = compile("[^@]+@[^@]+\.[^@]+")
    if not email_regex.match(raw_mail):
        raise ValueError("Provided e-mail '%s' seems invalid" % raw_mail)
    return str(raw_mail)


def check_int(raw_int):
    if not str(raw_int).isdigit():
        raise ValueError("Number expected: %s" % raw_int)
    return str(raw_int)


def check_str(raw_note):
    if not str(raw_note).isalpha():
        raise ValueError("String expected: %s" % raw_note)
    return str(raw_note)


def check_alnum(raw_note):
    if not str(raw_note).isalnum():
        raise ValueError("Alphanumeric characters expected: %s" % raw_note)
    return str(raw_note)


class TaskQueue:

    def __init__(self):
        from code.database.schema import Tasks
        self.task = Tasks(author=current_user, processed=False,
                          status="pending")

    def user(self, u_name):
        self.task.user = u_name
        return self

    def project(self, p_name):
        self.task.project = p_name
        return self

    def user_add(self, user):
        if not self.project:
            raise ValueError("Can't add a user to none existent project")
        self.task.limbo_user = user
        self.task.action = "create"
        self._user_action()

    def user_assign(self, user):
        if not self.project:
            raise ValueError("Can't assign a user to none existent project")
        self.task.limbo_user = self._copy_user(user)
        self.task.action = "assign"
        self._user_action()

    def responsible_assign(self, user):
        if not self.project:
            raise ValueError("Can't assign a new responsible to none existent"
                             " project")
        self.task.limbo_user = self._copy_user(user)
        self.task.action = "boost"
        self._user_action()

    def user_change(self, data):
        if not self.project:
            raise ValueError("Can't change user's info if project is not set")
        self.task.task = data
        self.task.action = "update"
        self._user_action()

    def user_delete(self, user):
        if not self.project:
            raise ValueError("Can't delete a user from none existent project")
        self.task.limbo_user = self._copy_user(user)
        self.task.action = "delete"
        self._user_action()

    @staticmethod
    def _copy_project(project):
        from code import db
        from code.database.schema import LimboProject
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

    @staticmethod
    def _copy_user(user):
        from code import db
        from code.database.schema import LimboUser
        limbo = LimboUser(
            name=user.name,
            surname=user.surname,
            email=user.email,
            phone=user.phone,
            lab=user.lab,
            position=user.position,
            login=user.login,
            active=user.active,
            comment=user.comment,
            reference=user
        )
        db.session.add(limbo)
        return limbo

    def _user_action(self):
        self.task.status = "pending"
        self._commit()

    def _commit(self):
        from code import db
        db.session.add(self.task)
        db.session.commit()


class ProjectLog:

    def __init__(self, project):
        from code.database.schema import LogDB
        self.project = project
        self.log = LogDB(author=current_user, project=project)

    def responsible_assign(self, user):
        self.log.event = "Request to assign new responsible %s"\
                         % user.full_name()
        self.log.user = user
        return self._commit()

    def user_assign(self, user):
        self.log.event = "Request to assign user %s" % user.full_name()
        self.log.user = user
        return self._commit()

    def user_del(self, user):
        self.log.event = "Request to delete user %s" % user.full_name()
        self.log.user = user
        self._commit()

    def extend(self, extension):
        self.log.event = "Request to extend by %s hours" % extension.hours
        self.log.extension = extension
        self._commit()

    def activate(self, extension):
        self.log.event = "activation request"
        self.log.extension = extension
        self._commit()

    def transform(self, extension):
        self.log.event = "Request to transform from type A to type B"
        self.log.extension = extension
        self._commit()

    def accept(self, extension):
        self.log.event = "accept extend request for %s hours" % extension.hours
        self.log.extension = extension
        self._commit()

    def ignore(self, extension):
        self.log.event = "ignore extend request for %s hours" % extension.hours
        self.log.extension = extension
        self._commit()

    def reject(self, extension):
        self.log.event = "reject extend request for %s hours" % extension.hours
        self.log.extension = extension
        self._commit()

    def event(self, message):
        self.log.event = message.lower()
        self._commit()

    def _commit(self):
        from code import db
        db.session.add(self.log)
        db.session.commit()
        message = "%s: %s" % (self.project.get_name(), self.log.event)
        send_message(self.project.responsible.email, message=message)
        return message
