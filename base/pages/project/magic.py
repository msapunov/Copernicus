from datetime import datetime as dt, timezone
from logging import error, debug, warning
from pathlib import Path

from flask import current_app, render_template, g
from flask_login import current_user
from owncloud import Client as OwnClient
from pdfkit import from_string

from base import db
from base.classes import TmpUser, ProjectLog, Task
from base.functions import project_config, generate_password, calculate_ttl
from base.database.schema import Extend, File, Project, Tasks, User
from base.pages import calculate_usage, generate_login, TaskQueue
from base.pages import ssh_wrapper
from base.pages.user.magic import user_by_id
from base.pages.board.magic import create_resource
from base.utils import save_file, get_tmpdir, form_error_string

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def project_attach_user(name, form):
    """
    Function which attach an existing user to a given project
    :param name: String. Name of the project to which user should be attached
    :param form: Instance of WTForm
    :return: Instance of a project to which a new user has to be attached and an
    instance of User class
    """
    project = check_responsible(name)
    uid = form.login.data
    user = User.query.filter(User.id == uid).first()
    if not user:
        raise ValueError("Failed to find user with ID '%s' in database" % uid)
    if user in project.users:
        raise ValueError("User %s has been already attached to project %s"
                         % (user.full(), project.get_name()))
    task = TaskQueue().project(project).user_assign(user).task
    if "admin" in current_user.permissions():
        Task(task).accept()
    return ProjectLog(project).user_assign(task)


def project_create_user(name, form):
    """
    Function which creates a temporary user based on provide info and add a
    create user task in the task queue
    :param name: String. Name of the project where a use should be created
    :param form: Instance of WTForm
    :return: Instance of a project to which a new user has to be attached and an
    instance of TmpUser class
    """
    project = check_responsible(name)
    prenom = form.prenom.data.strip().lower()
    surname = form.surname.data.strip().lower()
    email = form.email.data.strip().lower()
    if User.query.filter(User.email == email).first():
        raise ValueError("User with e-mail %s has been registered already"
                         % email)
    user = TmpUser()
    user.login = generate_login(prenom, surname)
    user.password = generate_password(16)
    user.name = prenom
    user.surname = surname
    user.email = email
    task = TaskQueue().project(project).user_create(user).task
    if current_user.login and "admin" in current_user.permissions():
        Task(task).accept()
    return ProjectLog(project).user_create(task)


def upload_file_cloud(path, remote=None):
    """
    Function which uploads a file to OwnCloud instance
    :param path: String. Path to file to upload.
    :param remote: String. Name of the remote directory to store files in.
    :return: Boolean. Return result of put_file() function call for OwnCloud
             instance. Result of this function call is boolean
    """
    url = current_app.config.get("OWN_CLOUD_URL", None)
    if not url:
        error("No url to the cloud given")
        return False
    oc = OwnClient(url)
    login = current_app.config.get("OWN_CLOUD_LOGIN", None)
    password = current_app.config.get("OWN_CLOUD_PASSWORD", None)
    try:
        oc.login(login, password)
    except Exception as err:
        error("Failed to connect to the cloud: %s" % err)
        return False
    po = Path(path)
    if not po.exists() or not po.is_file():
        error("Can't upload a file to a cloud. '%s' doesn't exists or not "
              "a file" % path)
        return False
    if not remote:
        remote_dir = current_app.config.get("ACTIVITY_DIR", "/")
        if remote_dir[-1] is not "/":
            remote_dir += "/"
        remote = remote_dir + po.name
    debug("Uploading file %s to %s" % (path, remote))
    return oc.put_file(remote, path)


def check_responsible(name):
    """
    Check if current user is responsible of a project given in argument
    :param name: String. Name of a project
    :return: Object. Object of a project under given project name
    """
    project = get_project_by_name(name)
    if current_user != project.get_responsible():
        raise ValueError("User %s is not register as the responsible person "
                         "for the project %s" % (current_user.login, name))
    return project


def assign_responsible(name, form):
    """
    Assigning a responsible to a project. Admins do that without check with any
    users. For non admins several conditions has to be satisfied:
    1) New responsible has to be different user.
    2) New responsible should be one of project's users
    :param name: String. Name of the project
    :param form: WTForm. Form with data
    :return: object. Instance of ProjectLog object
    """
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    uid = form.login.data
    send = form.send.data
    user = user_by_id(uid)
    if "admin" in current_user.permissions():
        project = get_project_by_name(name)
    else:
        project = check_responsible(name)
    if user == project.responsible:
        raise ValueError("User %s is already responsible for the project %s" %
                         (user.full_name(), project.get_name()))
    if "admin" in current_user.permissions():
        task = TaskQueue().project(project).responsible_assign(user).task
        Task(task).accept()
        return ProjectLog(project).send_message(send).responsible_assign(task)
    if user not in project.users:
        raise ValueError("New responsible has to be one of the project users")
    task = TaskQueue().project(project).responsible_assign(user).task
    return ProjectLog(project).responsible_assign(task)


