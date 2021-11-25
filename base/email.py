from pathlib import Path
from flask import current_app as app
from logging import warning, debug
from configparser import ConfigParser, ExtendedInterpolation
from os.path import join as path_join, exists
from threading import Thread
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import smtplib


class Mail(Thread):

    def __init__(self):
        self.sending = app.config.get("MAIL_SEND", False)
        self.destination = None
        self.sender = None
        self.cc = None
        self.title = "Copernicus reporting"
        self.message = None
        self.msg = MIMEMultipart()
        self.server = None
        self.port = None
        self.use_tls = None
        self.use_ssl = None
        self.username = None
        self.password = None
        self.cfg = None
        self.signature = None
        self.greetings = None
        self.configure()
        Thread.__init__(self)

    def attach_file(self, path=None):
        if not path:
            raise ValueError("Please, indicate a name of a file to attach")
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
        self.msg.attach(part)
        debug("File %s attached" % path)
        return self

    def attach(self, name=None):
        for path in name or []:
            self.attach_file(path)
        return self

    def populate(self, name):
        """
        Takes a section in configuration file and fill Mail object with data
        found in this section. Like destination, cc, sender, title, message body
        and signature.
        :param name: String. Name of a section
        :return: Object. Instance of Mail object
        """
        self.destination = self.cfg.get(name, "TO", fallback=None)
        self.cc = self.cfg.get(name, "CC", fallback=None)
        self.sender = self.cfg.get(name, "FROM", fallback=None)
        self.title = self.cfg.get(name, "TITLE", fallback=None)
        self.message = self.cfg.get(name, "MESSAGE", fallback=None)
        self.signature = self.cfg.get(name, "SIGNATURE", fallback=None)
        return self

    def configure(self):
        """
        Configure Mail object with the values found in SERVER section of
        configuration file
        :return: Object. Instance of Mail object
        """
        cfg_file = app.config.get("EMAIL_CONFIG", "mail.cfg")
        cfg_path = path_join(app.instance_path, cfg_file)
        if not exists(cfg_path):
            warning("E-mail configuration file doesn't exists. Using defaults")
            return
        self.cfg = ConfigParser(interpolation=ExtendedInterpolation(),
                                allow_no_value=True)
        self.cfg.read(cfg_path, encoding="utf-8")
        self.server = self.cfg.get("SERVER", "HOST", fallback="localhost")
        self.port = self.cfg.getint("SERVER", "PORT", fallback=25)
        self.use_tls = self.cfg.getboolean("SERVER", "USE_TLS", fallback=False)
        self.use_ssl = self.cfg.getboolean("SERVER", "USE_SSL", fallback=False)
        self.username = self.cfg.get("SERVER", "USERNAME", fallback=None)
        self.password = self.cfg.get("SERVER", "PASSWORD", fallback=None)
        return self

    def run(self):
        """
        Asynchronous sending of mail
        :return: Nothing
        """
        self.send()

    def send(self):
        """
        Synchronous sending of mail
        :return: Nothing
        """
        debug("Sending mail to %s" % self.destination)
        self.msg["Subject"] = self.title
        self.msg["From"] = self.sender
        if self.destination and isinstance(self.destination, str):
            self.msg["To"] = self.destination
        else:
            raise ValueError("Cannot send message to %s" % self.destination)
        self.msg["Date"] = formatdate(localtime=True)
        if self.cc:
            if isinstance(self.cc, list):
                self.msg["Cc"] = ",".join(self.cc)
            else:
                self.msg["Cc"] = self.cc
        self.msg["Message-ID"] = make_msgid()
        if self.message:
            if self.signature:
                self.message = self.message + self.signature
            self.msg.attach(MIMEText(self.message))
        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(self.server, self.port)
        else:
            smtp = smtplib.SMTP(self.server, self.port)
        if self.use_tls:
            smtp.starttls()
        if self.username and self.password:
            smtp.login(self.username, self.password)
        debug("Value of self.sending switch: %s" % self.sending)
        if self.sending:
            debug("Submitting mail to SMTP server")
            smtp.send_message(self.msg)
        debug("Quit SMTP server")
        smtp.quit()
        for header in self.msg.items():
            debug("%s: %s" % (header[0], header[1]))
        debug("Message sent to %s" % self.msg["To"])

    def registration(self, rec):
        self.populate("PROJECT VISA")
        cfg = self.cfg["PROJECT VISA"]
        self.destination = cfg.get("TO", fallback=rec.responsible_email)
        self.cc = cfg.get("CC", fallback=[])
        self.sender = cfg.get("FROM", fallback="")
        self.title = cfg.get("TITLE", fallback="Visa for: %s" % rec.project_id())
        message = """Dear %s,
        You have to sign the visa in order to have your project activated
        """ % rec.responsible_full_name()
        self.message = cfg.get("MESSAGE", fallback=message)
        self.signature = cfg.get("SIGNATURE", fallback="Truly Yours, Robot")
        self.__populate_values({"%FULLNAME": rec.responsible_full_name()})
        return self

    def visa_received(self, pending):
        self.populate("VISA RECEIVED")
        details = "\n".join(pending.cloud())
        name = pending.project_id()
        self.__populate_values({"%NAME": name, "DETAILS": details})
        return self

    def visa_attach(self, visa):
        if type(visa) is list:
            [self.attach_file(x) for x in visa]
        else:
            self.attach_file(visa)
        return self

    def __pending_init(self, record, section_name):
        self.populate(section_name)
        if not record.responsible_email:
            raise ValueError("Responsible has no email")
        self.destination = record.responsible_email
        pid = record.project_id()
        title = record.title
        first = record.responsible_first_name
        last = record.responsible_last_name
        full = "%s %s" % (first, last)
        self.__populate_values({"%FULLNAME": full, "%MESO": pid,
                                "%TITLE": title})
        return self

    def pending_reject(self, log, message):
        self.__pending_init(log, "REGISTRATION REJECTED")
        self.__populate_values({"%COMMENT": message})
        return self

    def pending_message(self, msg):
        self.populate("REGISTRATION MESSAGE")
        self.destination = msg["destination"]
        self.__populate_values({"%TITLE": msg["title"], "%MESSAGE": msg["body"]})
        return self.run()

    def visa_resent(self, log):
        return self.pending_log(log)

    def visa_sent(self, log):
        return self.pending_log(log)

    def visa_skip(self, log):
        return self.pending_log(log)

    def pending_approve(self, log):
        return self.pending_log(log)

    def pending_reset(self, log):
        return self.pending_log(log)

    def pending_ignore(self, log):
        return self.pending_log(log)

    def pending_log(self, log):
        self.populate("TECH")
        title = "[%s] %s" % (log.pending.project_id(), log.log.event)
        message = log.log.brief()["event"]
        self.__populate_values({"%TITLE": title, "%MESSAGE": message})
        return self

    def report_uploaded(self, record):
        self.__project_init(record, "REPORT UPLOADED")
        return self

    def user_update(self, record):
        self.populate("USER UPDATE")
        self.destination = record.user.email
        full = record.user.full_name()
        changes = record.log.event
        self.__populate_values({"%FULLNAME": full, "%CHANGES": changes})
        return self

    def user_updated(self, record):
        pass

    def responsible_assign(self, task):
        self.populate("RESPONSIBLE ASSIGN")
        self.destination = task.project.responsible.email
        name = task.project.get_name()
        full = task.project.responsible.full_name()
        new_full = task.user.full()
        self.cc = task.user.email + "," + self.cc
        self.__populate_values({"%FULLNAME": full, "%NEW_FULLNAME": new_full,
                                "%NAME": name})
        return self

    def responsible_assigned(self, task):
        self.populate("RESPONSIBLE ASSIGNED")
        self.destination = task.project.responsible.email
        name = task.project.get_name()
        full = task.project.responsible.full_name()
        self.cc = task.author.email + "," + self.cc
        self.__populate_values({"%FULLNAME": full, "%MAIL": self.destination,
                                "%OLD_NAME": task.author.full_name(),
                                "%NAME": name})
        return self

    def user_new(self, user):
        self.populate("USER NEW")
        self.destination = user.email
        self.__populate_values({"%FULLNAME": user.full(), "%LOGIN": user.login,
                                "%PASS": user.pasword})
        return self

    def user_create(self, user, done=False):
        task = user.task
        if done:
            self.populate("USER CREATED")
        else:
            self.populate("USER CREATE")
        self.destination = task.author.email
        self.cc = user.email + "," + self.cc
        self.__populate_values({"%FULLNAME": task.author.full_name(),
                                "%MAIL": user.email, "%NEWUSER": user.full(),
                                "%NAME": task.project.get_name()})
        return self

    def user_created(self, user):
        return self.user_create(user, done=True)

    def user_assign(self, task, done=False):
        if done:
            self.populate("USER ASSIGNED")
        else:
            self.populate("USER ASSIGN")
        self.destination = task.author.email
        if self.cc:
            self.cc = task.user.email + "," + self.cc
        else:
            self.cc = task.user.email
        self.__populate_values({"%FULLNAME": task.author.full_name(),
                                "%ASSIGN_USER": task.user.full(),
                                "%NAME": task.project.get_name()})
        return self

    def user_assigned(self, task):
        return self.user_assign(task, done=True)

    def user_delete(self, task, done=False):
        if done:
            self.populate("USER DELETED")
        else:
            self.populate("USER DELETE")
        self.destination = task.author.email
        self.__populate_values({"%FULLNAME": task.author.full_name(),
                                "%DELETE_USER": task.user.full(),
                                "%NAME": task.project.get_name()})
        return self

    def user_deleted(self, task):
        return self.user_delete(task, done=True)

    def __project_init(self, record, section_name):
        self.populate(section_name)

        if not record.project.responsible.email:
            raise ValueError("Responsible has no email")
        self.destination = record.project.responsible.email
        cpu = str(record.hours) if getattr(record, "hours", None) else ""
        name = record.project.get_name()
        full = record.project.responsible.full_name()
        self.__populate_values({"%FULLNAME": full, "%NAME": name, "%CPU": cpu})
        if getattr(record, "exception", None) and record.exception:
            self.title = "[EXCEPTIONAL]" + self.title
        return self

    def __populate_values(self, values):
        for attr in ["title", "greetings", "message", "signature"]:
            for key, value in values.items():
                val = getattr(self, attr, "")
                if val:
                    val = val.replace(key, value)
                setattr(self, attr, val)
        return self

    def project_renew(self, record):
        self.__project_init(record, "PROJECT RENEW")
        return self

    def project_renewed(self, record):
        self.__project_init(record, "PROJECT RENEWED")
        return self

    def project_extend(self, record):
        self.__project_init(record, "PROJECT EXTEND")
        return self

    def project_extended(self, record):
        self.__project_init(record, "PROJECT EXTENDED")
        return self

    def project_transform(self, record):
        self.__project_init(record, "PROJECT TRANSFORM")
        self.__populate_values({"%TYPE_BEFORE": record.project.type,
                                "%TYPE_AFTER": record.transform})
        return self

    def project_transformed(self, record):
        self.__project_init(record, "PROJECT TRANSFORMED")
        self.__populate_values({"%TYPE_BEFORE": record.project.type,
                                "%TYPE_AFTER": record.transform})
        return self

    def project_expired(self, record):
        self.__project_init(record, "PROJECT EXPIRED")
        self.__populate_values({"%TYPE_BEFORE": record.project.type,
                                "%TYPE_AFTER": record.transform})
        return self

    def project_expiring(self, record):
        self.__project_init(record, "PROJECT EXPIRING")
        self.__populate_values({"%TYPE_BEFORE": record.project.type,
                                "%TYPE_AFTER": record.transform})
        return self

    def project_activate(self, record):
        self.__project_init(record, "PROJECT ACTIVATE")
        return self

    def allocation_accepted(self, record, extend_or_renew):
        self.__project_init(record, "ALLOCATION ACCEPTED")
        reason = record.decision if record.decision else None
        self.__populate_values({"%EXT": extend_or_renew, "%REASON": reason})
        return self

    def allocation_ignored(self, record, e_type):
        self.__project_init(record, "ALLOCATION IGNORED")
        rid = str(record.id)
        created = str(record.created)
        self.__populate_values({"%EXT": e_type, "%CREATED": created, "ID": rid})
        return self

    def allocation_rejected(self, record, extend_or_renew):
        self.__project_init(record, "ALLOCATION REJECTED")
        reason = record.decision if record.decision else None
        self.__populate_values({"%EXT": extend_or_renew, "%REASON": reason})
        return self

    def task_accepted(self, task):
        self.populate("TECH")
        title = "Task id '%s' has been accepted" % task.id
        message = "Task '%s' has been accepted" % task.description()
        self.__populate_values({"%TITLE": title, "%MESSAGE": message})
        return self

    def task_rejected(self, task):
        self.populate("TECH")
        title = "Task id '%s' has been rejected" % task.id
        message = "Task '%s' has been rejected" % task.description()
        self.__populate_values({"%TITLE": title, "%MESSAGE": message})
        return self

    def log(self, log):
        self.populate("TECH")
        title = "Log entry ID: %s" % log.id
        self.__populate_values({"%TITLE": title, "%MESSAGE": log.event})
        return self


class Sympa(Mail):

    def __init__(self, list_name):
        super().__init__()
        self.configure()
        self.list = self.cfg.get("LIST", list_name)
        self.destination = self.cfg.get("LIST", "SYMPA")

    def subscribe(self, email, name=None):
        self.sender = email
        if name:
            self.title = "SUBSCRIBE %s %s" % (self.list, name)
        else:
            self.title = "SUBSCRIBE %s" % self.list
        return self.start()

    def unsubscribe(self, email):
        self.sender = email
        self.title = "UNSUBSCRIBE %s" % self.list
        return self.start()

    def change(self, old_mail, new_mail, name=None):
        if self.unsubscribe(old_mail):
            return self.subscribe(new_mail, name=name)


class UserMailingList(Sympa):

    def __init__(self):
        super().__init__("USER_LIST")


class ResponsibleMailingList(Sympa):

    def __init__(self):
        super().__init__("RESPONSIBLE_LIST")
