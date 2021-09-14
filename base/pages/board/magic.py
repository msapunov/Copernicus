from flask_login import current_user
from base.classes import ProjectLog
from base.pages import check_str, check_json, calculate_ttl
from base.functions import projects_consumption
from base.database.schema import Extend, Resources
from operator import attrgetter
from base import db
from logging import debug


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


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
        records = self.queue.filter_by(processed=False).all()
        projects = list(map(lambda x: x.project, records))
        consumption = projects_consumption(projects)
        for i in records:
            project = list(filter(lambda x: i.project.name == x.name, consumption))
            if len(project) < 1:
                continue
            i.project = project[0]
#            if len(project) < 1:
#                i.consumed = "Undefined"
#                i.consumed_use = "Undefined"
#            else:
#                i.consumed = str(project[0].consumed)
#                i.consumed_use = str(project[0].consumed_use) + "%"
        return records

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

    def transform(self, note):
        self.rec = self.record()
        if self.rec.processed:
            raise ValueError("This request has been already processed")
        self.rec.decision = note
        if not self.rec.transform:
            raise ValueError("This request is not transformation one")
        self.rec.accepted = True
        return self._process(self.rec)

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


def ignore_extension(eid):
    return Extensions(eid).ignore()


def reject_extension(eid):
    data = check_json()
    note = check_str(data["comment"])
    if not note:
        raise ValueError("Please indicate reason for rejection extension")
    record = Extensions(eid)
    return record.reject(note)


def create_resource(project, cpu):
    return Resources(
        approve=current_user,
        valid=True,
        cpu=cpu,
        type=project.type,
        project=project.get_name(),
        ttl=calculate_ttl(project),
        treated=False
    )


def transform():
    eid, note, cpu = get_arguments(True)
    record = Extensions(eid)
    if cpu > 0:
        record.cpu = cpu
    record.extend = False
    record.transform(note)
    message = ProjectLog(record.rec.project).transform(record.rec)
    return record.id, message


def get_arguments(trans=False):
    data = check_json()

    eid = int(data["eid"]) if "eid" in data else None
    debug("Extension's ID: %s" % eid)
    if not eid:
        raise ValueError("No extension ID provided")

    note = str(data["comment"]) if "comment" in data else None
    debug("Extension's comment value: %s" % note)
    if not note:
        raise ValueError("Provide a comment please!")

    cpu = int(data["cpu"]) if "cpu" in data else 0
    debug("Extension's CPU value: %s" % cpu)
    if cpu < 0:
        raise ValueError("CPU can't be a negative value!")

    extension = str(data["extension"].lower()) if "extension" in data else None
    debug("Extension flag value: %s" % extension)
    if extension == "true":
        ext = True
    elif extension == "false":
        ext = False
    else:
        ext = None
    if not trans and ext is None:
        raise ValueError("Failed to get value of extension variable")

    if trans:
        return eid, note, cpu
    return eid, note, cpu, ext
