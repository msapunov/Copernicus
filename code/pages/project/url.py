from flask import render_template, request, jsonify, current_app
from flask_login import login_required
from code.pages import ProjectLog, check_int, check_str
from code.pages import send_message
from code.pages.user import bp
from code.pages.project.magic import get_project_info, get_project_consumption

from datetime import datetime as dt


def send_extend_mail(project, extend):
    subj = "Request extend project %s" % project.name
    msg = """
    Dear %s
    You have requested to extend your project %s with %s hours
    Extension reason is:
      %s
    Your request will be examined shortly
    """ % (project.responsible.full_name(), project.name, extend.hours,
           extend.reason)
    project_email(project.responsible.email, subj, msg)


def send_activate_mail(project, extend):
    subj = "Request to activate project %s" % project.name
    msg = """
    Dear %s
    You have requested to activate your suspended project %s
    The reason for activation is:
      %s
    Your request will be examined shortly
    """ % (project.responsible.full_name(), project.name, extend.reason)
    project_email(project.responsible.email, subj, msg)


def send_transform_mail(project, extend):
    subj = "Request to transform project %s" % project.name
    msg = """
    Dear %s
    You have requested to transform your project %s of type A to type B
    The reason for transformation is:
      %s
    Your request will be examined shortly
    """ % (project.responsible.full_name(), project.name, extend.reason)
    project_email(project.responsible.email, subj, msg)


def project_email(to, title, msg):
    by_who = current_app.config["EMAIL_PROJECT"]
    return jsonify(data=send_message(to, by_who=by_who, title=title,
                                     message=msg))


@bp.route("/project/transform", methods=["POST"])
@login_required
def web_project_transform():
    from code import db

    record = extend_update()
    record.transform = True
    db.session.add(record)
    ProjectLog(record.project).transform(record)
    db.session.commit()
    send_transform_mail(record.project, record)
    return jsonify(message="Project transformation request has been registered"
                           " successfully")


@bp.route("/project/reactivate", methods=["POST"])
@login_required
def web_project_reactivate():
    from code import db

    record = extend_update()
    record.activate = True
    db.session.add(record)
    ProjectLog(record.project).activate(record)
    db.session.commit()
    send_activate_mail(record.project, record)
    return jsonify(message="Project activation has been registered "
                           "successfully")


@bp.route("/project/extend", methods=["POST"])
@login_required
def web_project_extend():
    from code import db

    record = extend_update()
    db.session.add(record)
    ProjectLog(record.project).extend(record)
    db.session.commit()
    send_extend_mail(record.project, record)
    return jsonify(message="Project extension has been registered successfully")


def extend_update():
    from code.database.schema import Extend, Project

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")

    if "project" in data:
        pid = check_int(data["project"])
    else:
        raise ValueError("Project ID is missing")
    if "cpu" in data:
        cpu = check_int(data["cpu"])
    else:
        cpu = 0
    if "note" in data:
        note = check_str(data["note"])
    else:
        raise ValueError("Comment is absent")

    project = Project().query.filter_by(id=pid).first()
    if not project:
        raise ValueError("Failed to find a project with id: %s" % pid)

    p_name = project.get_name()
    p_info = get_project_consumption([p_name])
    if not p_info:
        use = 0
    else:
        use = p_info[p_name]["total"]
    maximum = project.resources.cpu
    if not use:
        usage = 0
    else:
        usage = "{0:.1%}".format(float(use)/float(maximum))
    return Extend(project=project, hours=cpu, reason=note, present_use=use,
                  usage_percent=usage, present_total=maximum)


@bp.route("/project/history", methods=["POST"])
@login_required
def web_project_history():
    from code.database.schema import LogDB

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = check_int(data["project"])
    recs = LogDB().query.filter(LogDB.project_id == pid).all()
    result = list(map(lambda x: x.to_dict(), recs))
    return jsonify(result)


@bp.route("/project.html", methods=["GET"])
@login_required
def web_project_index():
    projects = get_project_info()
    now = dt.now()
    if now.month != 1:
        renew = False
    else:
        renew = now.year
    data = {"projects": projects, "renew": renew}
    return render_template("project.html", data=data)
