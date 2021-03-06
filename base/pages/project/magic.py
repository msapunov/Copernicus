import logging as log
from datetime import datetime as dt
from pathlib import Path

from flask import flash, current_app, jsonify, request, render_template
from flask_login import current_user
from owncloud import Client as OwnClient
from pdfkit import from_string

from base import db
from base.database.schema import Extend, File, Project, Tasks
from base.pages import ProjectLog, calculate_usage
from base.pages import ssh_wrapper, check_int, check_str, send_message
from base.pages.board.magic import create_resource
from base.utils import accounting_start, save_file, get_tmpdir
from logging import error, debug, warning

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def upload_file_cloud(path, remote=None):
    url = current_app.config.get("OWN_CLOUD_URL", None)
    if not url:
        log.error("No url to the cloud given")
        return False
    oc = OwnClient(url)
    login = current_app.config.get("OWN_CLOUD_LOGIN", None)
    password = current_app.config.get("OWN_CLOUD_PASSWORD", None)
    try:
        oc.login(login, password)
    except Exception as err:
        log.error("Failed to connect to the cloud: %s" % err)
        return False
    po = Path(path)
    if not po.exists() or not po.is_file():
        log.error("Can't upload a file to a cloud. '%s' doesn't exists or not "
                  "a file" % path)
        return False
    if not remote:
        remote_dir = current_app.config.get("ACTIVITY_DIR", "/")
        if remote_dir[-1] is not "/":
            remote_dir += "/"
        remote = remote_dir + po.name
    log.debug("Uploading file %s to %s" % (path, remote))
    return oc.put_file(remote, path)


def check_responsible(name):
    project = get_project_by_name(name)
    if current_user != project.get_responsible():
        raise ValueError("User %s is not register as the responsible person "
                         "for the project %s" % (current_user.login, name))
    return project


def get_activity_files(name):
    check_responsible(name)
    temp_dir = get_tmpdir(current_app)
    log.debug("Using temporary directory to store files: %s" % temp_dir)
    pattern = "*%s*" % name
    log.debug("Pattern %s to get associated files for %s" % (pattern, name))
    already = list(Path(temp_dir).glob(pattern))
    log.debug("List of existing files: %s" % already)
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
    log.debug("Returning result: %s" % name)
    return name


def save_report(project):
    project_name = project.get_name()
    html = render_template("report.html", data=project)
    ts = str(dt.now().replace(microsecond=0).isoformat("_")).replace(":", "-")
    name = "%s_activity_report_%s.pdf" % (project_name, ts)
    path = str(Path(get_tmpdir(current_app), name))
    log.debug("The resulting PDF will be saved to: %s" % path)
    pdf = from_string(html, path)
    log.debug("If PDF converted successfully: %s" % pdf)
    if not pdf:
        return False

    if current_app.config.get("ACTIVITY_UPLOAD", False):
        log.debug("Uploading report to a cloud storage")
        if current_app.config.get("ACTIVITY_UPLOAD_IMG", False):
            for i in ["image_1", "image_2", "image_3"]:
                tmp = getattr(project, i, None)
                upload_file_cloud(tmp) if tmp else False
        upload_file_cloud(path)

    if current_app.config.get("ACTIVITY_SEND", False):
        log.debug("Sending report by mail to project's responsible")
        result = send_activity_report(project, path)
        log.debug(result)

    report = File(path=name,
                  size=Path(path).stat().st_size,
                  comment="Activity report",
                  user=current_user,
                  project_id=project.id,
                  created=dt.now())
    project.resources.file = report
    db.session.commit()
    log.debug("Activity report saved to the file %s" % path)
    return "Activity report saved on the server to the file %s" % name


def report_activity(name, req):
    project = check_responsible(name)
    data = req.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")

    result = get_project_consumption(project)
    if not result:
        raise ValueError("No information found for project '%s' Failure during "
                         "report generation" % project.get_name())
    result.report = data["report"]
    result.doi = data["doi"]
    result.training = data["training"]
    result.hiring = data["hiring"]
    result.generated = dt.strftime(dt.now(), "%c")

    tmp = get_tmpdir(current_app)
    for i in ["image_1", "image_2", "image_3"]:
        path = Path(tmp, data[i])
        if path.exists() and path.is_file():
            setattr(result, i, str(path.resolve()))
    log.debug(result)
    return save_report(result)