def get_activity_files(name):
    check_responsible(name)
    temp_dir = get_tmpdir(current_app)
    debug("Using temporary directory to store files: %s" % temp_dir)
    pattern = "*%s*" % name
    debug("Pattern %s to get associated files for %s" % (pattern, name))
    already = list(Path(temp_dir).glob(pattern))
    debug("List of existing files: %s" % already)
    return already


def save_activity(req):
    limit = current_app.config.get("ACTIVITY_REPORT_LIMIT", 3)
    project = req.form.get("project", None)
    if not project:
        raise ValueError("No project name provided!")
    check_responsible(project)
    files = get_activity_files(project)
    if len(files) >= limit:
        raise ValueError("You have already uploaded %s or more files" % limit)
    ts = str(dt.now().replace(microsecond=0).isoformat("_")).replace(":", "-")
    image_name = "%s_activity_report_%s" % (project, ts)
    name = save_file(req, get_tmpdir(current_app), image_name)
    debug("Returning result: %s" % name)
    return name


def save_report(project):
    project_name = project.get_name()
    html = render_template("report.html", data=project)
    ts = str(dt.now().replace(microsecond=0).isoformat("_")).replace(":", "-")
    name = "%s_activity_report_%s.pdf" % (project_name, ts)
    path = str(Path(get_tmpdir(current_app), name))
    debug("The resulting PDF will be saved to: %s" % path)
    pdf = from_string(html, path)
    debug("If PDF converted successfully: %s" % pdf)
    if not pdf:
        raise ValueError("")

    if current_app.config.get("ACTIVITY_UPLOAD", False):
        debug("Uploading report to a cloud storage")
        if current_app.config.get("ACTIVITY_UPLOAD_IMG", False):
            for i in ["image_1", "image_2", "image_3"]:
                tmp = getattr(project, i, None)
                upload_file_cloud(tmp) if tmp else False
        upload_file_cloud(path)

    report = File(path=path,
                  size=Path(path).stat().st_size,
                  comment="Activity report",
                  user=current_user,
                  project=project,
                  created=dt.now(timezone.utc))
    db.session.commit()
    debug("Activity report saved to the file %s" % report.path)
    return report


def report_activity(name, form):
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    project = check_responsible(name)
    result = get_project_consumption(project)
    if not result:
        raise ValueError("No information found for project '%s' Failure during "
                         "report generation" % name)

    result.report = form.report.data
    result.doi = form.doi.data
    result.training = form.training.data
    result.hiring = form.hiring.data
    result.generated = dt.strftime(dt.now(timezone.utc), "%c")
    tmp = get_tmpdir(current_app)
    for i in ["image_1", "image_2", "image_3"]:
        path = Path(tmp, form[i].data)
        if path.exists() and path.is_file():
            setattr(result, i, str(path.resolve()))
        else:
            error("Path for image doesn't exists: %s" % path.resolve())
    debug(result)
    return save_report(result)


def remove_activity(name, file_name):
    check_responsible(name)
    temp_dir = get_tmpdir(current_app)
    path = Path(temp_dir) / file_name
    if not path.exists():
        debug("Path doesn't exists: %s" % str(path))
        return True
    if path.is_file():
        path.unlink()
        debug("File deleted: %s" % file_name)
        return True
    if path.is_dir():
        error("Path %s is a directory and can't be removed" % str(path))
        return False


def clean_activity(name):
    debug("Cleaning activity files for project %s" % name)
    project = check_responsible(name)
    files = get_activity_files(project.get_name())
    if len(files) < 1:
        return True
    for x in files:
        x.unlink()
        debug("File deleted: %s" % str(x))
    return True


def renew_project(pid, ext, date):
    ext.project.resources.valid = False
    ext.project.resources = create_resource(ext.project, ext.hours)
    msg = "Created based on renewal request ID %s on %s" % (pid, date)
    ext.project.resources.comment = msg
    return ProjectLog(ext.project).renewed(ext)


def extend_project(pid, ext, date):
    ext.project.resources.ttl = calculate_ttl(ext.project)
    ext.project.resources.cpu += ext.hours
    ext.project.resources.valid = True
    msg = "CPU value has been extended to %s hours on %s based upon "\
          "extension request ID %s" % (ext.hours, date, pid)
    if ext.project.resources.comment:
        ext.project.resources.comment = ext.project.resources.comment \
                                        + "\n" + msg
    else:
        ext.project.resources.comment = msg
    return ProjectLog(ext.project).extended(ext)


