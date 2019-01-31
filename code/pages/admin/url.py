from flask import g, flash, request, redirect, url_for, render_template, jsonify
from flask import current_app
from flask_login import login_required, login_user
from code.pages.admin import bp
from code.pages import ssh_wrapper, check_str
from logging import debug, error


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
    result = {}
    result["partition"] = slurm_partition_info()
    return render_template("admin.html", data=result)