def remove_activity(name, file_name):
    check_responsible(name)
    temp_dir = get_tmpdir(current_app)
    path = Path(temp_dir) / file_name
    if not path.exists():
        log.debug("Path doesn't exists: %s" % str(path))
        return True
    if path.is_file():
        path.unlink()
        log.debug("File deleted: %s" % file_name)
        return True
    if path.is_dir():
        log.error("Path %s is a directory and can't be removed" % str(path))
        return False


def clean_activity(name):
    log.debug("Cleaning activity files for project %s" % name)
    project = check_responsible(name)
    files = get_activity_files(project.get_name())
    if len(files) < 1:
        return True
    for x in files:
        x.unlink()
        log.debug("File deleted: %s" % str(x))
    return True


def renew_project(id, ext, date):
    ext.project.resources.valid = False
    ext.project.resources = create_resource(ext.project, ext.hours)
    msg = "Created based on renewal request ID %s on %s" % (id, date)
    ext.project.resources.comment = msg
    return ProjectLog(ext.project).renew(ext)


def extend_project(id, ext, date):
    ext.project.resources.cpu += ext.hours
    ext.project.resources.valid = True
    msg = "CPU value has been extended to %s hours on %s based upon "\
          "extension request ID %s" % (ext.hours, date, id)
    if ext.project.resources.comment:
        ext.project.resources.comment = ext.project.resources.comment \
                                        + "\n" + msg
    else:
        ext.project.resources.comment = msg
    return ProjectLog(ext.project).extended(ext)


def transform_project(id, ext, date):
    ext.project.type = ext.transform
    ext.project.name = "%s%s" % (ext.transform, str(ext.project.id).zfill(3))
    ext.project.resources.valid = False
    ext.project.resources = create_resource(ext.project, ext.hours)
    msg = "Created based on transformation request ID %s on %s" % (id, date)
    ext.project.resources.comment = msg
    return ProjectLog(ext.project).transformed(ext)


def process_extension(eid):
    ext = Extend.query.filter_by(id=eid).first()
    if not ext:
        raise ValueError("Failed to find extension record with id '%s'" % ext)
    ext.done = True
    date = dt.now().replace(microsecond=0).isoformat(" ")
    never_extend = current_app.config.get("NO_EXTENSION_TYPE", [])
    never_renew = current_app.config.get("NO_RENEWAL_TYPE", [])
    if ext.transform.strip() != "":
        return transform_project(eid, ext, date)
    if ext.project.type in never_extend:
        return renew_project(eid, ext, date)
    if ext.project.type in never_renew:
        return extend_project(eid, ext, date)
    if not ext.extend:
        return renew_project(eid, ext, date)
    return extend_project(eid, ext, date)


def pending_resources():
    projects = Project.query.all()
    pending = list(filter(lambda x: x.resources.treated == False, projects))
    return list(map(lambda x: x.api_resources(), pending))


def get_users(pid):
    project = get_project_record(pid)
    get_limbo_users([project])
    users = list(map(lambda x: x.to_dict(), project.users))
    debug(users)
    for user in users:
        if user["login"] == project.responsible.login:
            user["responsible"] = True
    return users


def get_limbo_users(projects):
    if not projects:
        return projects

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


def is_extension():
    kick_month = int(current_app.config.get("EXTENSION_KICKOFF_MONTH", 1))
    kick_day = int(current_app.config.get("EXTENSION_KICKOFF_DAY", 1))
    allo_month = int(current_app.config.get("ACC_START_MONTH", 3))
    allo_day = int(current_app.config.get("ACC_START_DAY", 1))

    present = dt.now()
    kick_date = dt(present.year, kick_month, kick_day)
    allo_date = dt(present.year, allo_month, allo_day)
    if kick_date < present < allo_date:
        return False
    else:
        return True


