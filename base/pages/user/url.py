"""URL routes for the user blueprint: user lists, SSH key management,
user info editing, and the user home page.
"""

import logging as log
from datetime import datetime as dt
from datetime import timezone
from operator import attrgetter

from flask import flash, jsonify, render_template, request
from flask_login import current_user, login_required

from base.database.schema import User
from base.functions import form_error_string
from base.pages import grant_access
from base.pages.user import bp
from base.pages.user.form import InfoForm, KeyForm, edit_info
from base.pages.user.magic import (
    absent_users_check,
    archived_users_check,
    get_jobs,
    get_pending_projects,
    get_scratch,
    get_user_record,
    inactive_users_check,
    ssh_key,
    user_edit,
    working_users_check,
)


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/user/check/active", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def user_check_active():
    """Compare users in DB against a list from the remote server.

    Archives missing users, deactivates inactive ones, and activates
    restored ones.

    Returns:
        JSON with result summary.
    """
    raw_data = request.get_data()
    if not raw_data:
        return jsonify(data="No data received")
    logins = raw_data.decode("utf-8", errors="replace").split("\n")
    result = ""
    archive = archived_users_check(logins)
    if archive:
        result += "Archived user(s):\n%s" % "\n".join(archive)
    inactive = inactive_users_check(logins)
    if inactive:
        result += "Deactivated user(s):\n%s" % "\n".join(inactive)
    working = working_users_check(logins)
    if working:
        result += "Activated user(s):\n%s" % "\n".join(working)
    absent = absent_users_check(logins)
    log.debug(f"Absent users: {len(absent)}")
    if absent:
        result += "Absent user(s):\n%s" % "\n".join(absent)
    return jsonify(data=result)


@bp.route("/user/list/all", methods=["GET"])
@login_required
def user_all():
    """Return a list of all users (including inactive).

    Returns:
        JSON with user list.
    """
    return user_list(active=False)


@bp.route("/user/list", methods=["GET"])
@login_required
def user_list(active=True):
    """Return a filtered list of users as JSON for select2.

    Supports search via the ``term`` query parameter.

    Args:
        active: If True, only return active users.

    Returns:
        JSON with ``results`` list of user dicts.
    """
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
    """Render the SSH key upload modal for the current user.

    Returns:
        JSON with rendered HTML.
    """
    log.info("Call to render upload ssh key modal")
    form = KeyForm()
    form.username = current_user.login
    form.email = current_user.email
    return jsonify(render_template("modals/user_load_ssh.html", form=form))


@bp.route("/user/modal/edit/<string:login>", methods=["POST"])
@login_required
def web_modal_edit(login):
    """Render the edit-user-info modal.

    Args:
        login: User login.

    Returns:
        JSON with rendered HTML.
    """
    log.info("Call to render edit user info modal")
    user = get_user_record(login)
    form = edit_info(user)
    return jsonify(render_template("modals/user_edit_info.html", form=form))


@bp.route("/user/upload/ssh", methods=["POST"])
@login_required
def web_user_upload_ssh():
    """Process an SSH public key upload.

    Returns:
        JSON with status message.
    """
    log.info("Call to process new SSH key")
    form = KeyForm()
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    return jsonify(message=ssh_key(form))


@bp.route("/user/edit/<string:login>", methods=["POST"])
@login_required
def web_user_edit(login):
    """Process a user information edit request.

    Args:
        login: User login.

    Returns:
        JSON with status message.
    """
    log.info("Call to process new user's info")
    form = InfoForm()
    return jsonify(message=user_edit(login, form))


@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
@bp.route("/user.html", methods=["GET"])
@login_required
def user_index():
    """Render the user home page with projects, jobs, and scratch info.

    For managers, shows pending project requests instead.

    Returns:
        Rendered user.html template.
    """
    if current_user.acl.is_manager:
        pending = get_pending_projects()
        if not pending:
            flash("Looks like there are no new project requests at the moment")
        return render_template("user.html", data={"user": current_user,
                                                  "external": True,
                                                  "pending": pending})
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
