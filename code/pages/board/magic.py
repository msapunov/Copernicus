from flask import current_app
from flask_login import current_user
from code.pages import check_int, check_str, send_message, check_json


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


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