def extend_update():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    if "project" in data:
        pid = check_int(data["project"])
    else:
        raise ValueError("Project ID is missing")
    if "cpu" in data:
        cpu = check_int(data["cpu"])
    else:
        cpu = 0
    if "note" in data:
        note = check_str(data["note"])
    else:
        raise ValueError("Comment is absent")

    if ("exception" in data) and (check_str(data["exception"]) == "yes"):
        exception = True
    else:
        exception = False

    extend = is_extension()
    # Make sure that exceptional extension are extension no matter when
    if not extend and exception:
        extend = True

    project = get_project_record(pid)
    project = get_project_consumption(project)
    return Extend(project=project, hours=cpu, reason=note, extend=extend,
                  present_use=project.consumed,
                  usage_percent=project.consumed_use,
                  present_total=project.resources.cpu,
                  exception=exception)


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
    log.debug("Checking is file %s exists" % remote)
    try:
        oc.file_info(remote)
    except Exception as e:
        raise ValueError("Failed to find activity report %s on the cloud:"
                         " %s\nProbably you should re-upload it" % (path, e))
    return True


def send_activity_report(project, report):
    subj = "Activity report for the project %s" % project.name
    msg = """
    Dear %s
    Thank you for submitting the activity report for the project %s
    You can find a copy of the report in the attachment 
    """ % (project.responsible.full_name(), project.get_name())
    return project_email(project.responsible.email, subj, msg, attach=report)


def send_renew_mail(project, extend):
    subj = "Request renew project %s" % project.name
    msg = """
    Dear %s
    You have requested to renew your project %s with %s hours
    Renew reason is:
      %s
    Your request will be examined shortly
    """ % (project.responsible.full_name(), project.name, extend.hours,
           extend.reason)
    project_email(project.responsible.email, subj, msg)


def send_extend_mail(project, extend):
    subj = "Request extend project %s" % project.name
    msg = """
    Dear %s
    You have requested to extend your project %s with %s hours
    Extension reason is:
      %s
    Your request will be examined shortly
    """ % (project.responsible.full_name(), project.name, extend.hours,
           extend.reason)
    project_email(project.responsible.email, subj, msg)


def send_activate_mail(project, extend):
    subj = "Request to activate project %s" % project.name
    msg = """
    Dear %s
    You have requested to activate your suspended project %s
    The reason for activation is:
      %s
    Your request will be examined shortly
    """ % (project.responsible.full_name(), project.name, extend.reason)
    project_email(project.responsible.email, subj, msg)


def send_transform_mail(project, extend):
    subj = "Request to transform project %s" % project.name
    msg = """
    Dear %s
    You have requested to transform your project %s of type A to type B
    The reason for transformation is:
      %s
    Your request will be examined shortly
    """ % (project.responsible.full_name(), project.name, extend.reason)
    project_email(project.responsible.email, subj, msg)


def project_email(to, title, msg, attach=None):
    by_who = current_app.config["EMAIL_PROJECT"]
    return jsonify(data=send_message(to, by_who=by_who, title=title,
                                     message=msg, attach=attach))


def list_of_projects():
    projects = map(lambda x: x.get_name(), Project.query.all())
    return sorted(list(projects))


def get_project_overview():
    def extract_info(rec):
        name = rec.get_name()
        start = rec.resources.created.strftime("%Y-%m-%d")
        finish = rec.resources.ttl.strftime("%Y-%m-%d")
        total = rec.resources.cpu
        responsible = rec.responsible.login
        return "%s %s %s %s %s" % (name, start, finish, total, responsible)

    projects = Project.query.all()
    return list(map(lambda x: extract_info(x), projects))


def project_info_by_name(name):
    project = get_project_by_name(name)
    return project.to_dict()


def get_project_info(every=None, user_is_responsible=None):
    if every:
        projects = Project.query.all()
    else:
        pids = current_user.project_ids()
        if user_is_responsible:
            query = Project.query.filter(Project.id.in_(pids))
            projects = query.filter(Project.responsible == current_user).all()
        else:
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
        end = dt.now()
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
