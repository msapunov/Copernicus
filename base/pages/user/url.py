from flask import render_template, request, jsonify, flash
from flask_login import login_required
from base.pages import check_str, send_message
from base.pages.user import bp
from base.pages.user.magic import get_user_record, changes_to_string, get_jobs
from base.pages.user.magic import get_scratch, get_project_info
from base.utils import accounting_start
from datetime import datetime as dt
from operator import attrgetter


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/user/list", methods=["GET"])
@login_required
def user_list():
    from base.database.schema import User

    term = request.args.get("term")
    if term:
        term = "%%%s%%" % term.lower()
        users_obj = User.query.filter(User.surname.like(term)
                                      | User.name.like(term)
                                      | User.login.like(term)).all()
    else:
        users_obj = User.query.filter(User.active==True)\
            .filter(User.surname!="").all()
    users_obj = sorted(users_obj, key=attrgetter("login"))

    users = map(lambda x: {"id": x.id, "login": x.login,
                           "text": "%s <%s>" % (x.full_name(), x.login)},
                users_obj)
    user_list = list(users)
    return jsonify(results=user_list)


@bp.route("/user/edit/info", methods=["POST"])
@login_required
def user_edit_info():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    for arg in ["name", "surname", "email", "login"]:
        if arg not in data:
            raise ValueError("Expecting to have '%s' in the request" % arg)

    user = get_user_record(data["login"])
    old = {"name": user.name, "surname": user.surname, "email": user.email,
           "login": user.login}

    c_dict = {}
    for key in ["name", "surname", "email", "login"]:
        old_value = old[key].lower()
        new_value = check_str(data[key]).lower()
        if old_value == new_value:
            continue
        c_dict[key] = new_value

    if not c_dict:
        return jsonify(data="No changes in user's information found")

    from base.pages import TaskQueue
    TaskQueue().user(user).user_update(c_dict)
    title = "User's information change request"
    msg = "Your request for personal information change (%s) has been " \
          "registered" % changes_to_string(c_dict)
    send_message(user.email, title=title, message=msg)
    return jsonify(data=msg)


@bp.route("/exception_test", methods=["GET", "POST"])
@login_required
def exception_test():
    log.critical("Critical level")
    log.error("Error level")
    log.warning("warning level")
    log.info("Info level")
    log.debug("Debug level")
    raise ValueError("This is a test exception")


@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
@bp.route("/user.html", methods=["GET"])
@login_required
def user_index():
    start = accounting_start()
    end = dt.now().strftime("%m/%d/%y-%H:%M")
    user_record = get_user_record()
    user = {"full": user_record.full_name(),
            "name": user_record.name,
            "surname": user_record.surname,
            "email": user_record.email,
            "uid": user_record.uid,
            "login": user_record.login}
    try:
        jobs = get_jobs(start, end)
    except ValueError as err:
        jobs = None
        flash(err)
    try:
        scratch = get_scratch()
    except ValueError as err:
        scratch = None
        flash(err)
    try:
        projects = get_project_info(start, end)
    except ValueError as err:
        projects = None
        flash(err)

    return render_template("user.html", data={"user": user,
                                              "jobs": jobs,
                                              "scratch": scratch,
                                              "projects": projects})
