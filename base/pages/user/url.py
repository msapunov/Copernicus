from flask import render_template, request, jsonify, flash
from flask_login import login_required
from base.database.schema import User
from base.pages.user import bp
from base.pages.user.magic import get_user_record, get_jobs
from base.pages.user.magic import get_scratch, user_edit
from base.pages.project.magic import get_project_info
from base.pages.user.form import EditInfo, InfoForm
from base.utils import accounting_start
from datetime import datetime as dt
from operator import attrgetter
import logging as log


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/user/list", methods=["GET"])
@login_required
def user_list(active=True):
    term = request.args.get("term")
    query = User.query.filter(User.active == active)
    if term:
        term = "%%%s%%" % term.lower()
        users_obj = query.filter(User.surname.like(term)
                                 | User.name.like(term)
                                 | User.login.like(term)).all()
    else:
        users_obj = query.filter(User.surname != "").all()
    users_obj = sorted(users_obj, key=attrgetter("login"))
    users = map(lambda x:
                {"id": x.id, "login": x.login, "text": x.full()},
                users_obj)
    users_list = list(users)
    return jsonify(results=users_list)


@bp.route("/user/modal/edit/<string:login>", methods=["POST"])
@login_required
def web_modal_edit(login):
    log.info("Call to render edit user info modal")
    user = get_user_record(login)
    form = EditInfo(user)
    return jsonify(render_template("modals/user_edit_info.html", form=form))


@bp.route("/user/edit/<string:login>", methods=["POST"])
@login_required
def web_user_edit(login):
    log.info("Call to process new user's info")
    form = InfoForm()
    return jsonify(message=user_edit(login, form))


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
        projects = get_project_info()
    except ValueError as err:
        projects = None
        flash(err)

    return render_template("user.html", data={"user": user,
                                              "jobs": jobs,
                                              "scratch": scratch,
                                              "projects": projects})
