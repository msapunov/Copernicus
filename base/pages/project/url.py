from flask import render_template, request, jsonify, flash
from flask_login import login_required, current_user
from base.classes import ProjectLog
from base.database.schema import LogDB, Project
from base.pages import (
    TaskQueue,
    grant_access)
from base.pages.project import bp
from base.pages.user.magic import get_user_record
from base.pages.project.form import (
    new_responsible, ResponsibleForm,
    transform, TransForm,
    activate, ActivateForm,
    extend, ExtendForm,
    new_user, UserForm,
    renew, RenewForm,
    activity, ActivityForm,
    get_transformation_options)
from base.pages.project.magic import (
    is_project_transformable,
    check_responsible,
    active_check,
    sanity_check,
    assign_responsible,
    set_consumed_users,
    get_project_by_name,
    is_project_renewable,
    is_project_extendable,
    project_create_user,
    project_attach_user,
    project_transform,
    is_activity_report,
    report_activity,
    remove_activity,
    clean_activity,
    save_activity,
    get_project_record,
    project_extend,
    project_renew,
    get_future_users)
from logging import debug


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/project/check/active", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def project_check_active():
    return jsonify(data=active_check())


@bp.route("/project/sanity", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def project_sanity():
    return jsonify(data=sanity_check())


@bp.route("/project/activity/remove/<string:project>/<string:file_name>",
          methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def project_activity_remove(project, file_name):
    return jsonify(data=remove_activity(project, file_name))


@bp.route("/project/activity/clean/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def project_activity_clean(project_name):
    return jsonify(data=clean_activity(project_name))


@bp.route("/project/activity/upload", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def project_activity_upload():
    return jsonify(data=save_activity(request))


@bp.route("/project/activity/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def project_activity(project_name):
    form = ActivityForm()
    report = report_activity(project_name, form)
    return jsonify(message=ProjectLog(report.project).activity_report(report))


@bp.route("/project/info/<string:name>", methods=["POST"])
@bp.route("/project/info", methods=["POST"])
@login_required
@grant_access("admin", "responsible", "tech")
def project_info(name=None):
    projects = Project.query.all()
    if name:
        projects = [project for project in projects if project.name == name]
    return jsonify(data=list(map(lambda x: x.to_dict(), projects)))


@bp.route("/project/<string:project_name>/add/user", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_add_user(project_name):
    form = UserForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    if form.create_user:
        return jsonify(message=project_create_user(project_name, form))
    else:
        return jsonify(message=project_attach_user(project_name, form))


@bp.route("/project/<string:project_name>/assign/responsible", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_assign_responsible(project_name):
    form = ResponsibleForm()
    return jsonify(message=assign_responsible(project_name, form))


@bp.route("/project/delete/user", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_delete_user():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = data["project"]
    login = data["login"].strip().lower()
    project = get_project_record(pid)
    users = list(map(lambda x: x.login, project.users))
    if login not in users:
        raise ValueError("User '%s' seems not to be registered in project '%s'"
                         % (login, project.get_name()))
    user = get_user_record(login)
    task = TaskQueue().project(project).user_remove(user).task
    return jsonify(message=ProjectLog(project).user_delete(task))


@bp.route("/project/transform/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_transform(project_name):
    form = TransForm()
    form.new.choices = get_transformation_options()
    record = project_transform(project_name, form)
    return jsonify(message=ProjectLog(record.project).transform(record))


@bp.route("/project/activate/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_reactivate(project_name):
    form = ActivateForm()
    project = check_responsible(project_name)
    record = project_renew(project, form, active=True)
    record.activate = True
    return jsonify(message=ProjectLog(record.project).activate(record))


@bp.route("/project/renew/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_renew(project_name):
    form = RenewForm()
    project = check_responsible(project_name)
    if not is_activity_report(project):
        raise ValueError("Please upload an activity report first!")
    record = project_renew(project, form)
    return jsonify(message=ProjectLog(project).renew(record))


@bp.route("/project/extend/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_extend(project_name):
    form = ExtendForm()
    record = project_extend(project_name, form)
    return jsonify(message=ProjectLog(record.project).extend(record))


@bp.route("/project/history/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_history(project_name):
    project = get_project_by_name(project_name)
    recs = LogDB().query.filter_by(project_id=project.id).all()
    return jsonify(data=list(map(lambda x: x.to_dict(), recs)))


@bp.route("/project/modal/assign/responsible/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_responsible(pid):
    project = get_project_record(pid)
    if "admin" in current_user.permissions():
        form = new_responsible(project, True)
    else:
        form = new_responsible(project, False)
    return jsonify(render_template("modals/project_add_responsible.html", form=form))


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
    return jsonify(render_template("modals/project_show_history.html", form=project))


@bp.route("/project/modal/activity/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_activity(pid):
    project = get_project_record(pid)
    form = activity(project)
    return jsonify(render_template("modals/project_upload_activity.html", form=form))


@bp.route("/project.html", methods=["GET"])
@login_required
@grant_access("admin", "responsible")
def web_project_index():
    def set_users_len(x):
        x.users_length = len(x.users)
        return x
    projects = Project.query.filter_by(responsible=current_user).all()
    if not projects:
        flash("No projects associated with %s found" % current_user.full_name())
        return render_template("project.html", data={})
    list(map(lambda x: clean_activity(x.get_name()), projects))
    list(map(lambda x: is_project_transformable(x), projects))
    list(map(lambda x: is_project_extendable(x), projects))
    list(map(lambda x: is_project_renewable(x), projects))
    list(map(lambda x: set_users_len(x), projects))
    list(map(lambda x: set_consumed_users(x), projects))
    get_future_users(projects)
    return render_template("project.html", data={"projects": projects})
