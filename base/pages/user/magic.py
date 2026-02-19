from flask import request
from flask_login import current_user
from base import db
from base.utils import form_error_string
from base.functions import bytes2human, ssh_wrapper, ssh_public
from base.pages import TaskQueue
from base.database.schema import User, Project, Register
from base.classes import UserLog, Task
from tempfile import mkstemp
from os import path, remove
from logging import debug, error
from datetime import datetime as dt, timezone


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def upload_ssh_allowed(leader, user):
    if "TEMPORARY USER" not in user.comment:
        return False  # SSH key upload allowed for temporary users only
    leaders = []
    for project in user.project:
        leaders.append(project.responsible)
    if leader not in leaders:
        return False
    return True

def get_pending_projects():
    return False

def absent_users_check(logins):
    """

    :param logins: List of users on remote server
    :return: List. List of users which is registered in the system but absent
    on remote server
    """
    users = (
        User.query
        .filter(User.archived.is_(None))
        .filter(User.project.any(Project.active.is_(True)))
        .all()
    )
    debug(f"remote users: {len(logins)}")
    debug(f"users: {len(users)}")
    registered = {u.login for u in users}
    return list(registered - set(logins))


def archived_users_check(logins):
    """
    Archives users who are not in the provided login list and archived
    field is empty in the database.
    Returns:
    str: Summary of the archived users.
    """
    # Get all users who are not in the logins list and are not archived.
    # Lock the selected rows to prevent concurrent updates.
    result = []
    users = (
        User.query.filter(User.login.not_in(logins))
        .filter(User.archived.is_(None))
        .with_for_update()
        .all()
    )
    if not users:
        return result
    now = dt.now().replace(tzinfo=timezone.utc)
    debug(f"Number of users to archive: {len(users)}")
    for user in users:
        user.archived = now
        UserLog(user).archived()
        result.append(user.login)
        debug(f"{user.login} archived")
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Error during user archive: {e}")
    return result


def working_users_check(logins):
    """
    Activates and restore users who are in the provided login list if they are
    inactive or archived.
    Returns:
    str: Summary of the deactivated users.
    """
    active_users = User.query.filter(User.login.in_(logins))
    result = []
    for active_user in active_users:
        if not active_user.project:
            continue
        if not active_user.active:
            active_user.active = True
            UserLog(active_user).activated()
            result.append(f"{active_user.login} is activated")
            debug(f"Deactivated user {active_user.login} is activated")
        if active_user.archived:
            active_user.archived = None
            UserLog(active_user).restored()
            result.append(f"{active_user.login} is restored")
            debug(f"Archived user {active_user.login} is restored")
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Error during commiting changes: {e}")
    return result


def inactive_users_check(logins):
    """
    Deactivates users who are not in the provided login list if they are active,
     and not linked to a project.
    Returns:
    str: Summary of the deactivated users.
    """
    result = []
    users = (
        User.query.filter(User.login.not_in(logins))
        .filter(User.active.is_(True))
        .filter(~User.project.any())
        .with_for_update()
        .all()
    )
    if not users:
        return result
    debug(f"Number of users to deactivate: {len(users)}")
    for user in users:
        user.active = False
        UserLog(user).deactivated()
        result.append(user.login)
        debug(f"{user.login} deactivated")
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Error during user deactivation: {e}")
    return result


def sanitize_key(key):
    try:
        parts = key.split(" ")
    except:
        return key
    algo = parts[0]
    host = parts[-1]
    key = "".join(parts[1:-1]).replace(" ", "")
    return "%s %s %s" % (algo, key, host)


def ssh_check(key_text):
    fd, key_path = mkstemp(text=True)
    with open(key_path, "w") as writer:
        writer.write(key_text)
    stdout, stderr = ssh_public(key_path)
    if path.exists(key_path):
        remove(key_path)
    debug(stdout)
    if stderr:
        return False
    return True


def ssh_key(form):
    key = form.key.data
    debug("Provided key: '%s'" % key)
    clean = key.strip()
    sane = sanitize_key(key)
    for k in [key, sane, clean]:
        if not ssh_check(k):
            continue
        task = TaskQueue().user(current_user).key_upload(k).task
        Task(task).accept()
        UserLog(current_user).key_upload(k)
        return "You will be notified when your public key is installed"
    raise ValueError("Provided public key failed to pass ssh-keygen check. " 
                     "Please make sure that you've inserted the content of "
                     "the public key file which should looks like this key "
                     "for example: \n521 SHA256:dm7lPKaRcwGfa66ZFQ3LSD70BSPOyX1"
                     "UWZk key_name (ECDSA)")


def user_by_id(uid):
    user = User.query.filter_by(id=uid).first()
    if not user:
        raise ValueError("Failed to find user with id '%s'" % uid)
    return user


def get_user_record(login=None):
    if not login:
        login = current_user.login
    if len(login) < 1:
        raise ValueError("Username '%s' is too short!" % login)
    if len(login) > 128:
        raise ValueError("Username '%s' is too long!" % login)
    if not login.isalnum():
        raise ValueError("Username '%s' consists not only from letters" % login)
    user = User.query.filter_by(login=login).first()
    if not user:
        raise ValueError("Failed to find user with login '%s'" % login)
    return user


def get_scratch():
    cmd = "beegfs-ctl --getquota --csv --uid %s" % current_user.login
    result, err = ssh_wrapper(cmd)
    if not result:
        raise ValueError("No scratch space info found")

    info = list(filter(lambda x: current_user.login in x, result))
    if not info:
        raise ValueError("Error parsing scratch space info")
    name, uid, used, total, files, hard = info[0].split(",")
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
    task = TaskQueue().user(user).user_update(c_dict).task
    if "admin" in current_user.permissions():
        Task(task).accept()
        user_log = UserLog(user)
        user_log.senf = False
        user_log.user_update(info=c_dict)
        return "Task ID %s Has been created" % task.id
    return UserLog(user).user_update(info=c_dict)