def transform_project(ext, date):
    ext.project.type = ext.transform
    ext.project.name = "%s%s" % (ext.transform, str(ext.project.id).zfill(3))
    ext.project.resources.valid = False
    ext.project.resources = create_resource(ext.project, ext.hours)
    msg = "Created based on transformation request ID %s on %s" % (ext.id, date)
    ext.project.resources.comment = msg
    return ProjectLog(ext.project).transformed(ext)


def process_extension(eid):
    ext = Extend.query.filter_by(id=eid).first()
    if not ext:
        raise ValueError("Failed to find extension record with id '%s'" % eid)
    ext.done = True
    date = dt.now().replace(microsecond=0).isoformat(" ")
    never_extend = current_app.config.get("NO_EXTENSION_TYPE", [])
    never_renew = current_app.config.get("NO_RENEWAL_TYPE", [])
    if ext.transform.strip() != "":
        return transform_project(ext, date)
    if ext.project.type in never_extend:
        return renew_project(eid, ext, date)
    if ext.project.type in never_renew:
        return extend_project(eid, ext, date)
    if not ext.extend:
        return renew_project(eid, ext, date)
    return extend_project(eid, ext, date)


def get_users(project=None):
    """
    This function suppose to return all users belonging to a project if project
    record is provided as argument. Otherwise it'll return the list of all
    users registered in the system
    :param project: Object or None. Record of a project or None
    :return: List.
    """
    if project:
        get_limbo_users([project])
        return project.users
    else:
        return User.query.all()


def get_limbo_users(projects):
    for project in projects:
        pid = project.id
        tasks = Tasks.query.filter(
            Tasks.processed == False, Tasks.pid == pid, Tasks.limbo_uid > 0
        ).all()
        if not tasks:
            continue
        limbos = list(map(lambda x: x.limbo_user.login, tasks))

        for user in project.users:
            login = user.login
            if login in limbos:
                user.active = "Suspended"
                limbos = [x for x in limbos if x != login]

        if len(limbos) > 0:
            add = list(filter(lambda x: x.limbo_user.login in limbos, tasks))
            new_users = list(map(lambda x: x.limbo_user.to_dict(), add))
            for user in new_users:
                user.active = "Suspended"
            project.users.extend(new_users)
    return projects


def get_project_by_name(name):
    projects = Project.query.all()
    for project in projects:
        if project.get_name() != name:
            continue
        return project
    raise ValueError("Failed to find a project with name '%s'" % name)


def get_project_record(pid):
    project = Project.query.filter_by(id=pid).first()
    if not project:
        raise ValueError("Failed to find project with id '%s'" % pid)
    return project


def project_transform(name, form):
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    new = form.new.data
    cpu = form.cpu.data
    note = form.note.data
    project = check_responsible(name)
    possible_types = get_transformation_options(project.type)
    possible_types = list(map(lambda x: x[0], possible_types))
    if new not in possible_types and "admin" not in g.permissions:
        raise ValueError("Configuration forbids transformation to %s" % new)
    project = get_project_consumption(project)
    record = Extend(project=project, hours=cpu, reason=note, extend=True,
                    present_use=project.consumed, transform=new,
                    usage_percent=project.consumed_use,
                    present_total=project.resources.cpu,
                    exception=False)
    db.session.add(record)
    db.session.commit()
    return record


def project_renew(name, form, activate=False):
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    cpu = form.cpu.data
    note = form.note.data
    project = check_responsible(name)
    if activate and project.active:
        raise ValueError("Project %s already active" % name)
    project = is_project_renewable(project)
    if not project.is_renewable and "admin" not in g.permissions:
        raise ValueError("Project %s is not renewable" % name)
    project = get_project_consumption(project)
    record = Extend(project=project, hours=cpu, reason=note, extend=False,
                    present_use=project.consumed,
                    usage_percent=project.consumed_use,
                    present_total=project.resources.cpu,
                    exception=False)
    db.session.add(record)
    db.session.commit()
    return record


def project_extend(name, form):
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    exception = form.exception.data
    cpu = form.cpu.data
    note = form.note.data
    project = check_responsible(name)
    project = is_project_extendable(project)
    if not project.is_extendable and "admin" not in g.permissions:
        raise ValueError("Project %s is not extendable" % name)
    project = get_project_consumption(project)
    record = Extend(project=project, hours=cpu, reason=note, extend=True,
                    present_use=project.consumed,
                    usage_percent=project.consumed_use,
                    present_total=project.resources.cpu,
                    exception=exception)
    db.session.add(record)
    db.session.commit()
    return record


