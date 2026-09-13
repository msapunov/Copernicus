"""Business logic for the board: resource creation and extension processing."""

from logging import debug

from flask_login import current_user

from base.classes import Extensions, ProjectLog
from base.database.schema import Resources
from base.functions import calculate_ttl
from base.pages import check_json

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def create_resource(project, cpu):
    """Create a new Resources record for a project.

    Args:
        project: Project instance.
        cpu: Number of CPU hours.

    Returns:
        New Resources instance.

    Raises:
        Exception: If cpu is less than 1.
    """
    if cpu < 1:
        raise Exception("CPU hours must be greater than 0")
    return Resources(
        approve=current_user,
        valid=True,
        cpu=cpu,
        type=project.type,
        project=project.get_name(),
        ttl=calculate_ttl(project.type),
        treated=False
    )


def transform():
    """Process a transformation request from JSON input.

    Expects JSON with ``eid``, ``comment``, and optionally ``cpu``.

    Returns:
        Tuple of (record_id, log_message).
    """
    eid, note, cpu = get_arguments(True)
    record = Extensions(eid)
    if cpu > 0:
        record.cpu = cpu
    record.extend = False
    record.transform(note)
    message = ProjectLog(record.rec.project).accept(record.rec)
    return record.id, message


def get_arguments(trans=False):
    """Extract and validate arguments from a JSON request.

    Args:
        trans: If True, only require eid, comment, cpu (no extension flag).

    Returns:
        Tuple of (eid, note, cpu[, ext]).
    """
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