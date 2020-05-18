from pathlib import Path
from flask import current_app as app
from logging import warning
from configparser import ConfigParser
from os.path import join as path_join, exists
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate


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
        self.server = current_app.config.get("MAIL_SERVER", "localhost")
        self.port = current_app.config.get("MAIL_PORT", 25)
        self.use_tls = current_app.config.get("MAIL_USE_TLS", False)
        self.use_ssl = current_app.config.get("MAIL_USE_SSL", False)
        self.username = current_app.config.get("MAIL_USERNAME", None)
        self.password = current_app.config.get("MAIL_PASSWORD", None)
        return self

    def send(self):
        self.msg["Subject"] = self.title
        self.msg["From"] = self.sender
        self.msg["To"] = COMMASPACE.join(self.destination)
        self.msg["Date"] = formatdate(localtime=True)
        self.msg["Cc"] = COMMASPACE.join(self.cc)
        if self.message:
            self.msg.attach(MIMEText(self.message))
        self.configure()
        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(self.server, self.port)
        else:
            smtp = smtplib.SMTP(self.server, self.port)
        if self.use_tls:
            smtp.starttls()
        if self.username and self.password:
            smtp.login(self.username, self.password)
        if current_app.config.get("MAIL_SEND", False):
            smtp.send_message(self.msg)
        smtp.quit()
        return True

    def registration(self, registration_obj):
        self.working_object = registration_obj
        return self

    def send_visa(self, visa):
        self.attach_file(visa)
        self.destination = self.working_object.responsible_email
        self.title = "Visa for your project registration id: %s" % \
                     self.working_object.project_id()
        self.cc = [current_app.config.get("EMAIL_PROJECT", ""),
                   current_app.config.get("EMAIL_TECH", "")]
        self.sender = current_app.config.get("EMAIL_PROJECT", "")
        name = self.working_object.responsible_first_name
        surname = self.working_object.responsible_last_name
        self.message = """Dear %s %s
        Have to sign the visa
        """ % (name, surname)
        if self.send():
            return "Sent email with visa to %s" % self.destination
        return "Failed to send email with visa to %s" % self.destination