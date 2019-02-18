from flask_login import current_user
from paramiko import SSHClient, AutoAddPolicy, AuthenticationException, RSAKey
from flask import current_app
from logging import debug, error
from flask_mail import Message


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


def check_int(raw_int):
    number = int(raw_int)
    if (not number) or (number < 1):
        raise ValueError("Integer must be a positive number: %s" % number)
    return number


def check_str(raw_note):
    note = str(raw_note)
    if (not note) or (len(note) < 1):
        raise ValueError("Provided string can't be empty")
    return note


class TaskQueue:

    def __init__(self):
        from code.database.schema import Tasks
        self.task = Tasks(author=current_user, processed=False,
                          status="pending")

    def user_add(self, data):
        self.task.task = data
        self.task.entity = "user"
        self.task.action = "create"
        self._commit()

    def user_change(self, data):
        self.task.task = data
        self.task.entity = "user"
        self.task.action = "update"
        self._commit()

    def user_delete(self, data):
        self.task.task = data
        self.task.entity = "user"
        self.task.action = "delete"
        self._commit()

    def _commit(self):
        from code import db
        db.session.add(self.task)
        db.session.commit()


class ProjectLog:

    def __init__(self, project):
        from code.database.schema import LogDB
        self.log = LogDB(author=current_user, project=project)

    def extend(self, extension):
        self.log.event = "extension request"
        self.log.extension = extension
        self._commit()

    def activate(self, extension):
        self.log.event = "activation request"
        self.log.extension = extension
        self._commit()

    def transform(self, extension):
        self.log.event = "transformation request"
        self.log.extension = extension
        self._commit()

    def accept(self, extension):
        self.log.event = "accept request"
        self.log.extension = extension
        self._commit()

    def ignore(self, extension):
        self.log.event = "ignore request"
        self.log.extension = extension
        self._commit()

    def reject(self, extension):
        self.log.event = "reject request"
        self.log.extension = extension
        self._commit()

    def _commit(self):
        from code import db
        db.session.add(self.log)
        db.session.commit()
