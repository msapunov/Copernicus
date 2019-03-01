from flask import render_template, request, jsonify
from flask_login import login_required
from code.pages import ProjectLog, check_int, check_str, TaskQueue
from code.pages.user import bp
from code.pages.project.magic import get_project_info, get_project_record
from code.pages.project.magic import send_activate_mail, send_transform_mail
from code.pages.project.magic import send_extend_mail, extend_update
from code.pages.user.url import get_user_record
from datetime import datetime as dt


@bp.route("/project/delete/user", methods=["POST"])
@login_required
def web_project_delete_user():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = check_int(data["project"])
    login = check_str(data["login"])
    project = get_project_record(pid)
    users = list(map(lambda x: x.login, project.users))
    if login not in users:
        raise ValueError("User '%s' seems not to be registered in project '%s'"
                         % (login, project.get_name()))
    user = get_user_record(login)
    TaskQueue().user_delete(user)
#    ProjectLog(project).user_del(user)

    return jsonify(message="Delete user request has been registered"
                           " successfully")


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
