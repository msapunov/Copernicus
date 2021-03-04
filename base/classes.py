from flask_login import current_user
from base.database.schema import Extend
from operator import attrgetter
from base import db
from base.database.schema import LogDB, User


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class Log:

    def __init__(self):
        self.log = LogDB(author=current_user)

    def _commit(self):
        db.session.add(self.log)
        db.session.commit()
        return self.log.event


class RequestLog(Log):

    def __init__(self, project):
        super().__init__()
        self.pending = project
        self.log = LogDB(author=current_user, register=project)
        self.send = True

    def visa_sent(self):
        self.log.event = "Visa sent to %s" % self.pending.responsible_email
        return self._commit()

    def visa_skip(self):
        self.log.event = "Visa sending step has been skipped"
        return self._commit()

    def approve(self):
        self.log.event = "Project software requirements approved"
        return self._commit()

    def create(self):
        self.log.event = "Project created out of this request"
        return self._commit()

    def user_del(self, user):
        self.log.event = "Remove user %s" % user
        return self._commit()

    def user_add(self, user):
        self.log.event = "Add user %s" % user
        return self._commit()

    def user_change(self, info):
        self.log.event = "Change user info: %s" % info
        return self._commit()

    def request_change(self, info):
        self.log.event = "Change request info: %s" % info
        return self._commit()

    def accept(self):
        self.log.event = "Project creation request accepted"
        return self._commit()

    def reject(self):
        self.log.event = "Project creation request rejected"
        return self._commit()

    def ignore(self):
        self.log.event = "Project creation request ignored"
        return self._commit()


class UserLog(Log):

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.log = LogDB(author=current_user, user=user)
        self.send = True

    def acl(self, acl):
        result = []
        for name, value in acl.items():
            result.append("%s to %s" % (name, value))
        self.log.event = "Set ACL permissions: %s" % "; ".join(result)
        return self._commit()

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
        return self._commit()


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
        recs = self.queue.filter_by(processed=True).filter_by(accepted=True)\
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
            self.rec.decision += "\nExtension option was manually set to %s"\
                                 % self.extend
        if self.cpu and (self.rec.hours != self.cpu):
            self.rec.hours = self.cpu
            self.rec.decision += "\nCPU value was manually set to %s" % self.cpu

        self.rec.accepted = True
        return self._process(self.rec)
