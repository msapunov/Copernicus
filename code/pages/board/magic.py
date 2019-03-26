from flask import request, current_app
from flask_login import current_user
from code.pages import check_int, check_str, send_message
from code.pages.project.magic import get_project_record
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta


def board_action():

    from code.database.schema import Extend

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    eid = check_int(data["eid"])
    note = check_str(data["comment"])
    cpu = check_int(data["cpu"])

    extend = Extend().query.filter(Extend.id == eid).one()
    if not extend:
        raise ValueError("No extension with id '%s' found" % eid)
    if extend.processed:
        raise ValueError("This request has been already processed")
    if (not cpu) or (cpu <= 0):
        cpu = extend.hours

    project = get_project_record(extend.project.id)
    from code.database.schema import Resources
    from code import db

    now = dt.now()
    if project.type == "a":
        month = int(current_app.config["ACC_TYPE_A"])
        ttl = now + relativedelta(month=+month)
    elif project.type == "h":
        month = int(current_app.config["ACC_TYPE_H"])
        ttl = now + relativedelta(month=+month)
    else:  # For project type B
        day = int(current_app.config["ACC_START_DAY"])
        month = int(current_app.config["ACC_START_MONTH"])
        year = now.year + 1
        ttl = dt(year, month, day)

    resource = Resources(
        approve=current_user,
        valid=True,
        cpu=cpu,
        type=project.type,
        ttl=ttl
    )
    db.session.add(resource)
    project.resources = resource
    extend.processed = True
    extend.decision = note
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
