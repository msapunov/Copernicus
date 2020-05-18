from pathlib import Path
from flask import current_app as app
from logging import warning
from configparser import ConfigParser
from os.path import join as path_join, exists
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
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
        self.working_object = None
        self.cfg = None
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

    def configure(self):
        cfg_file = app.config.get("EMAIL_CONFIG", "mail.cfg")
        cfg_path = path_join(app.instance_path, cfg_file)
        if not exists(cfg_path):
            warning("E-mail configuration file doesn't exists. Using defaults")
            return
        self.cfg = ConfigParser()
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
        self.msg["Cc"] = COMMASPACE.join(self.cc)
        if self.message:
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
        return True

    def registration(self, registration_obj):
        self.working_object = registration_obj
        return self

    def send_visa(self, visa):
        self.attach_file(visa)
        to = self.working_object.responsible_email
        self.destination = self.cfg.get("PROJECT VISA", "TO",fallback=to)
        self.cc = [self.cfg.get("PROJECT VISA", "CC", fallback="")]
        self.sender = self.cfg.get("PROJECT VISA", "FROM", fallback="")
        ttl = "Visa for your project registration id: %s"\
              % self.working_object.project_id()
        self.title = self.cfg.get("PROJECT VISA", "TITLE", fallback=ttl)
        name = self.working_object.responsible_first_name
        surname = self.working_object.responsible_last_name
        message = """Dear %s %s
        You have to sign the visa in order to have your project activated
        """ % (name, surname)
        self.message = self.cfg.get("PROJECT VISA", "MESSAGE", fallback=message)
        if self.send():
            return "Sent email with visa to %s" % self.destination
        return "Failed to send email with visa to %s" % self.destination