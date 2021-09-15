from flask_login import current_user
from base.database.schema import Extend
from operator import attrgetter
from base import db
from base.email import Mail
from base.database.schema import LogDB

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class Log:

    def __init__(self, project=None, register=None, user=None):
        self.log = LogDB(
            author=current_user,
            project=project,
            register=register,
            user=user)

    def commit(self, mail=None):
        db.session.add(self.log)
        db.session.commit()
        Mail().log(self.log).start()
        try:
            if mail: mail.start()
        finally:
            return self.log.event


class ProjectLog(Log):

    def __init__(self, project):
        super().__init__(project=project)
        self.project = project
        self.send = True

    def __commit(self, mail=None):
        db.session.add(self.log)
        db.session.commit()
        message = "%s: %s" % (self.project.get_name(), self.log.event)
        try:
            if mail and self.send: mail.start()
        finally:
            return message

    def commit_user(self, user):
        self.log.user = user
        return self.commit()

    def send_message(self, send=True):
        if send:
            self.send = True
        else:
            self.send = False
        return self

    def created(self, date):
        self.log.event = "Project created"
        if date:
            self.log.created = date
        return self.commit()

    def responsible_added(self, user):
        self.log.event = "Added a new project responsible %s with login %s" % (
            user.full_name(), user.login)
        return self.commit_user(user)

    def responsible_assign(self, user):
        self.log.event = "Made a request to assign new responsible %s" \
                         % user.full_name()
        return self.commit_user(user)

    def user_add(self, user):
        self.log.event = "Request to add a new user: %s %s <%s>" % (
            user.name, user.surname, user.email)
        return self.commit()

    def user_added(self, user):
        self.log.event = "Added a new user %s with login %s" % (
            user.full_name(), user.login)
        return self.commit_user(user)

    def user_assign(self, user):
        self.log.event = "Made a request to assign a new user %s" \
                         % user.full_name()
        return self.commit_user(user)

    def user_assigned(self, user):
        self.log.event = "User %s has been attached" % user.full_name()
        return self.commit_user(user)

    def user_deleted(self, user):
        self.log.event = "User %s (%s) has been deleted" % (
            user.full_name(), user.login)
        return self.commit_user(user)

    def user_del(self, user):
        self.log.event = "Made a request to delete user %s" % user.full_name()
        return self.commit_user(user)

    def renew(self, extension):
        article = "an exceptional" if extension.exception else "a"
        self.log.event = "Made %s request to renew project for %s hour(s)" \
                         % (article, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().project_renew(extension))

    def renewed(self, extension):
        self.log.event = "Renewal request for %s hour(s) has been processed" \
                         % extension.hours
        self.log.extension = extension
        return self.commit(Mail().project_renewed(extension))

    def extend(self, extension):
        article = "an exceptional" if extension.exception else "a"
        self.log.event = "Made %s request to extend project for %s hour(s)" \
                         % (article, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().project_extend(extension))

    def extended(self, extension):
        self.log.event = "Extension request for %s hour(s) has been processed" \
                         % extension.hours
        self.log.extension = extension
        return self.commit(Mail().project_extended(extension))

    def transform(self, extension):
        self.log.event = "Transformation request has been registered"
        self.log.extension = extension
        return self.commit(Mail().project_transform(extension))

    def transformed(self, extension):
        self.log.event = "Transformation to type %s finished successfully" \
                         % extension.transform
        self.log.extension = extension
        return self.commit(Mail().project_transformed(extension))

    def activate(self, extension):
        self.log.event = "Activation request has been registered"
        self.log.extension = extension
        return self.commit(Mail().project_activate(extension))

    def accept(self, extension):
        ext_or_new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is accepted" \
                         % (ext_or_new, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_accepted(extension, ext_or_new))

    def ignore(self, extension):
        new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is ignored" \
                         % (new, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_ignored(extension, new))

    def reject(self, extension):
        ext_or_new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is rejected" \
                         % (ext_or_new, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_rejected(extension, ext_or_new))

    def activity_report(self, file_rec):
        file_name = file_rec.path
        self.log.event = "Activity report saved on the server in the file %s" \
                         % file_name
        mail = Mail().report_uploaded(file_rec).attach_file(file_name)
        return self.commit(mail)

    def event(self, message):
        self.log.event = message.lower()
        return self.commit()


class RequestLog(Log):

    def __init__(self, project):
        super().__init__(register=project)
        self.pending = project

    def visa_sent(self):
        self.log.event = "Visa sent to %s" % self.pending.responsible_email
        return self.commit()

    def visa_skip(self):
        self.log.event = "Visa sending step has been skipped"
        return self.commit()

    def approve(self):
        self.log.event = "Project software requirements approved"
        return self.commit()

    def create(self):
        self.log.event = "Project created out of this request"
        return self.commit()

    def user_del(self, user):
        self.log.event = "Remove user %s" % user
        return self.commit()

    def user_add(self, user):
        self.log.event = "Add user %s" % user
        return self.commit()

    def user_change(self, info):
        self.log.event = "Change user info: %s" % info
        return self.commit()

    def request_change(self, info):
        self.log.event = "Change request info: %s" % info
        return self.commit()

    def accept(self):
        self.log.event = "Project creation request accepted"
        return self.commit()

    def reject(self):
        self.log.event = "Project creation request rejected"
        return self.commit()

    def ignore(self):
        self.log.event = "Project creation request ignored"
        return self.commit()


