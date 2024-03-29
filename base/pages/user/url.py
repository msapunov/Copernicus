from flask import render_template, request, jsonify, flash
from flask_login import login_required, current_user
from base.database.schema import User
from base.pages.user import bp
from base.pages.user.magic import get_user_record, get_jobs
from base.pages.user.magic import get_scratch, user_edit, ssh_key
from base.pages.user.form import edit_info, InfoForm, KeyForm
from base.utils import form_error_string
from datetime import datetime as dt, timezone
from operator import attrgetter
import logging as log


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/user/list/all", methods=["GET"])
@login_required
def user_all():
    return user_list(active=False)


@bp.route("/user/list", methods=["GET"])
@login_required
def user_list(active=True):
    term = request.args.get("term")
    if active:
        query = User.query.filter_by(active=active)
    else:
        query = User.query
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


@bp.route("/user/modal/ssh", methods=["POST"])
@login_required
def web_modal_ssh():
    log.info("Call to render upload ssh key modal")
    form = KeyForm()
    form.username = current_user.login
    form.email = current_user.email
    return jsonify(render_template("modals/user_load_ssh.html", form=form))


@bp.route("/user/modal/edit/<string:login>", methods=["POST"])
@login_required
def web_modal_edit(login):
    log.info("Call to render edit user info modal")
    user = get_user_record(login)
    form = edit_info(user)
    return jsonify(render_template("modals/user_edit_info.html", form=form))


@bp.route("/user/upload/ssh", methods=["POST"])
@login_required
def web_user_upload_ssh():
    log.info("Call to process new SSH key")
    form = KeyForm()
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    return jsonify(message=ssh_key(form))


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
    if not current_user.project:
        current_user.project = []
        flash("No projects found for user '%s'" % current_user.full())
    start = dt.now(timezone.utc)
    for project in current_user.project:
        if project.resources.created < start:
            start = project.resources.created
    begin = start.strftime("%m/%d/%y-%H:%M")
    finish = dt.now().strftime("%m/%d/%y-%H:%M")
    try:
        jobs = get_jobs(begin, finish)
    except ValueError as err:
        jobs = None
        flash(str(err))
    try:
        scratch = get_scratch()
    except ValueError as err:
        scratch = None
        flash(str(err))

    for project in current_user.project:
        every = project.account_by_user()
        if current_user.login in every:
            project.private = every[current_user.login]
        else:
            project.private = 0
        project.private_use = "{0:.1%}".format(
            float(project.private) / float(project.resources.cpu))

    return render_template("user.html", data={"user": current_user,
                                              "jobs": jobs,
                                              "scratch": scratch,
                                              "projects": current_user.project})
