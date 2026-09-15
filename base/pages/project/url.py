"""URL routes for the project blueprint: sanity checks, activity reports,
user management, modal dialogs, and project info.
"""

from flask import flash, g, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from base.classes import ProjectLog, TaskQueue
from base.database.schema import LogDB, Project
from base.pages import grant_access
from base.pages.project import bp
from base.pages.project.form import (
    ActivateForm,
    ActivityForm,
    ExtendForm,
    RenewForm,
    ResponsibleForm,
    TransForm,
    UserForm,
    activate,
    activity,
    extend,
    get_transformation_options,
    new_responsible,
    new_user,
    renew,
    transform,
)
from base.pages.project.magic import (
    active_check,
    assign_responsible,
    check_responsible,
    clean_activity,
    get_future_users,
    get_project_by_name,
    get_project_record,
    get_reservation_options,
    get_ssh_options,
    is_activity_report,
    is_project_extendable,
    is_project_renewable,
    is_project_transformable,
    project_attach_user,
    project_create_user,
    project_extend,
    project_renew,
    project_transform,
    remove_activity,
    report_activity,
    sanity_check,
    save_activity,
)
from base.pages.user.form import KeyForm
from base.pages.user.magic import get_user_record

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/project/check/active", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def project_check_active():
    """Check project active status against SLURM data.

    Returns:
        JSON with result string.
    """
    return jsonify(data=active_check())


