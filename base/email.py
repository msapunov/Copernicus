from pathlib import Path
from flask import current_app as app
from logging import warning, debug
from configparser import ConfigParser, ExtendedInterpolation
from os.path import join as path_join, exists
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import smtplib


class Mail:

    def __init__(self):
        self. destination = None
        self.sender = None
        self.cc = []
        self.title = "Mesocentre reporting"
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
        return self

    def attach(self, name=None):
        for path in name or []:
            self.attach_file(path)
        return self

    def populate(self, name):
        self.destination = self.cfg.get(name, "TO", fallback=None)
        self.cc = [self.cfg.get(name, "CC", fallback=None)]
        self.sender = self.cfg.get(name, "FROM", fallback=None)
        self.title = self.cfg.get(name, "TITLE", fallback=None)
        self.greetings = self.cfg.get(name, "GREETINGS", fallback=None)
        self.message = self.cfg.get(name, "MESSAGE", fallback=None)
        self.signature = self.cfg.get(name, "SIGNATURE", fallback=None)
        return self
#        if not self.message:
#            raise ValueError("Message text not found")

    def configure(self):
        cfg_file = app.config.get("EMAIL_CONFIG", "mail.cfg")
        cfg_path = path_join(app.instance_path, cfg_file)
        if not exists(cfg_path):
            warning("E-mail configuration file doesn't exists. Using defaults")
            return
        self.cfg = ConfigParser(interpolation=ExtendedInterpolation(),
                                allow_no_value=True)
        self.cfg.read(cfg_path, encoding="utf-8")
        self.server = self.cfg.get("SERVER", "HOST")
        self.port = self.cfg.getint("SERVER", "PORT", fallback=25)
        self.use_tls = self.cfg.getboolean("SERVER", "USE_TLS", fallback=False)
        self.use_ssl = self.cfg.getboolean("SERVER", "USE_SSL", fallback=False)
        self.username = self.cfg.get("SERVER", "USERNAME", fallback=None)
        self.password = self.cfg.get("SERVER", "PASSWORD", fallback=None)
        return self

    def send(self):
        self.msg["Subject"] = self.title
        self.msg["From"] = self.sender
        self.msg["To"] = self.destination
        self.msg["Date"] = formatdate(localtime=True)
        if self.cc:
            self.msg["Cc"] = ",".join(self.cc)
        self.msg["Message-ID"] = make_msgid()
        if self.message:
            if self.greetings:
                self.message = self.greetings + self.message
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
        if app.config.get("MAIL_SEND", False):
            smtp.send_message(self.msg)
        smtp.quit()
        for header in self.msg.items():
            debug("%s: %s" % (header[0], header[1]))
        return True

    def registration(self, rec):
        cfg = self.cfg["PROJECT VISA"]
        self.destination = cfg.get("TO", fallback=rec.responsible_email)
        self.cc = [cfg.get("CC", fallback="")]
        self.sender = cfg.get("FROM", fallback="")
        self.title = cfg.get("TITLE", fallback="Visa for: %s" % rec.project_id())
        self.greetings = cfg.get("GREETINGS", fallback="Hi,")
        message = """Dear %s,
        You have to sign the visa in order to have your project activated
        """ % rec.responsible_full_name()
        self.message = cfg.get("MESSAGE", fallback=message)
        self.signature = cfg.get("SIGNATURE", fallback="Truly Yours, Robot")
        self.__populate_values({"%FULLNAME": rec.responsible_full_name()})
        return self

    def attach_visa(self, visa):
        if type(visa) is list:
            [self.attach_file(x) for x in visa]
        else:
            self.attach_file(visa)
        return self

    def responsible_add(self):
        pass

    def responsible_assign(self):
        pass

    def user_add(self):
        pass

    def user_assign(self):
        pass

    def user_assigned(self):
        pass

    def user_delete(self, user):
        pass

    def user_deleted(self, user):
        pass

    def __project_init(self, record, section_name):
        self.populate(section_name)

        if not record.project.responsible.email:
            raise ValueError("Responsible has no email")
        if not self.destination:
            self.destination = record.project.responsible.email
        cpu = str(record.hours)
        name = record.project.get_name()
        full = record.project.responsible.full_name()
        self.__populate_values({"%FULLNAME": full, "%NAME": name, "%CPU": cpu})
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
        self.destination = task.author.email
        title = "Task id '%s' has been accepted" % task.id
        message = "Task '%s' has been accepted" % task.description()
        self.__populate_values({"%TITLE": title, "%MESSAGE": message})
        return self

    def task_rejected(self, task):
        self.populate("TECH")
        self.destination = task.author.email
        title = "Task id '%s' has been rejected" % task.id
        message = "Task '%s' has been rejected" % task.description()
        self.__populate_values({"%TITLE": title, "%MESSAGE": message})
        return self
