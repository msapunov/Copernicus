from flask_login import current_user
from base.utils import form_error_string
from base.functions import bytes2human
from base.pages import ssh_wrapper, TaskQueue
from base.database.schema import User
from base.classes import UserLog


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


def user_edit(login, form):
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
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
    return UserLog(user).user_update(info=c_dict)
