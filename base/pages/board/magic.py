from flask_login import current_user
from base.classes import ProjectLog
from base.pages import check_str, check_json
from base.functions import projects_consumption, calculate_ttl
from base.database.schema import Extend, Resources
from operator import attrgetter
from base import db
from logging import debug


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


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
