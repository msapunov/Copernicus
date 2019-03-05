from flask import render_template, request, jsonify, flash
from flask.json import dumps
from flask_login import login_required
from code.pages import check_str, send_message
from code.pages.user import bp
from code.pages.user.magic import get_user_record, changes_to_string, get_jobs
from code.pages.user.magic import get_scratch, get_project_info
from code.utils import accounting_start
from datetime import datetime as dt


@bp.route("/user/edit/info", methods=["POST"])
@login_required
def user_edit_info():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")

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

    c_dict["entity"] = "user"
    changes = dumps(c_dict)

    from code.pages import TaskQueue
    TaskQueue().user_change(changes)
    title = "User's information change request"
    msg = "Your request for personal information change (%s) has been " \
          "registered" % changes_to_string(c_dict)
    send_message(user.email, title=title, message=msg)
    return jsonify(data=msg)


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