@bp.route("/project/sanity", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def project_sanity():
    """Run a sanity check on all active projects.

    Returns:
        JSON with result string.
    """
    return jsonify(data=sanity_check())


@bp.route("/project/activity/remove/<string:project>/<string:file_name>",
          methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def project_activity_remove(project, file_name):
    """Remove an uploaded activity file.

    Args:
        project: Project name.
        file_name: File to remove.

    Returns:
        JSON with result.
    """
    return jsonify(data=remove_activity(project, file_name))


@bp.route("/project/activity/clean/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def project_activity_clean(project_name):
    """Remove all uploaded activity files for a project.

    Args:
        project_name: Project name.

    Returns:
        JSON with result.
    """
    return jsonify(data=clean_activity(project_name))


@bp.route("/project/activity/upload", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def project_activity_upload():
    """Upload an activity file.

    Returns:
        JSON with saved file info.
    """
    return jsonify(data=save_activity(request))


@bp.route("/project/activity/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def project_activity(project_name):
    """Submit an activity report for a project.

    Args:
        project_name: Project name.

    Returns:
        JSON with log event message.
    """
    form = ActivityForm()
    report = report_activity(project_name, form)
    return jsonify(message=ProjectLog(report.project).activity_report(report))


@bp.route("/project/info/<string:name>", methods=["POST"])
@bp.route("/project/info", methods=["POST"])
@login_required
@grant_access("admin", "responsible", "tech")
def project_info(name=None):
    """Return project information as JSON.

    If a name is provided, only that project's info is returned.

    Args:
        name: Optional project name filter.

    Returns:
        JSON with list of project dictionaries.
    """
    projects = Project.query.all()
    if name:
        projects = [project for project in projects if project.name == name]
    return jsonify(data=list(map(lambda x: x.to_dict(), projects)))


@bp.route("/project/<string:project_name>/add/user", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_add_user(project_name):
    """Add a user (existing or new) to a project.

    Args:
        project_name: Project name.

    Returns:
        JSON with log event message.
    """
    form = UserForm()
    if not form.validate_on_submit():
        raise ValueError(form.error_message())
    project = check_responsible(project_name)
    if form.create_user:
        return jsonify(message=project_create_user(project, form))
    else:
        return jsonify(message=project_attach_user(project, form))


@bp.route("/project/<string:project_name>/assign/responsible", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_assign_responsible(project_name):
    """Assign a new responsible person to a project.

    Args:
        project_name: Project name.

    Returns:
        JSON with log event message.
    """
    form = ResponsibleForm()
    return jsonify(message=assign_responsible(project_name, form))


@bp.route("/project/delete/user", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_delete_user():
    """Delete a user from a project.

    Expects JSON with ``project`` and ``login`` fields.

    Returns:
        JSON with log event message.
    """
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid = data["project"]
    login = data["login"].strip().lower()
    project = get_project_record(pid)
    if "admin" not in current_user.permissions():
        if current_user != project.responsible:
            raise ValueError(
                "User %s is not authorized to modify project '%s'"
                % (current_user.login, project.get_name())
            )
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
    """Initiate a project transformation request.

    Args:
        project_name: Project name.

    Returns:
        JSON with log event message.
    """
    form = TransForm()
    form.new.choices = get_transformation_options()
    record = project_transform(project_name, form)
    return jsonify(message=ProjectLog(record.project).transform(record))


@bp.route("/project/activate/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_reactivate(project_name):
    """Reactivate a suspended project.

    Args:
        project_name: Project name.

    Returns:
        JSON with log event message.
    """
    form = ActivateForm()
    project = check_responsible(project_name)
    record = project_renew(project, form, active=True)
    record.activate = True
    return jsonify(message=ProjectLog(record.project).activate(record))


@bp.route("/project/renew/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_renew(project_name):
    """Renew a project's allocation.

    Args:
        project_name: Project name.

    Returns:
        JSON with log event message.
    """
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
    """Extend a project's allocation.

    Args:
        project_name: Project name.

    Returns:
        JSON with log event message.
    """
    form = ExtendForm()
    record = project_extend(project_name, form)
    return jsonify(message=ProjectLog(record.project).extend(record))


@bp.route("/project/history/<string:project_name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_project_history(project_name):
    """Return the event history for a project.

    Args:
        project_name: Project name.

    Returns:
        JSON with list of log dictionaries.
    """
    project = get_project_by_name(project_name)
    recs = LogDB().query.filter_by(project_id=project.id).all()
    return jsonify(data=list(map(lambda x: x.to_dict(), recs)))


@bp.route("/project/modal/assign/responsible/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_responsible(pid):
    """Render the assign-responsible modal for a project.

    Args:
        pid: Project ID.

    Returns:
        JSON with rendered HTML.
    """
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
    """Render the add-user modal for a project.

    Args:
        pid: Project ID.

    Returns:
        JSON with rendered HTML.
    """
    project = get_project_record(pid)
    form = new_user(get_ssh_options(project))
    return jsonify(render_template("modals/project_add_user.html", form=form))


@bp.route("/project/modal/transform/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_transform(pid):
    """Render the transform-project modal.

    Args:
        pid: Project ID.

    Returns:
        JSON with rendered HTML.
    """
    project = get_project_record(pid)
    form = transform(project)
    return jsonify(render_template("modals/project_transform_type.html", form=form))


@bp.route("/project/modal/renew/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_renew(pid):
    """Render the renew-project modal.

    Args:
        pid: Project ID.

    Returns:
        JSON with rendered HTML or error div.
    """
    project = get_project_record(pid)
    form = renew(project)
    if not form:
        return jsonify("<div>Error processing the form</div>")
    return jsonify(render_template("modals/project_renew_cpu.html", form=form))


@bp.route("/project/modal/extend/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_extend(pid):
    """Render the extend-project modal.

    Args:
        pid: Project ID.

    Returns:
        JSON with rendered HTML.
    """
    project = get_project_record(pid)
    form = extend(project)
    return jsonify(render_template("modals/project_extend_cpu.html", form=form))


@bp.route("/project/modal/activate/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_activate(pid):
    """Render the activate-project modal.

    Args:
        pid: Project ID.

    Returns:
        JSON with rendered HTML.
    """
    project = get_project_record(pid)
    form = activate(project)
    return jsonify(render_template("modals/project_activate_suspended.html", form=form))


@bp.route("/project/modal/history/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_history(pid):
    """Render the project history modal.

    Args:
        pid: Project ID.

    Returns:
        JSON with rendered HTML.
    """
    project = get_project_record(pid)
    history_url = url_for("project.web_project_history", project_name=project.name)
    return jsonify(render_template("modals/common_show_history.html",
                                   rec=project, url=history_url))


@bp.route("/project/modal/activity/<int:pid>", methods=["GET", "POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_activity(pid):
    """Render the activity report upload modal.

    Args:
        pid: Project ID.

    Returns:
        JSON with rendered HTML.
    """
    project = get_project_record(pid)
    form = activity(project)
    return jsonify(render_template("modals/project_upload_activity.html", form=form))


@bp.route("/project/modal/ssh/<string:login>", methods=["POST"])
@login_required
@grant_access("admin", "responsible")
def web_modal_ssh(login):
    """Render the SSH key upload modal for a user.

    Args:
        login: User login.

    Returns:
        JSON with rendered HTML.
    """
    if login not in g.user_list:
        raise ValueError(f"User with login '{login}' not found")
    form = KeyForm(login=login)
    form.username = login
    form.email = current_user.email
    return jsonify(render_template("modals/user_load_ssh.html", form=form))


@bp.route("/project.html", methods=["GET"])
@login_required
@grant_access("admin", "responsible")
def web_project_index():
    """Render the main project management page.

    Shows projects for which the current user is responsible, with
    transformation, extension, renewal, reservation, and SSH options.

    Returns:
        Rendered project.html template.
    """

    def set_users_len(x):
        """Set the ``users_length`` attribute on a project for template use.

        Args:
            x: A Project instance.

        Returns:
            The same Project instance with ``users_length`` set.
        """
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
    list(map(lambda x: get_reservation_options(x), projects))
    list(map(lambda x: get_ssh_options(x), projects))
    list(map(lambda x: set_users_len(x), projects))
    get_future_users(projects)
    return render_template("project.html", data={"projects": projects})
