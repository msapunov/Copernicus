from flask import g, flash, request, redirect, url_for, render_template, jsonify
from flask import current_app
from flask_login import login_required, login_user
from base.pages import ssh_wrapper, send_message, Task
from base.pages.user.magic import get_user_record
from base.pages.admin import bp
from base.pages.admin.magic import remote_project_creation_magic, get_users
from base.pages.admin.magic import get_responsible, get_registration_record
from base.pages.admin.magic import is_user_exists, get_pid_notes, get_uptime
from base.pages.admin.magic import slurm_partition_info, project_creation_magic
from base.pages.admin.magic import project_assign_resources, get_mem, message
from base.pages.admin.magic import accept_message, reject_message, TaskManager
from base.pages.admin.magic import get_ltm, task_action
from base.pages.project.magic import pending_resources, processed_resource
from logging import info, debug


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

    return jsonify(data=Task(tid).done())


"""
@bp.route("/admin/registration/users", methods=["POST"])
@login_required
def web_admin_registration_users():

    print(request.form)
    pid = check_int(request.form.get("pid"))

    register = get_registration_record(pid)
    tmp_responsible = {
        "name": register.responsible_first_name,
        "surname": register.responsible_last_name,
        "email": register.responsible_email
    }
    responsible = is_user_exists(tmp_responsible)
    users = []
    return jsonify(data={"responsible": responsible, "users": users})


@bp.route("/admin/registration/accept", methods=["POST"])
@login_required
def web_admin_registration_accept():
    from base.database.schema import Register, User
    from base import db

    approve = User.query.filter_by(login=login_user).first()
    if not approve:
        raise ValueError("Can't find user %s in database!" % login_user)
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid, note = get_pid_notes(data)
    responsible = get_responsible(data)
    users = {"responsible": responsible, "users": get_users(data)}
    register = Register.query.filter_by(id=pid).first()
    if not register:
        raise ValueError("Project with id %s not found" % pid)
    debug("Perform project creation")
    project = project_creation_magic(register, users, approve)
    db.session.add(project)
    db.session.commit()  # get the id of the record which becomes the project's name
    debug("Updating registration request DB")
    register.accepted = True
    register.processed = True
    register.comment = note
    p_resources = project_assign_resources(register, approve)
    db.session.add(p_resources)
    project_name = project.get_name()
    gid = remote_project_creation_magic(project_name, users)
    project.resources = p_resources
    project.gid = gid
    project.name = project_name
    db.session.commit()
    info("Project has been created successfully")
    return jsonify(data=accept_message(register, note))


@bp.route("/admin/registration/reject", methods=["POST"])
@login_required
def web_admin_registration_reject():
    from base.database.schema import Register
    from base import db

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid, note = get_pid_notes(data)
    register = Register.query.filter_by(id=pid).first()
    if not register:
        raise ValueError("Project with id %s not found" % pid)
    register.accepted = False
    register.processed = True
    register.comment = note
    db.session.commit()
    return jsonify(data=reject_message(register, note))


@bp.route("/admin/message/register", methods=["POST"])
@login_required
def web_admin_message():
    from base.database.schema import Register

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid, note = get_pid_notes(data)
    register = Register.query.filter_by(id=pid).first()
    if not register:
        raise ValueError("Project with id %s not found" % pid)
    return jsonify(data=message(register.responsible_email, note))
"""

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
    return render_template("admin.html", data=result)
