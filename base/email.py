"""Email and mailing list management for the Copernicus application.

Provides the :class:`Mail` class for sending emails and the :class:`Sympa`
subclasses (:class:`UserMailingList`, :class:`ResponsibleMailingList`) for
managing mailing list subscriptions.
"""

import smtplib
from configparser import ConfigParser, ExtendedInterpolation
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from logging import debug, warning
from os.path import exists
from os.path import join as path_join
from pathlib import Path
from threading import Thread

from flask import current_app as app


class Mail(Thread):
    """Asynchronous email sender with configuration-driven templates.

    Reads email configuration from a config file (default ``mail.cfg``
    in the instance directory). Supports TLS, SSL, attachments, and
    template value substitution.
    """

    def __init__(self):
        """Initialize the Mail object with default values and configuration."""
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
        """Attach a file to the email.

        Args:
            path: Path to the file to attach.

        Returns:
            The Mail instance for method chaining.

        Raises:
            ValueError: If the path is not provided, does not exist, or
                is not a file.
        """
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
        part["Content-Disposition"] = "attachment; filename=%s" % str(attach_file.name)
        self.msg.attach(part)
        debug("File %s attached" % path)
        return self

    def attach(self, name=None):
        """Attach multiple files to the email.

        Args:
            name: List of file paths to attach.

        Returns:
            The Mail instance for method chaining.
        """
        for path in name or []:
            self.attach_file(path)
        return self

    def populate(self, name):
        """Fill email fields from a named section in the configuration file.

        Sets destination, CC, sender, title, message body, and signature
        from the configuration section.

        Args:
            name: Section name in the configuration file.

        Returns:
            The Mail instance for method chaining.
        """
        self.destination = self.cfg.get(name, "TO", fallback="")
        self.cc = self.cfg.get(name, "CC", fallback="")
        self.sender = self.cfg.get(name, "FROM", fallback="")
        self.title = self.cfg.get(name, "TITLE", fallback="")
        self.message = self.cfg.get(name, "MESSAGE", fallback="")
        self.signature = self.cfg.get(name, "SIGNATURE", fallback="")
        return self

    def configure(self):
        """Read server settings from the configuration file.

        Reads the ``SERVER`` section for SMTP host, port, TLS/SSL, and
        credentials.

        Returns:
            The Mail instance for method chaining.
        """
        cfg_file = app.config.get("EMAIL_CONFIG", "mail.cfg")
        cfg_path = path_join(app.instance_path, cfg_file)
        self.cfg = ConfigParser(interpolation=ExtendedInterpolation(),
                                allow_no_value=True)
        if exists(cfg_path):
            self.cfg.read(cfg_path, encoding="utf-8")
        else:
            warning("E-mail configuration file doesn't exists. Using defaults")
        self.server = self.cfg.get("SERVER", "HOST", fallback="localhost")
        self.port = self.cfg.getint("SERVER", "PORT", fallback=25)
        self.use_tls = self.cfg.getboolean("SERVER", "USE_TLS", fallback=False)
        self.use_ssl = self.cfg.getboolean("SERVER", "USE_SSL", fallback=False)
        self.username = self.cfg.get("SERVER", "USERNAME", fallback=None)
        self.password = self.cfg.get("SERVER", "PASSWORD", fallback=None)
        return self

    def run(self):
        """Send the email asynchronously (called by :class:`Thread`)."""
        self.send()

    def send(self):
        """Send the email synchronously via SMTP.

        Builds the MIME message, connects to the SMTP server, and sends it.
        If ``MAIL_SEND`` is disabled, the message is logged but not sent.

        Raises:
            ValueError: If no destination address is set.
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
        debug("Value of self.sending switch: %s" % self.sending)
        if not self.sending:
            debug("No e-mail has been sent")
            return
        debug("Complete message: %s" % self.msg)
        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(self.server, self.port)
        else:
            smtp = smtplib.SMTP(self.server, self.port)
        if self.use_tls:
            smtp.starttls()
        if self.username and self.password:
            debug("Login to SMTP server")
            smtp.login(self.username, self.password)
        smtp.send_message(self.msg)
        debug("Quit SMTP server")
        smtp.quit()
        for header in self.msg.items():
            debug("%s: %s" % (header[0], header[1]))
        debug("Message sent!")

    def simple_message(self, msg):
        """Send a simple message with destination, title, and body.

        Args:
            msg: Dictionary with ``destination``, ``title``, and ``body`` keys.
        """
        self.populate("SIMPLE MESSAGE")
        self.destination = msg["destination"]
        self.title = msg["title"]
        self.message = msg["body"]
        return self.run()

    def registration(self, rec):
        """Prepare a visa notification email for a registration request.

        Args:
            rec: Register record instance.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("PROJECT VISA")
        cfg = self.cfg["PROJECT VISA"]
        self.destination = cfg.get("TO", fallback=rec.responsible_email)
        self.cc = cfg.get("CC", fallback=[])
        self.sender = cfg.get("FROM", fallback="")
        self.title = cfg.get("TITLE", fallback="Visa for: %s" % rec.project_id())
        message = """Dear %s,
        You have to sign the visa in order to have your project created
        """ % rec.responsible_full_name()
        self.message = cfg.get("MESSAGE", fallback=message)
        self.signature = cfg.get("SIGNATURE", fallback="Truly Yours, Robot")
        self.__populate_values({"%FULLNAME": rec.responsible_full_name()})
        return self

    def visa_received(self, pending):
        """Prepare a notification when a signed visa has been received.

        Args:
            pending: Register record instance.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("VISA RECEIVED")
        details = "\n".join(pending.cloud())
        name = pending.project_id()
        self.__populate_values({"%NAME": name, "%DETAILS": details})
        return self

    def visa_attach(self, visa):
        """Attach visa PDF files to the email.

        Args:
            visa: A single path or list of paths to PDF files.

        Returns:
            The Mail instance for method chaining.
        """
        if type(visa) is list:
            [self.attach_file(x) for x in visa]
        else:
            self.attach_file(visa)
        return self

    def __pending_init(self, record, section_name):
        """Initialize email fields for a pending registration event.

        Args:
            record: RequestLog or Pending object.
            section_name: Configuration section name.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate(section_name)
        if not hasattr(record, "pending"):
            raise ValueError("Pending object is not attached to log")
        if not hasattr(record.pending, "responsible_email"):
            raise ValueError("Responsible has no email")
        self.destination = record.pending.responsible_email
        pid = record.pending.project_id()
        title = record.pending.title
        first = record.pending.responsible_first_name
        last = record.pending.responsible_last_name
        full = "%s %s" % (first, last)
        self.__populate_values({"%FULLNAME": full, "%MESO": pid,
                                "%TITLE": title})
        return self

    def pending_reject(self, log, message):
        """Prepare a rejection notification for a pending registration.

        Args:
            log: RequestLog instance.
            message: Rejection reason.

        Returns:
            The Mail instance for method chaining.
        """
        self.__pending_init(log, "REGISTRATION REJECTED")
        self.__populate_values({"%COMMENT": message})
        return self

    def visa_resent(self, log):
        """Prepare a notification for a resent visa.

        Args:
            log: RequestLog instance.

        Returns:
            The Mail instance for method chaining.
        """
        return self.pending_log(log)

    def visa_sent(self, log):
        """Prepare a notification that a visa was sent.

        Args:
            log: RequestLog instance.

        Returns:
            The Mail instance for method chaining.
        """
        return self.pending_log(log)

    def visa_skip(self, log):
        """Prepare a notification that visa sending was skipped.

        Args:
            log: RequestLog instance.

        Returns:
            The Mail instance for method chaining.
        """
        return self.pending_log(log)

    def pending_approve(self, log):
        """Prepare a notification that a pending request was approved.

        Args:
            log: RequestLog instance.

        Returns:
            The Mail instance for method chaining.
        """
        return self.pending_log(log)

    def pending_reset(self, log):
        """Prepare a notification that a pending request was reset.

        Args:
            log: RequestLog instance.

        Returns:
            The Mail instance for method chaining.
        """
        return self.pending_log(log)

    def pending_ignore(self, log):
        """Prepare a notification that a pending request was ignored.

        Args:
            log: RequestLog instance.

        Returns:
            The Mail instance for method chaining.
        """
        return self.pending_log(log)

    def pending_log(self, log):
        """Prepare a generic tech-team notification about a pending event.

        Args:
            log: RequestLog instance.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("TECH")
        title = "[%s] %s" % (log.pending.project_id(), log.log.event)
        message = log.log.brief()["event"]
        self.__populate_values({"%TITLE": title, "%MESSAGE": message})
        return self

    def report_uploaded(self, record):
        """Prepare a notification when an activity report is uploaded.

        Args:
            record: File or project record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "REPORT UPLOADED")
        return self

    def user_password(self, record, passwd):
        """Prepare a password-reset email for a user.

        Args:
            record: UserLog instance.
            passwd: Plain-text temporary password.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("PASSWORD RESET")
        self.destination = record.user.email
        full = record.user.full_name()
        self.__populate_values({"%FULLNAME": full, "%PASS": passwd})
        return self

    def user_publickey(self, record, key):
        """Prepare a notification that a public SSH key was installed.

        Args:
            record: UserLog instance.
            key: The SSH public key string.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("PUBLIC KEY")
        self.destination = record.user.email
        full = record.user.full_name()
        key = key[:62] + "..." + key[-62:]
        self.__populate_values({"%FULLNAME": full, "%KEY": key})
        return self

    def user_update(self, record):
        """Prepare a notification about a user info change request.

        Args:
            record: UserLog instance.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("USER UPDATE")
        self.destination = record.user.email
        full = record.user.full_name()
        changes = record.log.event
        self.__populate_values({"%FULLNAME": full, "%CHANGES": changes})
        return self

    def user_updated(self, record):
        """Handle a completed user update (currently a no-op).

        Args:
            record: UserLog instance.
        """

    def responsible_assign(self, task):
        """Prepare a notification about a responsible assignment request.

        Args:
            task: Tasks record.

        Returns:
            The Mail instance for method chaining.
        """
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
        """Prepare a notification that a responsible was assigned.

        Args:
            task: Tasks record.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("RESPONSIBLE ASSIGNED")
        self.destination = task.project.responsible.email
        name = task.project.get_name()
        full = task.project.responsible.full_name()
        self.cc = task.author.email + "," + self.cc
        self.__populate_values({"%FULLNAME": full, "%MAIL": self.destination,
                                "%OLD_NAME": task.author.full_name(),
                                "%NAME": name})
        return self

    def responsible_attached(self, task):
        """Prepare a notification that a responsible was attached.

        Args:
            task: Tasks record.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("RESPONSIBLE ATTACHED")
        self.destination = task.user.email
        self.__populate_values({"%FULLNAME": task.user.full_name(),
                                "%NAME": task.project.get_name()})
        return self

    def user_new(self, user):
        """Prepare a welcome email for a new user.

        Args:
            user: User instance with ``login``, ``passwd``, ``email``, etc.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("USER NEW")
        self.destination = user.email
        self.__populate_values({"%LOGIN": user.login, "%PASS": user.passwd,
                                "%FULLNAME": user.full_name()})
        return self

    def user_create(self, user, done=False):
        """Prepare a notification about a user creation request.

        Args:
            user: TmpUser instance with a ``task`` attribute.
            done: Whether the creation has been completed.

        Returns:
            The Mail instance for method chaining.
        """
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
        """Prepare a notification that a user was created.

        Args:
            user: TmpUser instance.

        Returns:
            The Mail instance for method chaining.
        """
        return self.user_create(user, done=True)

    def user_activate(self, task, done=False):
        """Prepare a notification about a user activation request.

        Args:
            task: Tasks record.
            done: Whether the activation has been completed.

        Returns:
            The Mail instance for method chaining.
        """
        if done:
            self.populate("USER ACTIVATED")
        else:
            self.populate("USER ACTIVATE")
        self.destination = task.author.email
        if self.cc:
            self.cc = task.user.email + "," + self.cc
        else:
            self.cc = task.user.email
        self.__populate_values({"%FULLNAME": task.author.full_name(),
                                "%ACTIVATE_USER": task.user.full(),
                                "%NAME": task.project.get_name()})
        return self

    def user_activated(self, task):
        """Prepare a notification that a user was activated.

        Args:
            task: Tasks record.

        Returns:
            The Mail instance for method chaining.
        """
        return self.user_activate(task, done=True)

    def user_assign(self, task, done=False):
        """Prepare a notification about a user assignment request.

        Args:
            task: Tasks record.
            done: Whether the assignment has been completed.

        Returns:
            The Mail instance for method chaining.
        """
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
        """Prepare a notification that a user was assigned.

        Args:
            task: Tasks record.

        Returns:
            The Mail instance for method chaining.
        """
        return self.user_assign(task, done=True)

    def user_attached(self, task):
        """Prepare a notification that a user was attached to a project.

        Args:
            task: Tasks record.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("USER ATTACHED")
        self.destination = task.user.email
        self.__populate_values({"%FULLNAME": task.user.full_name(),
                                "%NAME": task.project.get_name()})
        return self

    def user_delete(self, task, done=False):
        """Prepare a notification about a user deletion request.

        Args:
            task: Tasks record.
            done: Whether the deletion has been completed.

        Returns:
            The Mail instance for method chaining.
        """
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
        """Prepare a notification that a user was deleted.

        Args:
            task: Tasks record.

        Returns:
            The Mail instance for method chaining.
        """
        return self.user_delete(task, done=True)

    def __project_init(self, record, section_name):
        """Initialize email fields for a project-related event.

        Args:
            record: Project-level record (Extend or similar).
            section_name: Configuration section name.

        Returns:
            The Mail instance for method chaining.

        Raises:
            ValueError: If the responsible has no email.
        """
        self.populate(section_name)

        if not record.project.responsible.email:
            raise ValueError("Responsible has no email")
        self.destination = record.project.responsible.email
        val = getattr(record, "hours", None)
        cpu = str(val) if val is not None else ""
        name = record.project.get_name()
        full = record.project.responsible.full_name()
        self.__populate_values({"%FULLNAME": full, "%NAME": name, "%CPU": cpu})
        if getattr(record, "exception", None) and record.exception:
            self.title = "[EXCEPTIONAL]" + self.title
        return self

    def __populate_values(self, values):
        """Replace placeholder tokens in email fields with actual values.

        Iterates over ``title``, ``greetings``, ``message``, and
        ``signature`` attributes and replaces all occurrences of the
        placeholders (e.g. ``%FULLNAME``) with the corresponding values.

        Args:
            values: Dictionary mapping placeholder names (e.g. ``%FULLNAME``)
                to replacement strings.

        Returns:
            The Mail instance for method chaining.
        """
        for attr in ["title", "greetings", "message", "signature"]:
            for key, value in values.items():
                val = getattr(self, attr, "")
                if val:
                    val = val.replace(key, value)
                setattr(self, attr, val)
        return self

    def project_new(self, project):
        """Prepare a notification about a new project creation.

        Args:
            project: Project instance.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("PROJECT NEW")
        self.destination = project.responsible.email
        emails = list(map(lambda x: x.email, project.users))
        self.cc = emails + [self.cc]
        name = project.get_name()
        full = project.responsible.full_name()
        title = project.title
        cpu = str(project.resources.cpu)
        logins = ", ".join(list(map(lambda x: x.login, project.users)))
        self.__populate_values({"%FULLNAME": full, "%NAME": name, "%CPU": cpu,
                                "%TITLE": title, "%LOGIN": logins})
        return self

    def project_renew(self, record):
        """Prepare a notification about a project renewal request.

        Args:
            record: Extend record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "PROJECT RENEW")
        return self

    def project_renewed(self, record):
        """Prepare a notification that a project was renewed.

        Args:
            record: Extend record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "PROJECT RENEWED")
        return self

    def project_extend(self, record):
        """Prepare a notification about a project extension request.

        Args:
            record: Extend record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "PROJECT EXTEND")
        return self

    def project_extended(self, record):
        """Prepare a notification that a project was extended.

        Args:
            record: Extend record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "PROJECT EXTENDED")
        return self

    def project_transform(self, record):
        """Prepare a notification about a project transformation request.

        Args:
            record: Extend record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "PROJECT TRANSFORM")
        self.__populate_values({"%TYPE_BEFORE": record.project.type,
                                "%TYPE_AFTER": record.transform})
        return self

    def project_transformed(self, record):
        """Prepare a notification that a project was transformed.

        Args:
            record: Extend record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "PROJECT TRANSFORMED")
        self.__populate_values({"%TYPE_BEFORE": record.project.type,
                                "%TYPE_AFTER": record.transform})
        return self

    def project_expired(self, project):
        """Prepare a notification that a project has expired.

        .. note::
            Currently returns immediately without populating email fields.

        Args:
            project: Project instance.

        Returns:
            The Mail instance.
        """
        return self

    def project_expiring(self, record):
        """Prepare a notification that a project is about to expire.

        .. note::
            Currently returns immediately without populating email fields.

        Args:
            record: Project-level record.

        Returns:
            The Mail instance.
        """
        return self

    def project_activate(self, record):
        """Prepare a notification about a project activation request.

        Args:
            record: Extend record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "PROJECT ACTIVATE")
        return self

    def project_activated(self, record):
        """Prepare a notification that a project was activated.

        Args:
            record: Extend record.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "PROJECT ACTIVATED")
        return self

    def allocation_accepted(self, record, e_type):
        """Prepare a notification that an allocation request was accepted.

        Args:
            record: Extend record.
            e_type: Event type string (``"transformation"``, ``"activation"``,
                or other).

        Returns:
            The Mail instance for method chaining.
        """
        reason = record.decision if record.decision else None
        if e_type == "transformation":
            self.__project_init(record, "TRANSFORMATION ACCEPTED")
            self.__populate_values({"%TYPE_BEFORE": record.project.type,
                                    "%TYPE_AFTER": record.transform,
                                    "%REASON": reason})
        elif e_type == "activation":
            self.__project_init(record, "ACTIVATION ACCEPTED")
        else:
            self.__project_init(record, "ALLOCATION ACCEPTED")
            self.__populate_values({"%EXT": e_type, "%REASON": reason})
        return self

    def allocation_ignored(self, record, e_type):
        """Prepare a notification that an allocation request was ignored.

        Args:
            record: Extend record.
            e_type: Event type string.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "ALLOCATION IGNORED")
        rid = str(record.id)
        created = str(record.created)
        self.__populate_values({"%EXT": e_type, "%CREATED": created, "ID": rid})
        return self

    def allocation_rejected(self, record, extend_or_renew):
        """Prepare a notification that an allocation request was rejected.

        Args:
            record: Extend record.
            extend_or_renew: Event type string.

        Returns:
            The Mail instance for method chaining.
        """
        self.__project_init(record, "ALLOCATION REJECTED")
        reason = record.decision if record.decision else None
        self.__populate_values({"%EXT": extend_or_renew, "%REASON": reason})
        return self

    def task_accepted(self, task, comment=None):
        """Prepare a notification that a task was accepted.

        Args:
            task: Tasks record.
            comment: Optional additional comment.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("TECH")
        title = "Task id '%s' has been accepted" % task.id
        message = "Task '%s' has been accepted" % task.description()
        if comment is not None:
            message += "\nWith following comment: %s" % comment
        self.__populate_values({"%TITLE": title, "%MESSAGE": message})
        return self

    def task_rejected(self, task, comment=None):
        """Prepare a notification that a task was rejected.

        Args:
            task: Tasks record.
            comment: Optional additional comment.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("TECH")
        title = "Task id '%s' has been rejected" % task.id
        message = "Task '%s' has been rejected" % task.description()
        if comment is not None:
            message += "\nWith following comment: %s" % comment
        self.__populate_values({"%TITLE": title, "%MESSAGE": message})
        return self

    def log(self, log):
        """Prepare a notification about a generic log entry.

        Args:
            log: LogDB instance.

        Returns:
            The Mail instance for method chaining.
        """
        self.populate("TECH")
        title = "Log entry ID: %s" % log.id
        self.__populate_values({"%TITLE": title, "%MESSAGE": log.event})
        return self


class Sympa(Mail):
    """Email-based mailing list management via a Sympa server.

    Sends commands to the Sympa mailing list manager to add, subscribe,
    or unsubscribe email addresses.
    """

    def __init__(self, list_name):
        """Initialize the Sympa mailing list manager.

        Args:
            list_name: Key name in the configuration file's ``LIST`` section.
        """
        super().__init__()
        self.configure()
        self.list = self.cfg.get("LIST", list_name)
        self.destination = self.cfg.get("LIST", "SYMPA")

    def add(self, email, name=None):
        """Add an email address to the mailing list (quiet add).

        Args:
            email: Email address to add.
            name: Optional display name.

        Returns:
            Result of :meth:`Mail.start` (sends the email command).
        """
        self.sender = self.cfg.get("LIST", "ADMIN")
        if not self.sender:
            raise ValueError("Admin email is absent can't add to the list")
        if name:
            self.title = "QUIET ADD %s %s %s" % (self.list, email, name)
        else:
            self.title = "QUIET ADD %s %s" % (self.list, email)
        return self.start()

    def subscribe(self, email, name=None):
        """Subscribe an email address to the mailing list.

        Args:
            email: Email address to subscribe.
            name: Optional display name.

        Returns:
            Result of :meth:`Mail.start` (sends the email command).
        """
        self.sender = email
        if name:
            self.title = "SUBSCRIBE %s %s" % (self.list, name)
        else:
            self.title = "SUBSCRIBE %s" % self.list
        return self.start()

    def unsubscribe(self, email):
        """Unsubscribe an email address from the mailing list.

        Args:
            email: Email address to unsubscribe.

        Returns:
            Result of :meth:`Mail.start` (sends the email command).

        Raises:
            ValueError: If admin email is not configured.
        """
        self.sender = self.cfg.get("LIST", "ADMIN")
        if not self.sender:
            raise ValueError("Admin email is absent can't unsubscribe from the list")
        self.title = "QUIET DELETE %s %s" % (self.list, email)
        return self.start()


class UserMailingList(Sympa):
    """Mailing list manager for general user notifications."""

    def __init__(self):
        """Initialize with the ``USER_LIST`` configuration key."""
        super().__init__("USER_LIST")


class ResponsibleMailingList(Sympa):
    """Mailing list manager for project responsible notifications."""

    def __init__(self):
        """Initialize with the ``RESPONSIBLE_LIST`` configuration key."""
        super().__init__("RESPONSIBLE_LIST")
