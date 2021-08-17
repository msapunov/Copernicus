from flask_login import current_user
from base.utils import bytes2human, form_error_string
from base.pages import ssh_wrapper, calculate_usage, TaskQueue
from base.database.schema import Project, User
from base.classes import UserLog
from datetime import datetime as dt
from logging import error, debug


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def user_by_id(uid):
    user = User.query.filter_by(id=uid).first()
    if not user:
        raise ValueError("Failed to find user with id '%s'" % uid)
    return user


def get_user_record(login=None):
    if not login:
        login = current_user.login
    user = User.query.filter_by(login=login).first()
    if not user:
        raise ValueError("Failed to find user with login '%s'" % login)
    return user


def get_project_info(every=None):
    if every:
        projects = Project.query.all()
    else:
        pids = current_user.project_ids()
        projects = Project.query.filter(Project.id.in_(pids)).all()
    if not projects:
        if every:
            raise ValueError("No projects found!")
        else:
            raise ValueError("No projects found for user '%s'" %
                             current_user.login)
    info = list(map(lambda x: get_project_consumption(x), projects))
    debug(info)
    return info


def get_project_consumption(project, start=None, end=dt.now()):
    project.private_use = 0
    project.private = 0
    project.consumed_use = 0
    project.consumed = 0
    name = project.get_name()
    if not project.resources:
        error("No resources attached to project %s" % name)
        return project
    if not start:
        start = project.resources.created
    start = start.strftime("%m/%d/%y-%H:%M")
    finish = end.strftime("%m/%d/%y-%H:%M")
    conso = get_project_conso(name, start, finish)
    if not conso:
        error("Failed to get consumption for project %s" % name)
        return project
    login = current_user.login
    if not project.resources.cpu:
        error("No CPU set in project resources for %s" % name)
        return project
    cpu = project.resources.cpu
    if login in conso.keys():
        project.private_use = calculate_usage(conso[login], cpu)
        project.private = conso[login]
    if name in conso.keys():
        project.consumed_use = calculate_usage(conso[name], cpu)
        project.consumed = conso[name]
    return project


def get_project_conso(name, start, finish):
    cmd = ["sreport", "cluster", "AccountUtilizationByUser", "-t", "hours"]
    cmd += ["-nP", "format=Account,Login,Used", "Accounts=%s" % name]
    cmd += ["start=%s" % start, "end=%s" % finish]
    run = " ".join(cmd)
    data, err = ssh_wrapper(run)
    if not data:
        debug("No data received, nothing to return")
        return None
    result = {}
    for item in data:
        item = item.strip()
        items = item.split("|")
        if len(items) != 3:
            continue
        login = items[1]
        conso = items[2]
        if not login:
            result[name] = int(conso)
        else:
            result[login] = int(conso)
    debug("Project '%s' consumption: %s" % (name, result))
    return result


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
           "--start=%s" % start, "--end=%s" % end, "-u", current_user.login,
           "|", "sort", "-n", "-r", "|", "head", "-%s" % last]
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
    return jobs


def changes_to_string(c_dict):
    if "entity" in c_dict:
        del c_dict["entity"]
    c_pairs = list(zip(c_dict.keys(), c_dict.values()))
    c_list = list(map(lambda x: "new %s: %s" % (x[0], x[1]), c_pairs))
    return ", ".join(c_list)


def user_edit(form):
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    login = form.login.data

    user = get_user_record(login)
    old = {"name": user.name, "surname": user.surname, "email": user.email,
           "login": user.login}
    new = {"name": form.prenom.data, "surname": form.surname.data,
           "email": form.email.data, "login": login}

    c_dict = {}
    for key in ["name", "surname", "email", "login"]:
        old_value = old[key].lower()
        new_value = new[key].lower()
        if old_value == new_value:
            continue
        c_dict[key] = new_value

    if not c_dict:
        raise ValueError("No changes in submitted user information found")
    TaskQueue().user(user).user_update(c_dict)
    return UserLog(user).info_update(info=c_dict)
