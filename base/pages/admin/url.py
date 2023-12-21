from flask import g, flash, request, redirect, url_for, render_template, jsonify
from flask import abort
from flask import current_app
from flask_login import login_required, login_user
from base.pages import Task, grant_access
from base.classes import Pending, Extensions
from base.pages.user.magic import get_user_record, user_by_id
from base.pages.admin import bp
from base.pages.admin.magic import (
    process_user_form,
    account_days,
    last_user,
    render_task,
    render_pending,
    render_registry,
    all_users,
    event_log,
    get_server_info,
    get_ltm,
    TaskManager,
    slurm_partition_info,
    process_task,
    unprocessed_dict,
    user_info_update,
    user_create_by_admin,
    user_set_pass,
    user_send_welcome,
    user_reset_pass,
    user_delete,
    registration_user_del,
    registration_user_add,
    registration_user_update,
    registration_responsible_edit,
    registration_record_edit,
    space_info,
    task_history)
from base.functions import slurm_nodes_status, show_configuration, ssh_wrapper
from base.pages.admin.form import (
    CreateForm,
    PendingActionForm,
    VisaPendingForm,
    AddUserForm,
    UserEditForm,
    RegistrationEditForm,
    ActivateUserForm,
    EditResponsibleForm,
    NewUserForm,
    TaskEditForm,
    NewUserEditForm)
from base.pages.project.magic import process_extension
from base.utils import form_error_string
from base.database.schema import Project
from datetime import datetime as dt, timezone as tz


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/test", methods=["GET"])
@bp.route("/test.html", methods=["GET"])
@login_required
@grant_access("admin")
def web_test():
    return render_template("test.html", data=Project.query.all())


@bp.route("/admin/switch_user", methods=["POST"])
@login_required
@grant_access("admin")
def web_switch_user():
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
    return jsonify(message=user_send_welcome(uid))


