from flask import current_app
from flask_login import current_user
from base.pages import check_int, check_str, check_json
from base.database.schema import Extend
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta as rd
from calendar import monthrange
from operator import attrgetter
from base import db


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
        return self.queue.filter_by(processed=False).all()

    def pending(self):
        return self.queue.filter_by(processed=True).filter_by(done=False).all()

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

        if self.extend and (self.rec.extend != self.extend):
            self.rec.extend = self.extend
            self.rec.decision += "\nExtension option was manually set to %s"\
                                 % self.extend
        if self.cpu and (self.rec.hours != self.cpu):
            self.rec.hours = self.cpu
            self.rec.decision += "\nCPU value was manually set to %s" % self.cpu

        self.rec.accepted = True
        return self._process(self.rec)


def create_resource(project, cpu):
    now = dt.now()
    if project.type == "a":
        month = int(current_app.config.get("ACC_TYPE_A", 6))
        ttl = now + rd(month=+month)
    elif project.type == "h":
        month = int(current_app.config.get("ACC_TYPE_H", 6))
        ttl = now + rd(month=+month)
    else:  # For project type B
        year = now.year + 1
        month = int(current_app.config.get("ACC_START_MONTH", 3))
        if "ACC_START_DAY" in current_app.config:
            day = int(current_app.config.get("ACC_START_DAY", 1))
        else:
            day = monthrange(year, month)[1]
        ttl = dt(year, month, day, 0, 0, 0)

    from base.database.schema import Resources

    resource = Resources(
        approve=current_user,
        valid=True,
        cpu=cpu,
        type=project.type,
        project=project.get_name(),
        ttl=ttl,
        treated=False
    )
    return resource


def get_arguments():
    data = check_json()
    eid = check_int(data["eid"])
    note = check_str(data["comment"])

    ext = check_str(data["extension"]).lower()
    extension = False
    if ext == "true":
        extension = True

    cpu = check_int(data["cpu"])
    if (not cpu) or (cpu <= 0):
        raise ValueError("CPU value is absent, zero or a negative value!")

    return eid, note, cpu, extension