def is_activity_report(rec):
    if (not rec.project.resources) or (not rec.project.resources.file):
        return False
    path = rec.project.resources.file.path
    if not current_app.config.get("ACTIVITY_UPLOAD", False):
        return True
    url = current_app.config.get("OWN_CLOUD_URL", None)
    if not url:
        raise ValueError("Failed to find own cloud url. Please try later")
    oc = OwnClient(url)
    login = current_app.config.get("OWN_CLOUD_LOGIN", None)
    password = current_app.config.get("OWN_CLOUD_PASSWORD", None)
    try:
        oc.login(login, password)
    except Exception as err:
        raise ValueError("Failed to connect to the cloud: %s" % err)
    remote_dir = current_app.config.get("ACTIVITY_DIR", "/")
    if remote_dir[-1] is not "/":
        remote_dir += "/"
    remote = remote_dir + path
    debug("Checking is file %s exists" % remote)
    try:
        oc.file_info(remote)
    except Exception as e:
        raise ValueError("Failed to find activity report %s on the cloud:"
                         " %s\nProbably you should re-upload it" % (path, e))
    return True


def list_of_projects():
    projects = map(lambda x: x.get_name(), Project.query.all())
    return sorted(list(projects))


def project_info_by_name(name):
    project = get_project_by_name(name)
    return project.to_dict()


def get_project_info(every=None, user_is_responsible=None):
    """
    Function which make a call to remote server and parse returned values as
    project consumption. The projects can be all projects, projects user is
    responsible for and projects user are registered in
    :param every: Boolean. If True returns consumption for all projects in the
    system
    :param user_is_responsible: Boolean. If True returns consumption for the
    projects user is responsible in. False returns consumption for the projects
    user registered in
    :return: List. Return projects with project consumption
    """
    if every:
        projects = Project.query.all()
    else:
        if user_is_responsible:
            projects = Project.query.filter_by(responsible = current_user).all()
        else:
            projects = current_user.project
    if not projects:
        if every:
            raise ValueError("No projects found!")
        else:
            raise ValueError("No projects found for user '%s'" %
                             current_user.full())
    info = list(map(lambda x: get_project_consumption(x), projects))
    debug(info)
    return info


def get_project_consumption(project, start=None, end=None):
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
    if not end:
        end = dt.now(timezone.utc)
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


def set_state(pid, state):
    """
    Set active state for a project
    :param pid: Integer. ID of a project
    :param state: Boolean. Set state of a project
    :return: Project record
    """
    project = get_project_record(pid)
    if type(state) != bool:
        ValueError("Argument state is not boolean: %s" % state)
    project.active = state
    db.session.commit()
    return project


def is_project_extendable(project):
    """
    Check if project type has evaluation_dt or extendable option in config file
    and set is_extendable property True if one of the options is present or
    False otherwise.
    :param project: Object. Project object
    :return: Object. Project object
    """
    cfg = project_config()
    eva = cfg[project.type].get("evaluation_dt", None)
    ext = cfg[project.type].get("extendable", False)
    if eva or ext:
        project.is_extendable = True
    else:
        project.is_extendable = False
    return project


def is_project_renewable(project):
    """
    Check if project type has finish_dt option in config file and set
    is_renewable property True if finish_dt present or False otherwise. But
    if finish_notice_dt is in configuration file the code actually check if
    dt.now() is in between time interval finish_notice_dt - now - finish_dt
    :param project: Object. Project object
    :return: Object. Project object
    """
    cfg = project_config()
    finish = cfg[project.type].get("finish_dt", None)
    resource_end = project.resources.ttl
    if finish and (resource_end > finish):
        finish = resource_end
    pre_end = cfg[project.type].get("finish_notice_dt", None)
    if finish and pre_end:
        now = dt.now(timezone.utc)
        if pre_end < now < finish:
            project.is_renewable = True
        else:
            project.is_renewable = False
    elif finish and not pre_end:
        project.is_renewable = True
    else:
        project.is_renewable = False
    return project


def get_transformation_options(project_type=None):
    """
    Checking what transformation options are available in configuration file for
    giving type of project.
    :param project_type: String. Type of the project (i.e. subsection in project
                         configuration file.
    :return: List. List of tuples, first item in tuple is type to which this
             project type can be transformed, second item is type's
             description
    """
    config = project_config()
    options = []
    for name in config.keys():
        desc = config[name].get("description", None)
        options.append((name.lower(), desc if desc else name))

    if (not project_type) or (project_type not in config.keys()):
        return options

    trans = config[project_type].get("transform", None)
    if not trans:
        return options

    options_copy = options.copy()
    for option in options_copy:
        if option[0] not in trans:
            options.remove(option)
    return options
