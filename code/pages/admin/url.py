from flask import g, flash, request, redirect, url_for, render_template, jsonify
from flask import current_app
from flask_login import login_required, login_user
from code.pages.admin import bp
from code.pages.admin.magic import remote_project_creation_magic, get_users
from code.pages.admin.magic import get_responsible
from code.pages import ssh_wrapper, check_str, send_message, check_int
from logging import error, info, debug


def get_uptime(server):
    tmp = {}
    result, err = ssh_wrapper("uptime", host=server)
    if not result:
        error("Error getting 'uptime' information: %s" % err)
        return tmp

    for up in result:
        output = up.split(",")
        for i in output:
            if "users" in i:
                users = i.replace("users", "")
                users = users.strip()
                try:
                    users = int(users)
                except Exception as err:
                    error("Failed to convert to int: %s" % err)
                    continue
                tmp["users"] = users
            if "load average" in i:
                idx = output.index(i)
                i = "|".join(output[idx:])
                load = i.replace("load average: ", "")
                load = load.strip()
                loads = load.split("|")
                tmp["load_1"] = loads[0]
                tmp["load_5"] = loads[1]
                tmp["load_15"] = loads[2]
    return tmp


def get_mem(server):
    tmp = {}
    result, err = ssh_wrapper("free -m", host=server)
    if not result:
        error("Error getting 'free' information: %s" % err)
        return tmp

    for mem in result:
        output = mem.split(",")
        for i in output:
            if "total" in i:
                continue
            if "Mem" in i:
                memory = i.split()
                mem_total = int(memory[1].strip())
                mem_available = int(memory[6].strip())
                mem_used = mem_total - mem_available
                mem_usage = "{0:.1%}".format(float(mem_used) / float(mem_total))
                tmp["mem_total"] = mem_total
                tmp["mem_avail"] = mem_available
                tmp["mem_used"] = mem_used
                tmp["mem_usage"] = mem_usage
            if "Swap" in i:
                swap = i.split()
                swap_total = int(swap[1].strip())
                swap_available = int(swap[3].strip())
                swap_used = swap_total - swap_available
                swap_usage = "{0:.1%}".format(float(swap_used) /
                                              float(swap_total))
                tmp["swap_total"] = swap_total
                tmp["swap_avail"] = swap_available
                tmp["swap_used"] = swap_used
                tmp["swap_usage"] = swap_usage
    return tmp


def slurm_partition_info():
    result, err = ssh_wrapper("sinfo -s")
    if not result:
        raise ValueError("Error getting partition information: %s" % err)

    partition = []
    for record in result:
        if "PARTITION" in record:
            continue
        name, avail, time, nodes, nodelist = record.split()
        name = name.strip()
        nodes = nodes.strip()
        allocated, idle, other, total = nodes.split("/")
        partition.append({"name": name, "allocated": allocated, "idle": idle,
                          "other": other, "total": int(total)})
    return partition


@bp.route("/switch_user", methods=["POST"])
@login_required
def web_switch_user():
    username = request.form.get("switch_user")
    if username not in g.user_list:
        flash("Invalid username: '%s'" % username)
        if request.referrer and (request.referrer in g.url_list):
            return redirect(request.referrer)
        else:
            return redirect(url_for("stat.index"))

    from code.database.schema import User

    user = User.query.filter_by(login=username).first()
    login_user(user, True)
    flash("Username: '%s'" % username)
    return redirect(url_for("user.user_index"))


def accept_message(register, msg):
    to = register.responsible_email
    name = register.responsible_first_name
    surname = register.responsible_last_name
    mid = register.project_id()
    title = "Your project request '%s' has been accepted" % mid
    prefix = "Dear %s %s,\nYour project request '%s' has been accepted by" \
             " scientific committee" % (name, surname, mid)
    if msg:
        msg = prefix + " with following comment:\n" + msg
    else:
        msg = prefix
    return message(to, msg, title)


def reject_message(register, msg):
    to = register.responsible_email
    name = register.responsible_first_name
    surname = register.responsible_last_name
    mid = register.project_id()
    title = "Your project request '%s' has been rejected" % mid
    prefix = "Dear %s %s,\nYour project request '%s' has been rejected with" \
             " following comment:\n\n" % (name, surname, mid)
    msg = prefix + msg
    return message(to, msg, title)


def message(to, msg, title=None):
    by_who = current_app.config["EMAIL_PROJECT"]
    cc = current_app.config["EMAIL_PROJECT"]
    if not title:
        title = "Concerning your project"
    if not send_message(to, by_who, cc, title, msg):
        return "Message was sent to %s successfully" % to


def project_type(register):
    if register.type_a:
        return "a"
    elif register.type_b:
        return "b"
    elif register.type_c:
        return "c"
    else:
        raise ValueError("Failed to determine project's type")


def project_assign_resources(register, approve):
    from code.database.schema import Resources
    resource = Resources(
        approve=approve,
        valid=True,
        cpu=register.cpu,
        type=project_type(register),
        smp=register.smp,
        gpu=register.gpu,
        phi=register.phi
    )
    return resource


def project_creation_magic(register, users, approve):
    from code.database.schema import Project

    project = Project(
        title=register.title,
        description=register.description,
        scientific_fields=register.scientific_fields,
        genci_committee=register.genci_committee,
        numerical_methods=register.numerical_methods,
        computing_resources=register.computing_resources,
        project_management=register.project_management,
        project_motivation=register.project_motivation,
        active=True,
        type=project_type(register),
        approve=approve,
        ref=register,
        privileged=True if project_type is "h" else False,
        responsible=users["responsible"],
        users=users["users"]
    )
    return project


def get_pid_notes(data):
    pid = check_int(data["project"])
    note = check_str(data["note"])
    return pid, note


@bp.route("/admin/registration/accept", methods=["POST"])
@login_required
def web_admin_registration_accept():
    from code.database.schema import Register, User
    from code import db

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
    from code.database.schema import Register
    from code import db

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
    from code.database.schema import Register

    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    pid, note = get_pid_notes(data)
    register = Register.query.filter_by(id=pid).first()
    if not register:
        raise ValueError("Project with id %s not found" % pid)
    return jsonify(data=message(register.responsible_email, note))


@bp.route("/admin/partition/info", methods=["POST"])
@login_required
def web_admin_partition_info():
    return jsonify(data=slurm_partition_info())


@bp.route("/admin/user/info", methods=["POST"])
@login_required
def web_admin_user_info():

    server_raw = request.form.get("server")
    server = check_str(server_raw)
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
    from code.database.schema import Register

    result = {"partition": slurm_partition_info()}
    reg_list = Register().query.filter(Register.processed == False).all()
    if not reg_list:
        result["extension"] = False
    else:
        result["extension"] = list(map(lambda x: x.to_dict(), reg_list))
    return render_template("admin.html", data=result)
