from flask import g, flash, request, redirect, url_for, render_template, jsonify
from flask import current_app
from flask_login import login_required, login_user, current_user
from base.pages import (
    send_message,
    Task,
    grant_access)
from base.classes import Pending, Extensions
from base.pages.user.magic import get_user_record, user_by_id
from base.pages.admin import bp
from base.pages.admin.magic import (
    render_pending,
    render_registry,
    all_users,
    create_project,
    event_log,
    get_server_info,
    get_ltm,
    TaskManager,
    slurm_partition_info,
    process_task,
    unprocessed,
    user_info_update,
    user_create_by_admin,
    user_reset_pass,
    user_delete,
    registration_user_del,
    registration_user_new,
    registration_user_update,
    registration_info_update,
    get_registration_record,
    space_info,
    reg_reject,
    register_message,
    reg_accept)
from base.functions import slurm_nodes_status, show_configuration, ssh_wrapper
from base.pages.login.form import MessageForm
from base.pages.admin.form import (
    PendingActionForm,
    VisaPendingForm,
    AddUserForm,
    UserEditForm,
    RegistrationEditForm,
    ActivateUserForm,
    NewUserEditForm)
from base.pages.project.magic import process_extension
from base.utils import form_error_string
from base.database.schema import Project


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


@bp.route("/admin/message/register/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_message_register(rid):
    form = MessageForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return jsonify(data=register_message(rid, form))


@bp.route("/admin/message/send", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_message_send():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    logins, title, msg = get_ltm(data)

    emails = []
    for login in logins:
        user = get_user_record(login)
        emails.append(user.email)
    cc = current_user.email
    return jsonify(data=send_message(emails, cc=cc, message=msg, title=title))


@bp.route("/admin/user/password/<int:uid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_password(uid):
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


@bp.route("/admin/user/new/add", methods=["POST"])
@login_required
@grant_access("admin")
def admin_user_new_add():
    form = NewUserEditForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    return jsonify(data=registration_user_new(form))


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


@bp.route("/admin/registration/details/get/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_details_get(rid):
    registration = get_registration_record(rid)
    return jsonify(data=registration.to_dict())


@bp.route("/admin/registration/details/set/<int:rid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_details_set(rid):
    form = RegistrationEditForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    result, msg = registration_info_update(form)
    return jsonify(data=result, message=msg)


@bp.route("/admin/registration/approve/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin", "tech", "manager")
def admin_registration_approve(pid):
    """
    Approve technical requirements for the new project
    :param pid: Int. ID of register record
    :return: String. Message to display
    """
    return jsonify(data=Pending(pid).approve().result)


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
    return jsonify(data=Pending(pid).create().result)


@bp.route("/admin/registration/accept/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def admin_registration_accept(pid):
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    if "note" not in data:
        raise ValueError("Parameter 'note' was not found in the client request")
    return jsonify(data=reg_accept(pid, data["note"]))


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


@bp.route("/admin/tasks/update/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_update(tid):
    data = request.get_json()
    return jsonify(data=Task(tid).update(data).to_dict())


@bp.route("/admin/tasks/ignore/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_ignore(tid):
    Task(tid).ignore()
    return jsonify(data=TaskManager().list())


@bp.route("/admin/tasks/reject/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_reject(tid):
    Task(tid).reject()
    return jsonify(data=TaskManager().list())


@bp.route("/admin/tasks/accept/<int:tid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_accept(tid):
    Task(tid).accept()
    return jsonify(data=TaskManager().list())


@bp.route("/admin/tasks/history", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_tasks_history():
    return jsonify(data=TaskManager().history())


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
    result = request.args.get("result", None)
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
    return jsonify(data=list(map(lambda x: x.to_dict(), unprocessed())))


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
    uptime = []
    for server in servers:
        uptime.append(get_server_info(server))
    return jsonify(data=uptime)


@bp.route("/admin/space/info", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_space_info():
    return jsonify(data=space_info())


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


@bp.route("/admin", methods=["GET", "POST"])
@bp.route("/admin.html", methods=["GET", "POST"])
@login_required
@grant_access("admin", "manager")
def web_admin():
    result = {"tasks": TaskManager().list()}
    return render_template("admin.html", data=result)
