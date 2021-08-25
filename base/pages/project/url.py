from flask import render_template, request, jsonify, flash
from flask_login import login_required, current_user
from base import db
from base.database.schema import LogDB
from base.pages import (
    ProjectLog,
    check_int,
    check_str,
    TaskQueue,
    grant_access)
from base.pages.user import bp
from base.pages.user.magic import get_user_record, user_by_id
from base.pages.project.form import (
    transform, TransForm,
    activate, ActivateForm,
    extend, ExtendForm,
    new_user, UserForm,
    RenewForm, renew,
    get_transformation_options)
from base.pages.project.magic import (
    is_project_renewable,
    is_project_extendable,
    project_add_user,
    project_attach_user,
    extend_transform,
    project_info_by_name,
    is_activity_report,
    report_activity,
    remove_activity,
    clean_activity,
    save_activity,
    get_project_info,
    get_project_record,
    get_project_overview,
    list_of_projects,
    extend_update,
    get_limbo_users,
    get_users)
from operator import attrgetter
from logging import debug


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/project/activity/remove/<string:project>/<string:file_name>",
          methods=["POST"])
@login_required
def project_activity_remove(project, file_name):
    return jsonify(data=remove_activity(project, file_name))


@bp.route("/project/activity/clean/<string:project_name>", methods=["POST"])
@login_required
def project_activity_clean(project_name):
    return jsonify(data=clean_activity(project_name))


@bp.route("/project/activity/upload", methods=["POST"])
@login_required
def project_activity_upload():
    return jsonify(data=save_activity(request))


@bp.route("/project/activity/<string:project_name>", methods=["POST"])
@login_required
def project_activity(project_name):
    return jsonify(message=report_activity(project_name, request))


@bp.route("/project/info/<string:project_name>", methods=["POST"])
@login_required
def project_info(project_name):
    return jsonify(data=project_info_by_name(project_name))


@bp.route("/project/list", methods=["POST"])
@login_required
def project_list():
    return jsonify(data=list_of_projects())


@bp.route("/project/overview/annie", methods=["POST"])
@login_required
def project_overview_annie():
    return jsonify(data=get_project_overview())


@bp.route("/project/add/user", methods=["POST"])
@login_required
def web_project_add_user():
    form = UserForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    if form.create_user:
        project, user = project_add_user(form)
        response = ProjectLog(project).user_add(user)
    else:
        project, user = project_attach_user(form)
        response = ProjectLog(project).user_assign(user)
    return jsonify(message=response, data=get_users(project.id))


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


@bp.route("/project/set/responsible/<int:pid>", methods=["POST"])
@login_required
def web_project_set_responsible(pid):
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    project = get_project_record(pid)
    user = user_by_id(check_int(data["uid"]))
    if user == project.responsible:
        raise ValueError("User %s is already responsible for the project %s" %
                         (user.full_name(), project.get_name()))
    project.responsible = user
    db.session.commit()
    #TaskQueue().project(project).responsible_assign(user)
    return jsonify(message=ProjectLog(project).responsible_assign(user),
                   data=project.with_usage())


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
    form = TransForm()
    form.new.choices = get_transformation_options()
    record = extend_transform(form)
    return jsonify(message=ProjectLog(record.project).transform(record))


@bp.route("/project/reactivate", methods=["POST"])
@login_required
def web_project_reactivate():
    form = ActivateForm()
    record = extend_update(form)
    record.activate = True
    return jsonify(message=ProjectLog(record.project).activate(record))


@bp.route("/project/renew", methods=["POST"])
@login_required
def web_project_renew():
    form = ExtendForm()
    record = extend_update(form)
    if not is_activity_report(record):
        raise ValueError("Please upload an activity report first!")
    return jsonify(message=ProjectLog(record.project).renew(record))


@bp.route("/project/extend", methods=["POST"])
@login_required
def web_project_extend():
    form = ExtendForm()
    record = extend_update(form)
    return jsonify(message=ProjectLog(record.project).extend(record))


@bp.route("/project/history", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_history():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = check_int(data["project"])
    recs = LogDB().query.filter(LogDB.project_id == pid).all()

    sorted_recs = sorted(recs, key=attrgetter("created"), reverse=True)
    result = list(map(lambda x: x.to_dict(), sorted_recs))
    return jsonify(result)


@bp.route("/project/modal/attach/user/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_user(pid):
    project = get_project_record(pid)
    form = new_user(project)
    return jsonify(render_template("modals/project_add_user.html", form=form))


@bp.route("/project/modal/transform/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_transform(pid):
    project = get_project_record(pid)
    form = transform(project)
    return jsonify(render_template("modals/project_transform_type.html", form=form))


@bp.route("/project/modal/renew/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_renew(pid):
    project = get_project_record(pid)
    form = renew(project)
    if not form:
        return jsonify("<div>Error processing the form</div>")
    return jsonify(render_template("modals/project_renew_cpu.html", form=form))


@bp.route("/project/modal/extend/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_extend(pid):
    project = get_project_record(pid)
    form = extend(project)
    return jsonify(render_template("modals/project_extend_cpu.html", form=form))


@bp.route("/project/modal/activate/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_activate(pid):
    project = get_project_record(pid)
    form = activate(project)
    return jsonify(render_template("modals/project_activate_suspended.html", form=form))


@bp.route("/project/modal/history/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_history(pid):
    project = get_project_record(pid)
    return jsonify(render_template("modals/modal_history.html", form=project))


@bp.route("/project.html", methods=["GET"])
@login_required
@grant_access("admin", "responsible")
def web_project_index():
    projects = get_project_info(user_is_responsible=True)
    debug(projects)
    if not projects:
        flash("No projects associated with %s" % current_user.full_name())
        return render_template("project.html", data={})
    list(map(lambda x: clean_activity(x.get_name()), projects))
    get_limbo_users(projects)
    list(map(lambda x: is_project_extendable(x), projects))
    list(map(lambda x: is_project_renewable(x), projects))
    return render_template("project.html", data={"projects": projects})
