from flask_login import current_user
from code.utils import bytes2human
from code.pages import ssh_wrapper
from datetime import datetime as dt


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


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
        raise ValueError("No active projects found for user '%s'" %
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
        raise ValueError("No project consumption information found")

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
        raise ValueError("No scratch space info found")

    info = result[1]
    name, uid, used, total, files, hard = info.split(",")
    usage = "{0:.1%}".format(float(used) / float(total))
    free = float(total) - float(used)
    return {"usage": usage, "total": total, "used": used, "free": free,
            "used_label": bytes2human(used), "free_label": bytes2human(free)}


def get_jobs(start, end, last=10):
    cmd = ["sacct", "-nPX",
           "--format=JobID,State,Start,Account,JobName,CPUTime,Partition",
           "--start=%s" % start, "--end=%s" % end, "-u",
           current_user.login]
    run = " ".join(cmd)

    result, err = ssh_wrapper(run)

    if not result:
        raise ValueError("No jobs found from %s to %s" % (start, end))
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
    result = jobs[0:last]
    return result


def changes_to_string(c_dict):
    if "entity" in c_dict:
        del c_dict["entity"]
    c_pairs = list(zip(c_dict.keys(), c_dict.values()))
    c_list = list(map(lambda x: "new %s: %s" % (x[0], x[1]), c_pairs))
    return ", ".join(c_list)
