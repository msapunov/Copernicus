from flask import render_template, request, jsonify
from flask_login import login_required
from code.pages import ProjectLog, check_int, check_str, check_mail, TaskQueue
from code.pages import generate_login
from code.pages.user import bp
from code.pages.project.magic import get_project_info, get_project_record
from code.pages.project.magic import extend_update, get_limbo_users, get_users
from code.pages.user.magic import get_user_record
from datetime import datetime as dt
from operator import attrgetter


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/project/add/user", methods=["POST"])
@login_required
def web_project_add_user():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    name = check_str(data["name"].strip().lower())
    surname = check_str(data["surname"].strip().lower())
    auto = generate_login(name, surname)

    email = check_mail(data["email"].strip().lower())
    pid = check_int(data["project"])
    project = get_project_record(pid)

    from code import db
    from code.database.schema import LimboUser, User

    if User.query.filter(User.email == email).first():
        raise ValueError("User with e-mail %s has been registered already"
                         % email)
    user = LimboUser(name=name, surname=surname, email=email, login=auto,
                     active=False)
    db.session.commit()
    TaskQueue().project(project).user_create(user)
    msg = "Request to add a new user: %s %s <%s>" % (name, surname, email)
    return jsonify(message=ProjectLog(project).event(msg), data=get_users(pid))


@bp.route("/project/assign/user", methods=["POST"])
@login_required
def web_project_assign_user():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = check_int(data["project"])
    project = get_project_record(pid)
    login = list(map(lambda x: check_str(x), data["users"]))
    users = list(map(lambda x: get_user_record(x), login))

    for user in users:
        if user in project.users:
            raise ValueError("User %s is already in the project %s!" % (
                user.full_name(), project.get_name()
            ))
    list(map(lambda x: TaskQueue().project(project).user_assign(x), users))
    logs = list(map(lambda x: ProjectLog(project).user_assign(x), users))
    return jsonify(message="<br>".join(logs), data=get_users(pid))


@bp.route("/project/assign/responsible", methods=["POST"])
@login_required
def web_project_assign_responsible():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = check_int(data["project"])
    login = check_str(data["login"])
    project = get_project_record(pid)
    user = get_user_record(login)
    if user == project.responsible:
        raise ValueError("User %s is already responsible for the project %s" %
                         (user.full_name(), project.get_name()))
    TaskQueue().project(project).responsible_assign(user)
    return jsonify(message=ProjectLog(project).responsible_assign(user),
                   data=get_users(pid))


@bp.route("/project/delete/user", methods=["POST"])
@login_required
def web_project_delete_user():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = check_int(data["project"])
    login = check_str(data["login"].strip().lower())
    project = get_project_record(pid)
    users = list(map(lambda x: x.login, project.users))
    if login not in users:
        raise ValueError("User '%s' seems not to be registered in project '%s'"
                         % (login, project.get_name()))
    user = get_user_record(login)
    TaskQueue().project(project).user_remove(user)
    return jsonify(message=ProjectLog(project).user_del(user))


@bp.route("/project/transform", methods=["POST"])
@login_required
def web_project_transform():
    from code import db

    record = extend_update()
    record.transform = True
    db.session.add(record)
    db.session.commit()
    return jsonify(message=ProjectLog(record.project).transform(record))


@bp.route("/project/reactivate", methods=["POST"])
@login_required
def web_project_reactivate():
    from code import db

    record = extend_update()
    record.activate = True
    db.session.add(record)
    db.session.commit()
    return jsonify(message=ProjectLog(record.project).activate(record))


@bp.route("/project/extend", methods=["POST"])
@login_required
def web_project_extend():
    from code import db

    record = extend_update()
    db.session.add(record)
    db.session.commit()
    return jsonify(message=ProjectLog(record.project).extend(record))


@bp.route("/project/history", methods=["POST"])
@login_required
def web_project_history():
    from code.database.schema import LogDB

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = check_int(data["project"])
    recs = LogDB().query.filter(LogDB.project_id == pid).all()

    sorted_recs = sorted(recs, key=attrgetter("created"), reverse=True)
    result = list(map(lambda x: x.to_dict(), sorted_recs))
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
    get_limbo_users(projects)
    data = {"projects": projects, "renew": renew}
    return render_template("project.html", data=data)