class UserLog(Log):

    def __init__(self, user):
        super().__init__(user=user)
        self.user = user

    def acl(self, acl):
        result = []
        for name, value in acl.items():
            result.append("%s to %s" % (name, value))
        self.log.event = "Set ACL permissions: %s" % "; ".join(result)
        return self.commit()

    def user_update(self, info):
        changes = []
        for name, value in info.items():
            old = getattr(self.user, name)
            prop = name.capitalize()
            changes.append("%s change: %s -> %s" % (prop, old, value))
        self.log.event = "; ".join(changes)
        return self.commit(Mail().user_update(self))

    def info_update(self, info=None, acl=None, projects=None, active=None):
        changes = []
        if info is not None:
            for name, value in info.items():
                old = getattr(self.user, name)
                prop = name.capitalize()
                changes.append("%s change: %s -> %s" % (prop, old, value))
        if acl is not None:
            for name, value in acl.items():
                old = getattr(self.user.acl, name)
                changes.append("ACL %s change %s -> %s" % (name, old, value))
        if active is not None:
            old = self.user.active
            changes.append("Set active status from %s to '%s'" % (old, active))
        if projects is not None:
            old = self.user.project_names()
            for name in projects:
                if name in old:
                    changes.append("Add to project %s" % name)
                else:
                    changes.append("Remove from project %s" % name)
        result = "; ".join(changes)
        self.log.event = "User information changes requested: %s" % result
        return self.commit(Mail().user_update(self))


class Extensions:
    def __init__(self, eid=None):
        if eid:
            self.id = eid
        else:
            self.id = False
        self.queue = Extend().query
        self.cpu = None
        self.extend = None
        self.rec = None
        self.ext = Extend

    def history(self, reverse=True):
        records = self.records()
        return sorted(records, key=attrgetter("created"), reverse=reverse)

    def unprocessed(self):
        return self.queue.filter_by(processed=False).all()

    def pending(self):
        recs = self.queue.filter_by(processed=True).filter_by(accepted=True) \
            .filter_by(done=False).all()
        return list(map(lambda x: x.api(), recs))

    def records(self):
        if self.id:
            return self.record()
        return self.queue.all()

    def record(self):
        if not self.id:
            return self.records()
        return self.queue.filter_by(id=self.id).one()

    @staticmethod
    def _process(record):
        record.processed = True
        record.approve = current_user
        db.session.commit()
        return record

    def ignore(self):
        record = self.record()
        if record.processed:
            raise ValueError("This request has been already processed")
        record.accepted = False
        record.decision = "Extension request has been ignored"
        return self._process(record)

    def reject(self, note):
        record = self.record()
        if record.processed:
            raise ValueError("This request has been already processed")
        record.accepted = False
        record.decision = note
        return self._process(record)

    def accept(self, note):
        self.rec = self.record()
        if self.rec.processed:
            raise ValueError("This request has been already processed")
        self.rec.decision = note

        if (self.extend is True or self.extend is False) and \
                self.rec.extend is not self.extend:
            self.rec.extend = self.extend
            self.rec.decision += "\nExtension option was manually set to %s" \
                                 % self.extend
        if self.cpu and (self.rec.hours != self.cpu):
            self.rec.hours = self.cpu
            self.rec.decision += "\nCPU value was manually set to %s" % self.cpu

        self.rec.accepted = True
        return self._process(self.rec)


class TmpUser:

    def __init__(self):
        self.login = None
        self.name = None
        self.surname = None
        self.email = None
        self.active = True
        self.is_user = True
        self.is_responsible = False
        self.is_manager = False
        self.is_tech = False
        self.is_committee = False
        self.is_admin = False

    def task_ready(self):
        u_part = "login: %s and name: %s and surname: %s and email: %s" % (
            self.login, self.name, self.surname, self.email)
        a_part = "user: %s, responsible: %s, manager: %s, tech: %s, " \
                 "committee: %s, admin: %s" % (self.is_user,
                                               self.is_responsible,
                                               self.is_manager, self.is_tech,
                                               self.is_committee, self.is_admin)
        return "%s WITH ACL %s WITH STATUS %s" % (u_part, a_part, self.active)


class Task:

    def __init__(self, task):
        self.task = task
        self.id = task.id

    def is_processed(self):
        return self.task.processed

    def done(self):
        self.task.done = True
        return self.commit()

    def description(self):
        return self.task.description()

    def accept(self):
        self.task.decision = "accept"
        Mail().task_accepted(self.task).send()
        return self.process()

    def ignore(self):
        self.task.decision = "ignore"
        return self.process()

    def reject(self):
        self.task.decision = "reject"
        Mail().task_rejected(self.task).send()
        return self.process()

    def action(self):
        return self.task.action

    def process(self):
        self.task.processed = True
        self.task.approve = current_user
        return self.commit()

    def commit(self):
        db.session.commit()
        return self.task