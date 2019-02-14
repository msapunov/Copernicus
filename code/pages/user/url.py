from flask import render_template, flash, request, jsonify
from flask.json import dumps
from flask_login import login_required, current_user
from code.pages import ssh_wrapper, check_str, send_message
from code.pages.user import bp
from code.utils import bytes2human, accounting_start
from datetime import datetime as dt
from logging import debug


@bp.route("/user/edit/info", methods=["POST"])
@login_required
def user_edit_info():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")

    user = get_user_record(data["login"])
    old = {"name": user.name, "surname": user.surname, "email": user.email,
           "login": user.login}

    c_dict = {}
    for key in ["name", "surname", "email", "login"]:
        old_value = old[key].lower()
        new_value = check_str(data[key]).lower()
        if old_value == new_value:
            continue
        c_dict[key] = new_value

    if not c_dict:
        return jsonify(data="No changes in user's information found")

    c_dict["entity"] = "user"
    changes = dumps(c_dict)

    from code.pages import TaskQueue
    TaskQueue().user_change(changes)
    return jsonify(data="You request for user information change has been"
                        " registered")


@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
@bp.route("/user.html", methods=["GET"])
@login_required
def user_index():
    start = accounting_start()
    end = dt.now().strftime("%m/%d/%y-%H:%M")
    user_record = get_user_record()
    user = {"full": user_record.full_name(),
            "name": user_record.name,
            "surname": user_record.surname,
            "email": user_record.email,
            "login": user_record.login}
    jobs = get_jobs(start, end)
    scratch = get_scratch()
    projects = get_project_info(start, end)
    debug(projects)
    return render_template("user.html", data={"user": user,
                                              "jobs": jobs,
                                              "scratch": scratch,
                                              "projects": projects})


def changes_to_string(c_dict):
    if "entity" in c_dict:
        del c_dict["entity"]
    c_pairs = list(zip(c_dict.keys(), c_dict.values()))
    c_list = list(map(lambda x: "new %s: %s" % (x[0], x[1]), c_pairs))
    return ", ".join(c_list)


def get_user_record(login=None):
    from code.database.schema import User

    if not login:
        login = current_user.login
    user = User.query.filter_by(login=login).first()
    if not user:
        raise ValueError("Failed to find user with login '%s'" % login)
    return user


def get_project_info(start, end):

    from code.database.schema import Project

    p_ids = current_user.project_ids()
    tmp = {}
    for pid in p_ids:
        project = Project().query.filter_by(id=pid).first()
        if not project.active:
            continue
        name = project.get_name()
        if name not in tmp:
            tmp[name] = {}
        tmp[name]["max"] = project.resources.cpu
        tmp[name]["start"] = project.created.strftime("%Y-%m-%d")
        project_end = dt.strptime(end, "%m/%d/%y-%H:%M").strftime("%Y-%m-%d")
        tmp[name]["end"] = project_end

    if not tmp:
        return flash("No active projects found for user '%s'" %
                     current_user.login)

    projects = get_project_consumption(tmp, start, end)
    if not projects:
        return []
    result = []
    for key in projects.keys():
        projects[key]["name"] = key
        if ("consumed" not in projects[key])or("private" not in projects[key]):
            continue
        total = projects[key]["max"]
        if total > 0:
            for i in ["consumed", "private"]:
                val = projects[key][i]
                tmp_usage = "{0:.1%}".format(float(val) / float(total))
                projects[key]["%s_use" % i] = float(tmp_usage.replace("%", ""))
        else:
            projects[key]["consumed_use"] = 0
            projects[key]["private_use"] = 0
        debug(projects[key])
        result.append(projects[key])
    return result


def get_project_consumption(projects, start, end):
    name = ",".join(projects.keys())
    cmd = ["sreport", "cluster", "AccountUtilizationByUser", "-t", "hours"]
    cmd += ["-nP", "format=Account,Login,Used", "Accounts=%s" % name]
    cmd += ["start=%s" % start, "end=%s" % end]
    run = " ".join(cmd)
    result, err = ssh_wrapper(run)
    if not result:
        return flash("No project consumption information found")

    login = current_user.login
    for item in result:
        item = item.strip()
        project, user, conso = item.split("|")
        if "private" not in projects[project]:
            projects[project]["private"] = 0
        if not user:
            projects[project]["consumed"] = int(conso)
            continue
        if user == login:
            projects[project]["private"] = int(conso)
            continue
    return projects


def get_scratch():
    cmd = "beegfs-ctl --getquota --csv --uid %s" % current_user.login
    result, err = ssh_wrapper(cmd)
    if not result:
        return flash("No scratch space info found")

    info = result[1]
    name, uid, used, total, files, hard = info.split(",")
    usage = "{0:.1%}".format(float(used) / float(total))
    free = float(total) - float(used)
    return {"usage": usage, "total": total, "used": used, "free": free,
            "used_label": bytes2human(used), "free_label": bytes2human(free)}


def get_jobs(start, end):
    cmd = ["sacct", "-nPX",
           "--format=JobID,State,Start,Account,JobName,CPUTime,Partition",
           "--start=%s" % start, "--end=%s" % end, "-u",
           current_user.login]
    run = " ".join(cmd)

    result, err = ssh_wrapper(run)

    if not result:
        return flash("No jobs found")
    jobs = []
    for job in result:
        tmp = {}
        job = job.strip().split("|")
        tmp["id"] = job[0]
        tmp["project"] = job[3]
        tmp["state"] = job[1]
        tmp["partition"] = job[6]
        tmp["date"] = job[2]
        tmp["name"] = job[4]
        tmp["duration"] = job[5]
        jobs.append(tmp)
    jobs = sorted(jobs, key=lambda x: x["id"], reverse=True)
    result = jobs[0:10]
    return result
