"""Business logic for user management: active checks, SSH keys, jobs,
scratch space, and user editing.
"""

from datetime import datetime as dt
from datetime import timezone
from logging import debug

from flask_login import current_user

from base import db
from base.classes import Task, TaskQueue, UserLog
from base.database.schema import Project, User
from base.functions import bytes2human, ssh_check, ssh_wrapper, form_error_string

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def upload_ssh_allowed(leader, user):
    """Check whether a leader can upload an SSH key for a user.

    SSH key upload is only allowed for temporary users, and only by
    their project responsible.

    Args:
        leader: The user attempting the upload.
        user: The target user.

    Returns:
        True if upload is allowed.
    """
    if "TEMPORARY USER" not in user.comment:
        return False  # SSH key upload allowed for temporary users only
    leaders = []
    for project in user.project:
        leaders.append(project.responsible)
    if leader not in leaders:
        return False
    return True


def get_pending_projects():
    """Check for pending project registrations.

    Returns:
        False (placeholder).
    """
    return False


def absent_users_check(logins):
    """Find users registered in the system but absent on the remote server.

    Args:
        logins: List of user logins from the remote server.

    Returns:
        List of user logins absent on the remote server but present in DB.
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
    """Archive users who are not in the provided login list.

    Users whose login is not among the provided logins and who have not
    yet been archived are marked with the current timestamp.

    Args:
        logins: List of active user logins from the remote server.

    Returns:
        List of logins that were archived.
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
    """Activate and restore users who are in the provided login list.

    Users who are inactive or archived are reactivated.

    Args:
        logins: List of active user logins from the remote server.

    Returns:
        List of status messages describing changes made.
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
    """Deactivate users not in the provided login list if they have no projects.

    Args:
        logins: List of active user logins from the remote server.

    Returns:
        List of deactivated user logins.
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


def ssh_key(form):
    """Process an SSH public key upload.

    Validates the key and creates a task for installing it on the
    remote server.

    Args:
        form: KeyForm with ``key`` and ``login`` data.

    Returns:
        Status message string.
    """
    pub = form.key.data
    login = form.login.data
    debug(f"Provided login '{login}' and public key: {pub}")
    user = get_user_record(login)
    ssh_check(pub)
    if user != current_user and upload_ssh_allowed(current_user, user):
        TaskQueue().user(user).key_upload(pub).task.accept()
    else:
        TaskQueue().user(current_user).key_upload(pub).task.accept()
    UserLog(current_user).key_upload(pub)
    return "You will be notified when your public key is installed"


def user_by_id(uid):
    """Find a user by their database ID.

    Args:
        uid: User ID.

    Returns:
        User instance.

    Raises:
        ValueError: If no user with the given ID is found.
    """
    user = User.query.filter_by(id=uid).first()
    if not user:
        raise ValueError("Failed to find user with id '%s'" % uid)
    return user


def get_user_record(login=None):
    """Find a user by login, or return the current user.

    Args:
        login: Optional login string. If None, uses the current user.

    Returns:
        User instance.

    Raises:
        ValueError: If the login is invalid or the user is not found.
    """
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
    """Query the user's scratch space usage on the remote cluster.

    Runs ``beegfs-ctl --getquota`` via SSH.

    Returns:
        Dictionary with usage, total, used, free, and labels.

    Raises:
        ValueError: If no scratch info is found or parsing fails.
    """
    cmd = "beegfs-ctl --getquota --csv --uid %s" % current_user.login
    result, err = ssh_wrapper(cmd)
    if not result:
        raise ValueError("No scratch space info found")

    info = list(filter(lambda x: current_user.login in x, result))
    if not info:
        raise ValueError("Error parsing scratch space info")
    name, uid, used, total, files, hard = info[0].split(",")
    usage = f"{float(used) / float(total):.1%}"
    free = float(total) - float(used)
    return {"usage": usage, "total": total, "used": used, "free": free,
            "used_label": bytes2human(used), "free_label": bytes2human(free)}


def get_jobs(start, end, last=10):
    """Query SLURM job history for the current user.

    Runs ``sacct`` via SSH to get recent jobs.

    Args:
        start: Start date string for the query.
        end: End date string for the query.
        last: Maximum number of jobs to return.

    Returns:
        List of job dictionaries with id, project, state, etc.

    Raises:
        ValueError: If no jobs are found.
    """
    cmd = ["sacct", "-nPX",
           "--format=JobID,State,Start,Account,JobName,CPUTime,Partition",
           "--start=%s" % start, "--end=%s" % end, "-u", current_user.login,
           "|", "sort", "-n", "-r", "|", "head", "-%s" % last]
    #  cmd = [ "slurm_jobs" ] - wrapper command
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
    """Process a user information edit request.

    Compares old and new values and creates a task for updating the
    user's information.

    Args:
        login: User login.
        form: InfoForm with updated data.

    Returns:
        Status message string.
    """
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