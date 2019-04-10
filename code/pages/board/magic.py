from flask import current_app
from flask_login import current_user
from code.pages import check_int, check_str, send_message, check_json
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta as rd
from calendar import monthrange


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


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


def board_action():

    from code.database.schema import Extend

    data = check_json()
    eid = check_int(data["eid"])
    note = check_str(data["comment"])
    extend = Extend().query.filter(Extend.id == eid).one()
    if not extend:
        raise ValueError("No extension with id '%s' found" % eid)
    if extend.processed:
        raise ValueError("This request has been already processed")
    extend.processed = True
    extend.decision = note
    extend.approve = current_user
    return extend


def accept_message(extension):
    to = extension.project.responsible.email
    full = extension.project.responsible.full_name()
    name = extension.project.get_name()
    cpu = extension.hours
    ts = extension.created.strftime("%Y-%m-%d %X %Z"),
    comment = extension.decision
    title = "Project extension accepted"
    msg_body = "Dear %s\nThe extension of your project %s for %s hours made " \
               "%s has been accepted:\n%s" % (full, name, cpu, ts, comment)
    return message(to, msg_body, title)


def reject_message(extension):
    to = extension.project.responsible.email
    full = extension.project.responsible.full_name()
    name = extension.project.get_name()
    cpu = extension.hours
    ts = extension.created.strftime("%Y-%m-%d %X %Z"),
    comment = extension.decision
    title = "Project extension rejected"
    msg_body = "Dear %s\nThe extension of your project %s for %s hours made " \
               "%s has been rejected:\n%s" % (full, name, cpu, ts, comment)
    return message(to, msg_body, title)


def message(to, msg, title=None):
    by_who = current_app.config["EMAIL_PROJECT"]
    #cc = current_app.config["EMAIL_PROJECT"]
    cc = "matvey.sapunov@univ-amu.fr"
    if not title:
        title = "Concerning your project"
    return send_message(to, by_who, cc, title, msg)
