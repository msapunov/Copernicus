from flask import current_app
from flask_login import current_user
from code.pages import check_int, check_str, send_message, check_json
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta as rd
from calendar import monthrange
from operator import attrgetter


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class Extensions:
    def __init__(self, eid=None):
        from code.database.schema import Extend

        if eid:
            self.id = eid
        self.queue = Extend().query
        self.ext = Extend

    def history(self, reverse=True):
        records = self.records()
        return sorted(records, key=attrgetter("created"), reverse=reverse)

    def unprocessed(self):
        return self.queue.filter_by(processed=False).all()

    def pending(self):
        return self.queue.filter_by(processed=False).filter_by(accepted=True)\
            .all()

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
        from code import db
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
        record = self.record()
        if record.processed:
            raise ValueError("This request has been already processed")
        record.accepted = True
        record.decision = note
        return self._process(record)


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

    from code.database.schema import Resources

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
    return eid, note