@bp.route("/admin/user/<int:uid>/password/set", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_set_password(uid):
    return jsonify(message=user_set_pass(uid))


@bp.route("/admin/user/reset/password/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_reset_password(uid):
    return jsonify(message=user_reset_pass(uid))


@bp.route("/admin/user/purge/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_purge(uid):
    raise ValueError("This sensitive code is not tested yet! Sorry!!!")


@bp.route("/admin/user/delete/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_delete(uid):
    return jsonify(message=user_delete(uid), data=True)


@bp.route("/admin/user/activate/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_activate(uid):
    form = ActivateUserForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    result, msg = "Not ready", " Not ready" #user_info_update(form)
    return jsonify(data=result, message=msg)


@bp.route("/admin/user/new/del/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_new_del(pid):
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
    form = NewUserEditForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return jsonify(data=registration_user_update(form))


@bp.route("/admin/user/details/set", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_update():
    """
    Update user's information
    :return: jsonified user_info_update_new and messages
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
    form = UserEditForm()
    if form.validate_on_submit():
        return jsonify(message=user_create_by_admin(form))
    raise ValueError(form.errors)


@bp.route("/admin/user/details/get/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_details(uid):
    user = user_by_id(uid)
    return jsonify(data=user.details())


@bp.route("/admin/user/lastlog", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def admin_user_lastlog():
    if request.content_length > 1000000:  # 1000000 - 1 Megabyte
        return abort(413)
    data = request.get_data(cache=False, as_text=True)
    last_user(data)
    return "Lastlog user info is updated", 200


@bp.route("/admin/registration/add/user/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_add_user(rid):
    form = NewUserForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return registration_user_add(rid, form)


@bp.route("/admin/registration/edit/responsible/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_edit_responsible(rid):
    form = EditResponsibleForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return registration_responsible_edit(rid, form)


@bp.route("/admin/registration/edit/user/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_edit_user(rid):
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
    form = RegistrationEditForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return registration_record_edit(rid, form)


@bp.route("/admin/registration/approve/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "tech", "manager")
def admin_registration_approve(pid):
    """
    Approve technical requirements for the new project
    :param pid: Int. ID of register record
    :return: String. Message to display
    """
    return jsonify(message=Pending(pid).approve().result)


@bp.route("/admin/registration/reset/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_reset(pid):
    """
    Reset new project creation process. No mail will be send
    :param pid: Int. ID of register record
    :return: String. Message to display
    """
    return jsonify(data=Pending(pid).reset().result)


@bp.route("/admin/registration/reject/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def admin_registration_reject(pid):
    """
    Reject new project request because request is malformed or not correct.
    :param pid: Int. ID of register record
    :return: String. Message to display
    """
    form = PendingActionForm()
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    return jsonify(data=Pending(pid).reject(form.note.data).result)


@bp.route("/admin/registration/ignore/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_ignore(pid):
    """
    Ignoring request for new project. No mail will be send
    :param pid: Int. ID of register record
    :return: String. Message to display
    """
    return jsonify(data=Pending(pid).ignore().result)


@bp.route("/admin/registration/create/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def admin_registration_create(pid):
    data = request.form.to_dict()
    indexes = list(set([int(key.split("-")[0]) for key in data.keys()]))
    users = []
    for i in indexes:
        form = CreateForm(prefix=str(i))
        if not form.validate_on_submit():
            raise ValueError(form.errors)
        users.append(process_user_form(form))
    return jsonify(message=Pending(pid).create(users).result)


@bp.route("/admin/registration/visa/received/<int:pid>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "tech")
def admin_registration_visa_received(pid):
    """
    Set status for new project to "visa received".
    :param pid: Int. ID of register record
    :return: String. Message to display.
    """
    return jsonify(data=Pending(pid).visa_received().result)


@bp.route("/admin/registration/visa/resend/<int:pid>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "tech")
def admin_registration_visa_resend(pid):
    """
    Sometimes visa should be sent once again
    :param pid: Int. ID of register record
    :return: String. Message to display. Result of admin_registration_visa()
    """
    return admin_registration_visa(pid, True)


@bp.route("/admin/registration/visa/<int:pid>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "tech")
def admin_registration_visa(pid, resend=False):
    """
    Sending visa for new project
    :param pid: Int. ID of register record
    :param resend: Boolean. Whether or not visa should be resent
    :return: String. Message to display
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
    return jsonify(data=process_extension(pid))


@bp.route("/admin/extension/todo", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def admin_extension_todo():
    return jsonify(data=Extensions().pending())


@bp.route("/admin/tasks/edit/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_edit(tid):
    form = TaskEditForm()
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    return jsonify(data=Task(tid).update(form).to_dict())


@bp.route("/admin/tasks/ignore/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_ignore(tid):
    task = Task(tid).ignore()
    tasks = TaskManager().list()
    if "admin.html" in request.referrer:
        return jsonify(data=tasks, info="Task '%s' is ignored" % task.short(),
                       html=render_template(
            "modals/admin_show_task.html", data={"tasks": tasks}))
    return jsonify(data=tasks)


@bp.route("/admin/tasks/reject/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_reject(tid):
    task = Task(tid).reject()
    tasks = TaskManager().list()
    if "admin.html" in request.referrer:
        return jsonify(data=tasks, info="Task '%s' is rejected" % task.short(),
                       html=render_template(
            "modals/admin_show_task.html", data={"tasks": tasks}))
    return jsonify(data=tasks)


@bp.route("/admin/tasks/accept/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_accept(tid):
    task = Task(tid).accept()
    tasks = TaskManager().list()
    if "admin.html" in request.referrer:
        return jsonify(data=tasks, info="Task '%s' is accepted" % task.short(),
                       html=render_template(
            "modals/admin_show_task.html", data={"tasks": tasks}))
    return jsonify(data=tasks)


@bp.route("/admin/tasks/info/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_info(tid):
    return render_task(Task(tid).task)


@bp.route("/admin/tasks/history", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_history():
    return jsonify(data=task_history())


@bp.route("/admin/tasks/todo", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def web_admin_tasks_todo():
    return jsonify(data=TaskManager().todo())


@bp.route("/admin/tasks/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_list():
    return jsonify(data=TaskManager().list())


@bp.route("/admin/tasks/done/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def admin_tasks_done(tid):
    result = request.get_json(silent=True)
    if result:
        result = result.get("result", None)
    return jsonify(data=process_task(tid, result).brief())


@bp.route("/admin/partition/info", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_partition_info():
    return jsonify(data=slurm_partition_info())


@bp.route("/admin/user/info", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_user_info():
    """
    Executes linux w command on a remote server and parse the result to be
    returned as JSON
    :return: List of dictionaries with user information like:
    {"username": login, "from": host, "process": cmd}
    """

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")

    server = str(data["server"]).strip()
    if not server:
        raise ValueError("Server is not defined")
    result, err = ssh_wrapper("PROCPS_USERLEN=32 PROCPS_FROMLEN=90 w -s -h",
                              host=server)
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
    return render_registry(get_user_record(login))


@bp.route("/admin/bits/pending/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def web_admin_bits_pending(rid):
    return render_pending(Pending(rid).pending)


@bp.route("/admin/pending/list", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def web_admin_pending_list():
    return jsonify(data=unprocessed_dict())


@bp.route("/admin/accounting/<string:name>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "manager")
def web_admin_accounting_project(name):
    project = Project.query.filter_by(name=name).one()
    days = (dt.now(tz=tz.utc) - project.resources.created).days
    return jsonify(data=account_days(days, project=project))


@bp.route("/admin/accounting/<int:last>", methods=["POST", "GET"])
@login_required
@grant_access("admin", "manager")
def web_admin_accounting_days(last):
    return jsonify(data=account_days(last))


@bp.route("/admin/slurm/nodes/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_slurm_node_list():
    return jsonify(data=slurm_nodes_status())


@bp.route("/admin/sys/info", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_sys_info():
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
    return jsonify(data=space_info())


@bp.route("/users/<login>", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_login_registry(login):
    info = render_registry(get_user_record(login))
    return render_template("registry.html", login=info)


@bp.route("/registry", methods=["GET", "POST"])
@bp.route("/registry.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_registry():
    form = AddUserForm()
    return render_template("registry.html", data=all_users(), form=form)


@bp.route("/log", methods=["GET", "POST"])
@bp.route("/log.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_log():
    return render_template("log.html", data=event_log())


@bp.route("/config", methods=["GET", "POST"])
@bp.route("/configuration", methods=["GET", "POST"])
@bp.route("/config.html", methods=["GET", "POST"])
@bp.route("/configuration.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_cfg():
    return render_template("config.html", data=show_configuration())


@bp.route("/tasks", methods=["GET", "POST"])
@bp.route("/tasks.html", methods=["GET", "POST"])
@login_required
@grant_access("admin", "manager")
def web_task():
    return render_template("task.html", data=task_history())


@bp.route("/admin", methods=["GET", "POST"])
@bp.route("/admin.html", methods=["GET", "POST"])
@login_required
@grant_access("admin", "manager")
def web_admin():
    result = {"tasks": TaskManager().list()}
    return render_template("admin.html", data=result)
