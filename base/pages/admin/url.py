from flask import g, flash, request, redirect, url_for, render_template, jsonify
from flask import current_app
from flask_login import login_required, login_user
from base.pages import ssh_wrapper, send_message, Task
from base.pages.user.magic import get_user_record, user_by_id
from base.pages.admin import bp
from base.pages.admin.magic import get_uptime, get_mem, get_ltm, TaskManager
from base.pages.admin.magic import slurm_partition_info, process_task
from base.pages.admin.magic import reg_ignore, group_users, user_info_update
from base.pages.admin.magic import user_create_by_admin
from base.pages.admin.form import UserEditForm
from base.pages.project.magic import pending_resources, processed_resource


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/admin/switch_user", methods=["POST"])
@login_required
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


@bp.route("/admin/message/send", methods=["POST"])
@login_required
def web_admin_message_send():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    logins, title, msg = get_ltm(data)

    emails = []
    for login in logins:
        user = get_user_record(login)
        emails.append(user.email)
    return jsonify(data=send_message(emails, message=msg, title=title))


@bp.route("/admin/user/details/set", methods=["POST"])
@login_required
def admin_user_update():
    form = UserEditForm()
    if form.validate_on_submit():
        return jsonify(data=user_info_update(form),
                       message="Modifications has been saved to the database")
    raise ValueError(form.errors)


@bp.route("/admin/user/create", methods=["POST"])
@login_required
def admin_user_create():
    form = UserEditForm()
    if form.validate_on_submit():
        return jsonify(message=user_create_by_admin(form))
    raise ValueError(form.errors)


@bp.route("/admin/user/details/get/<int:uid>", methods=["POST"])
@login_required
def admin_user_details(uid):
    user = user_by_id(uid)
    return jsonify(data=user.details())


@bp.route("/admin/registration/ignore/<int:pid>", methods=["POST"])
@login_required
def admin_registration_ignore(pid):
    return jsonify(data=reg_ignore(pid))


@bp.route("/admin/extension/processed/<int:pid>", methods=["POST"])
@login_required
def admin_extension_done(pid):
    return jsonify(data=processed_resource(pid))


@bp.route("/admin/extension/todo", methods=["POST"])
@login_required
def admin_extension_todo():
    return jsonify(data=pending_resources())


@bp.route("/admin/tasks/update/<int:tid>", methods=["POST"])
@login_required
def web_admin_tasks_update(tid):
    data = request.get_json()
    return jsonify(data=Task(tid).update(data).to_dict())


@bp.route("/admin/tasks/ignore/<int:tid>", methods=["POST"])
@login_required
def web_admin_tasks_ignore(tid):
    Task(tid).ignore()
    return jsonify(data=TaskManager().list())


@bp.route("/admin/tasks/reject/<int:tid>", methods=["POST"])
@login_required
def web_admin_tasks_reject(tid):
    Task(tid).reject()
    return jsonify(data=TaskManager().list())


@bp.route("/admin/tasks/accept/<int:tid>", methods=["POST"])
@login_required
def web_admin_tasks_accept(tid):
    Task(tid).accept()
    return jsonify(data=TaskManager().list())


@bp.route("/admin/tasks/history", methods=["POST"])
@login_required
def web_admin_tasks_history():
    return jsonify(data=TaskManager().history())


@bp.route("/admin/tasks/todo", methods=["POST"])
@login_required
def web_admin_tasks_todo():
    return jsonify(data=TaskManager().todo())


@bp.route("/admin/tasks/list", methods=["POST"])
@login_required
def web_admin_tasks_list():
    return jsonify(data=TaskManager().list())


@bp.route("/admin/tasks/done/<int:tid>", methods=["POST"])
@login_required
def admin_tasks_done(tid):
    return jsonify(data=process_task(tid))


@bp.route("/admin/partition/info", methods=["POST"])
@login_required
def web_admin_partition_info():
    return jsonify(data=slurm_partition_info())


@bp.route("/admin/user/info", methods=["POST"])
@login_required
def web_admin_user_info():

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


@bp.route("/admin/sys/info", methods=["POST"])
@login_required
def web_admin_sys_info():
    servers = current_app.config["ADMIN_SERVER"]
    uptime = []
    for server in servers:
        uptime.append({"server": server, "uptime": get_uptime(server),
                       "mem": get_mem(server)})
    return jsonify(data=uptime)


@bp.route("/admin", methods=["GET", "POST"])
@bp.route("/admin.html", methods=["GET", "POST"])
@login_required
def web_admin():
    from base.database.schema import Register

    result = {"partition": slurm_partition_info()}
    reg_list = Register().query.filter(Register.processed == False).all()
    if not reg_list:
        result["extension"] = False
    else:
        result["extension"] = list(map(lambda x: x.to_dict(), reg_list))
    result["tasks"] = TaskManager().list()
    result["users"] = group_users()
    form = UserEditForm()
    return render_template("admin.html", data=result, form = form)
