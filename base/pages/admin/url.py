"""URL routes for the admin blueprint: registration processing, user
management, task queue, server monitoring, and configuration views.
"""

from datetime import datetime as dt
from datetime import timezone as tz
from logging import debug

from flask import (
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, login_user

from base.classes import Extensions, Pending
from base.database.schema import Project, Resources, User
from base.functions import (
    show_configuration,
    slurm_nodes_status,
    ssh_wrapper,
    form_error_string,
)
from base.pages import Task, grant_access
from base.pages.admin import bp
from base.pages.admin.form import (
    ActivateUserForm,
    AddUserForm,
    CreateForm,
    EditResponsibleForm,
    NewUserEditForm,
    NewUserForm,
    PendingActionForm,
    RegistrationEditForm,
    TaskEditForm,
    UserEditForm,
    VisaPendingForm,
)
from base.pages.admin.magic import (
    TaskManager,
    account_days,
    all_users,
    event_log,
    get_server_info,
    last_user,
    process_task,
    process_user_form,
    registration_record_edit,
    registration_responsible_edit,
    registration_user_add,
    registration_user_del,
    registration_user_update,
    render_pending,
    render_registry,
    render_task,
    slurm_partition_info,
    space_info,
    task_history,
    unprocessed_dict,
    user_create_by_admin,
    user_delete,
    user_info_update,
    user_reset_pass,
    user_send_welcome,
    user_set_pass,
)
from base.pages.project.magic import process_extension
from base.pages.user.magic import get_user_record, user_by_id

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/test", methods=["GET"])
@bp.route("/test.html", methods=["GET"])
@login_required
@grant_access("admin")
def web_test():
    """Render the test page with project data.

    Returns:
        Rendered test.html template.
    """
    return render_template("test.html", data="test")


@bp.route("/admin/info/projects", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def admin_info_projects():
    """Return project info with user login and resource details.

    Returns:
        JSON list of project info dictionaries.
    """
    debug("Starting query for Project, User, Resources join")
    projects = (
        Project.query.join(User, Project.responsible_id == User.id)
        .join(Resources, Project.resources_id == Resources.id)
        .with_entities(
            Project.id,
            Project.type,
            Project.name,
            Resources.cpu,
            Resources.created,
            Resources.ttl,
            User.login,
        )
        .all()
    )
    debug(f"Query returned {len(projects)} rows")
    result = [
        {
            "id": pid,
            "type": ptype,
            "name": name,
            "cpu": cpu,
            "created": created.strftime("%Y-%m-%d %H:%M"),
            "end": ttl.strftime("%Y-%m-%d %H:%M"),
            "login": login,
        }
        for pid, ptype, name, cpu, created, ttl, login in projects
    ]
    if result:
        debug(f"Preview of first record: {result[0]}")
    return jsonify(data=result)


@bp.route("/admin/switch_user", methods=["POST"])
@login_required
@grant_access("admin")
def web_switch_user():
    """Switch to a different user account (admin impersonation).

    Returns:
        Redirect to the user's home page.
    """
    username = request.form.get("switch_user")
    if username not in g.user_list:
        flash("Invalid username: '%s'" % username)
        if request.referrer and (request.referrer in g.url_list):
            return redirect(request.referrer)
        else:
            return redirect(url_for("stat.index"))

    user = get_user_record(username)
    login_user(user, True)
    return redirect(url_for("user.user_index"))


@bp.route("/admin/user/<int:uid>/welcome", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_password_welcome(uid):
    """Send a welcome message to a user.

    Args:
        uid: User ID.

    Returns:
        JSON with status message.
    """
    return jsonify(message=user_send_welcome(uid))


@bp.route("/admin/user/<int:uid>/password/set", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_set_password(uid):
    """Set a user's password.

    Args:
        uid: User ID.

    Returns:
        JSON with status message.
    """
    return jsonify(message=user_set_pass(uid))


@bp.route("/admin/user/reset/password/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_reset_password(uid):
    """Reset a user's password.

    Args:
        uid: User ID.

    Returns:
        JSON with status message.
    """
    return jsonify(message=user_reset_pass(uid))


@bp.route("/admin/user/purge/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_purge(uid):
    """Purge a user (not implemented).

    Args:
        uid: User ID.

    Raises:
        ValueError: Always, as this function is not tested.
    """
    raise ValueError("This sensitive code is not tested yet! Sorry!!!")


@bp.route("/admin/user/delete/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_delete(uid):
    """Delete a user.

    Args:
        uid: User ID.

    Returns:
        JSON with status message.
    """
    return jsonify(message=user_delete(uid), data=True)


@bp.route("/admin/user/activate/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_activate(uid):
    """Activate a user (not fully implemented).

    Args:
        uid: User ID.

    Returns:
        JSON with data and message.
    """
    form = ActivateUserForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    result, msg = "Not ready", " Not ready" #user_info_update(form)
    return jsonify(data=result, message=msg)


@bp.route("/admin/user/new/del/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_new_del(pid):
    """Remove a user from a registration record.

    Args:
        pid: Registration ID.

    Returns:
        JSON with updated registration data.
    """
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    if "uid" not in data:
        raise ValueError("UID is required")
    return jsonify(data=registration_user_del(pid, data["uid"]))


@bp.route("/admin/user/new/update", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_new_update():
    """Update a user in a registration record.

    Returns:
        JSON with updated registration data.
    """
    form = NewUserEditForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return jsonify(data=registration_user_update(form))


@bp.route("/admin/user/details/set", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_update():
    """Update a user's details (ACL, projects, info).

    Returns:
        JSON with user details and status message.
    """
    form = UserEditForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    result, msg = user_info_update(form)
    return jsonify(data=result, message=msg)


@bp.route("/admin/user/create", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_create():
    """Create a new user by an admin.

    Returns:
        JSON with status message.
    """
    form = UserEditForm()
    if form.validate_on_submit():
        return jsonify(message=user_create_by_admin(form))
    raise ValueError(form.errors)


@bp.route("/admin/user/details/get/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_details(uid):
    """Get user details.

    Args:
        uid: User ID.

    Returns:
        JSON with user details dictionary.
    """
    user = user_by_id(uid)
    return jsonify(data=user.details())


@bp.route("/admin/user/lastlog", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def admin_user_lastlog():
    """Process ``last`` command output to update user last-seen timestamps.

    Returns:
        200 OK with message string.
    """
    if request.content_length > 1000000:  # 1000000 - 1 Megabyte
        return abort(413)
    data = request.get_data(cache=False, as_text=True)
    last_user(data)
    return "Lastlog user info is updated", 200


@bp.route("/admin/registration/add/user/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_add_user(rid):
    """Add a user to a registration record.

    Args:
        rid: Registration ID.

    Returns:
        Rendered pending HTML.
    """
    form = NewUserForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return registration_user_add(rid, form)


@bp.route("/admin/registration/edit/responsible/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_edit_responsible(rid):
    """Edit the responsible person on a registration record.

    Args:
        rid: Registration ID.

    Returns:
        Rendered pending HTML.
    """
    form = EditResponsibleForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return registration_responsible_edit(rid, form)


@bp.route("/admin/registration/edit/user/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_edit_user(rid):
    """Edit users on a registration record.

    Args:
        rid: Registration ID.

    Returns:
        Rendered pending HTML.
    """
    data = request.form.to_dict()
    indexes = list(set([int(key.split("-")[0]) for key in data.keys()]))
    forms = []
    for i in indexes:
        form = NewUserForm(prefix=str(i))
        if not form.validate_on_submit():
            raise ValueError(form.errors)
        forms.append(form)
    return registration_user_update(rid, forms)


@bp.route("/admin/registration/edit/record/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_edit_record(rid):
    """Edit fields of a registration record.

    Args:
        rid: Registration ID.

    Returns:
        Rendered pending HTML.
    """
    form = RegistrationEditForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return registration_record_edit(rid, form)


@bp.route("/admin/registration/approve/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "tech", "manager")
def admin_registration_approve(pid):
    """Approve technical requirements for a new project.

    Args:
        pid: Register record ID.

    Returns:
        JSON with approval result message.
    """
    return jsonify(message=Pending(pid).approve().result)


@bp.route("/admin/registration/reset/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_reset(pid):
    """Reset a new project creation process.

    Args:
        pid: Register record ID.

    Returns:
        JSON with reset result message.
    """
    return jsonify(data=Pending(pid).reset().result)


@bp.route("/admin/registration/reject/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def admin_registration_reject(pid):
    """Reject a new project request.

    Args:
        pid: Register record ID.

    Returns:
        JSON with rejection result message.
    """
    form = PendingActionForm()
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    return jsonify(data=Pending(pid).reject(form.note.data).result)


@bp.route("/admin/registration/ignore/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_ignore(pid):
    """Ignore a new project request.

    Args:
        pid: Register record ID.

    Returns:
        JSON with result message.
    """
    return jsonify(data=Pending(pid).ignore().result)


@bp.route("/admin/registration/create/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def admin_registration_create(pid):
    """Create a project from a registration request.

    Args:
        pid: Register record ID.

    Returns:
        JSON with creation result message.
    """
    data = request.form.to_dict()
    indexes = list(set([int(key.split("-")[0]) for key in data.keys()]))
    tmp = []
    for i in indexes:
        form = CreateForm(prefix=str(i))
        if not form.validate_on_submit():
            raise ValueError(form.errors)
        tmp.append(process_user_form(form))
    users = list(filter(lambda x: x, tmp))
    return jsonify(message=Pending(pid).create(users).result)


@bp.route("/admin/registration/visa/received/<int:pid>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "tech")
def admin_registration_visa_received(pid):
    """Mark visa as received for a registration.

    Args:
        pid: Register record ID.

    Returns:
        JSON with result message.
    """
    return jsonify(data=Pending(pid).visa_received().result)


@bp.route("/admin/registration/visa/resend/<int:pid>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "tech")
def admin_registration_visa_resend(pid):
    """Resend a visa for a registration.

    Args:
        pid: Register record ID.

    Returns:
        JSON with result message.
    """
    return admin_registration_visa(pid, True)


@bp.route("/admin/registration/visa/<int:pid>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "tech")
def admin_registration_visa(pid, resend=False):
    """Send or skip a visa for a registration.

    Args:
        pid: Register record ID.
        resend: Whether to resend the visa.

    Returns:
        JSON with result message.
    """
    form = VisaPendingForm()
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    if form.exception.data:
        return jsonify(data=Pending(pid).visa_skip().result)
    return jsonify(data=Pending(pid).visa_create(resend).result)


@bp.route("/admin/extension/processed/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def admin_extension_done(pid):
    """Mark an extension request as processed.

    Args:
        pid: Extension ID.

    Returns:
        JSON with result data.
    """
    return jsonify(data=process_extension(pid))


@bp.route("/admin/extension/todo", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def admin_extension_todo():
    """Return pending extension requests.

    Returns:
        JSON with list of pending extensions.
    """
    return jsonify(data=Extensions().pending())


@bp.route("/admin/tasks/edit/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_edit(tid):
    """Edit a task's processed/done/decision fields.

    Args:
        tid: Task ID.

    Returns:
        JSON with updated task dictionary.
    """
    form = TaskEditForm()
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    return jsonify(data=Task(tid).update(form).to_dict(), task=True)


@bp.route("/admin/tasks/ignore/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_ignore(tid):
    """Ignore a task.

    Args:
        tid: Task ID.

    Returns:
        JSON with updated task list.
    """
    task = Task(tid).ignore()
    tasks = TaskManager().list()
    if "admin.html" in request.referrer:
        return jsonify(
            data=tasks,
            info="Task '%s' is ignored" % task.short(),
            task=True,
            html=render_template("modals/admin_show_task.html", data={"tasks": tasks}),
        )
    return jsonify(data=tasks, task=True)


@bp.route("/admin/tasks/reject/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_reject(tid):
    """Reject a task.

    Args:
        tid: Task ID.

    Returns:
        JSON with updated task list.
    """
    data = request.form.to_dict()
    task = Task(tid).reject(data.get("reason", None))
    tasks = TaskManager().list()
    if "admin.html" in request.referrer:
        return jsonify(
            data=tasks,
            info="Task '%s' is rejected" % task.short(),
            task=True,
            html=render_template("modals/admin_show_task.html", data={"tasks": tasks}),
        )
    return jsonify(data=tasks, task=True)


@bp.route("/admin/tasks/accept/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_accept(tid):
    """Accept a task.

    Args:
        tid: Task ID.

    Returns:
        JSON with updated task list.
    """
    task = Task(tid).accept()
    tasks = TaskManager().list()
    if "admin.html" in request.referrer:
        return jsonify(
            data=tasks,
            info="Task '%s' is accepted" % task.short(),
            task=True,
            html=render_template("modals/admin_show_task.html", data={"tasks": tasks}),
        )
    return jsonify(data=tasks, task=True)


@bp.route("/admin/tasks/info/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_info(tid):
    """Render task information.

    Args:
        tid: Task ID.

    Returns:
        Rendered HTML.
    """
    return render_task(Task(tid).task)


@bp.route("/admin/tasks/history", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_history():
    """Return task history.

    Returns:
        JSON with list of task dictionaries.
    """
    return jsonify(data=task_history(), task=True)


@bp.route("/admin/tasks/todo", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def web_admin_tasks_todo():
    """Return tasks ready for execution.

    Returns:
        JSON with list of API-style task dictionaries.
    """
    return jsonify(data=TaskManager().todo(), task=True)


@bp.route("/admin/tasks/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_list():
    """Return unprocessed tasks.

    Returns:
        JSON with list of task dictionaries.
    """
    return jsonify(data=TaskManager().list(), task=True)


@bp.route("/admin/tasks/done/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def admin_tasks_done(tid):
    """Mark a task as done and process its action.

    Args:
        tid: Task ID.

    Returns:
        JSON with task brief.
    """
    result = request.get_json(silent=True)
    if result:
        result = result.get("result", None)
    return jsonify(data=process_task(tid, result).brief(), task=True)


@bp.route("/admin/partition/info", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_partition_info():
    """Return SLURM partition information.

    Returns:
        JSON with partition data.
    """
    return jsonify(data=slurm_partition_info())


@bp.route("/admin/user/info", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_user_info():
    """Return logged-in users on a remote server.

    Expects JSON with ``server`` field.

    Returns:
        JSON with list of user session dictionaries.
    """
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")

    server = str(data["server"]).strip()
    if not server:
        raise ValueError("Server is not defined")
    result, err = ssh_wrapper(
        "PROCPS_USERLEN=32 PROCPS_FROMLEN=90 w -s -h", host=server
    )
    if not result:
        raise ValueError("Error getting partition information: %s" % err)

    users = []
    for user in result:
        output = user.split()
        login = output[0].strip()
        host = output[2].strip()
        cmd = " ".join(output[4:]).strip()

        users.append({"username": login, "from": host, "process": cmd})
    return jsonify(data=users)


@bp.route("/admin/bits/user_info/<string:login>", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def web_admin_bits_user_info(login):
    """Render expanded user info for the registry view.

    Args:
        login: User login.

    Returns:
        Rendered HTML.
    """
    return render_registry(get_user_record(login))


@bp.route("/admin/bits/pending/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def web_admin_bits_pending(rid):
    """Render expanded pending registration view.

    Args:
        rid: Registration ID.

    Returns:
        Rendered HTML.
    """
    return render_pending(Pending(rid).pending)


@bp.route("/admin/pending/list", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def web_admin_pending_list():
    """Return unprocessed registrations.

    Returns:
        JSON with list of registration dictionaries.
    """
    return jsonify(data=unprocessed_dict())


@bp.route("/admin/accounting/<string:name>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "manager", "responsible", "user")
def web_admin_accounting_project(name):
    """Return accounting data for a project.

    Args:
        name: Project name.

    Returns:
        JSON with daily accounting data.
    """
    project = Project.query.filter_by(name=name).one()
    days = (dt.now(tz=tz.utc) - project.resources.created).days
    return jsonify(data=account_days(days, project=project))


@bp.route("/admin/accounting/<int:last>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "manager", "responsible", "user")
def web_admin_accounting_days(last):
    """Return accounting data for the last N days.

    Args:
        last: Number of days.

    Returns:
        JSON with daily accounting data.
    """
    return jsonify(data=account_days(last))


@bp.route("/admin/slurm/nodes/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_slurm_node_list():
    """Return SLURM node status.

    Returns:
        JSON with node status list.
    """
    return jsonify(data=slurm_nodes_status())


@bp.route("/admin/sys/info", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_sys_info():
    """Return system info for all admin servers.

    Returns:
        JSON with server info list.
    """
    servers = current_app.config["ADMIN_SERVER"]
    if not isinstance(servers, list):
        servers = servers.split(",")
    uptime = []
    for server in servers:
        uptime.append(get_server_info(server.strip()))
    return jsonify(data=uptime)


@bp.route("/admin/space/info", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_space_info():
    """Return disk space information.

    Returns:
        JSON with space info list.
    """
    return jsonify(data=space_info())


@bp.route("/users/<login>", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_login_registry(login):
    """Render the registry page for a specific user.

    Args:
        login: User login.

    Returns:
        Rendered registry.html template.
    """
    info = render_registry(get_user_record(login))
    return render_template("registry.html", login=info)


@bp.route("/registry", methods=["GET", "POST"])
@bp.route("/registry.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_registry():
    """Render the user registry page.

    Returns:
        Rendered registry.html template.
    """
    form = AddUserForm()
    return render_template("registry.html", data=all_users(), form=form)


@bp.route("/log", methods=["GET", "POST"])
@bp.route("/log.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_log():
    """Render the event log page.

    Returns:
        Rendered log.html template.
    """
    return render_template("log.html", data=event_log())


@bp.route("/config", methods=["GET", "POST"])
@bp.route("/configuration", methods=["GET", "POST"])
@bp.route("/config.html", methods=["GET", "POST"])
@bp.route("/configuration.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_cfg():
    """Render the configuration view page.

    Returns:
        Rendered config.html template.
    """
    return render_template("config.html", data=show_configuration())


@bp.route("/tasks", methods=["GET", "POST"])
@bp.route("/tasks.html", methods=["GET", "POST"])
@login_required
@grant_access("admin", "manager")
def web_task():
    """Render the task list page.

    Returns:
        Rendered task.html template.
    """
    return render_template("task.html", data=task_history())


@bp.route("/admin", methods=["GET", "POST"])
@bp.route("/admin.html", methods=["GET", "POST"])
@login_required
@grant_access("admin", "manager")
def web_admin():
    """Render the admin dashboard page.

    Returns:
        Rendered admin.html template.
    """
    servers = current_app.config["ADMIN_SERVER"]
    if not isinstance(servers, list):
        servers = servers.split(",")
    result = {"tasks": TaskManager().list(), "servers": servers}
    return render_template("admin.html", data=result)