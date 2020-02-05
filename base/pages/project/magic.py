import logging as log
from datetime import datetime as dt
from pathlib import Path

from flask import flash, current_app, jsonify, request, render_template
from flask_login import current_user
from owncloud import Client as OwnClient
from pdfkit import from_string

from base import db
from base.database.schema import Extend, File
from base.pages import ProjectLog
from base.pages import ssh_wrapper, check_int, check_str, send_message
from base.pages.board.magic import create_resource
from base.utils import accounting_start, save_file, get_tmpdir

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
    image_name = "%s_activity_report" % project
    for i in range(0, limit):
        tmp_name = "%s_%s" % (image_name, i)
        there = filter(lambda x: True if tmp_name in str(x) else False, files)
        if not list(there):
            image_name = tmp_name
            break
    name = save_file(req, get_tmpdir(current_app), image_name)
    log.debug("Returning result: %s" % name)
    return name


def save_report(data, project):
    project_name = project.get_name()
    html = render_template("report.html", data=data)
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
                upload_file_cloud(data[i]) if i in data and data[i] else False
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

    raw_result = get_project_info(p_ids=[project.id])
    if not raw_result:
        raise ValueError("No information found for project '%s' Failure during "
                         "report generation" % project.get_name())
    result = raw_result[0]
    result["report"] = data["report"]
    result["doi"] = data["doi"]
    result["training"] = data["training"]
    result["hiring"] = data["hiring"]
    result["generated"] = dt.strftime(dt.now(), "%c")

    tmp = get_tmpdir(current_app)
    for i in ["image_1", "image_2", "image_3"]:
        path = Path(tmp, data[i])
        if path.exists() and path.is_file():
            result[i] = str(path.resolve())
    log.debug(result)
    return save_report(result, project)


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


def process_extension(eid):
    ext = Extend.query.filter_by(id=eid).first()
    if not ext:
        raise ValueError("Failed to find extension record with id '%s'" % ext)
    date = dt.now().replace(microsecond=0).isoformat(" ")
    if (not ext.extend) or (ext.extend and ext.project.type == "h"):
        ext.project.resources.valid = False
        ext.project.resources = create_resource(ext.project, ext.hours)
        msg = "Created based on extension request ID %s on %s" % (eid, date)
        ext.project.resources.comment = msg
    else:
        ext.project.resources.cpu += ext.hours
        ext.project.resources.valid = True
        msg = "CPU value has been extended to %s hours on %s based upon " \
              "extension request ID %s" % (ext.hours, date, eid)
        if ext.project.resources.comment:
            ext.project.resources.comment = ext.project.resources.comment\
                                            + "\n" + msg
        else:
            ext.project.resources.comment = msg
    ext.done = True
    db.session.commit()
    ProjectLog(ext.project).extended(ext)
    return "Project extension ID %s has been processed" % eid


def pending_resources():
    from base.database.schema import Project
    projects = Project.query.all()
    pending = list(filter(lambda x: x.resources.treated == False, projects))
    return list(map(lambda x: x.api_resources(), pending))


def get_users(pid):
    projects = get_project_info(p_ids=[pid])
    get_limbo_users(projects)
    users = projects[0]["users"]
    for user in users:
        if user["login"] == projects[0]["responsible"]["login"]:
            user["responsible"] = True
    return users


def get_limbo_users(projects):
    from base.database.schema import Tasks

    if not projects:
        return projects

    for project in projects:
        pid = project["id"]
        tasks = Tasks.query.filter(
            Tasks.processed == False, Tasks.pid == pid, Tasks.limbo_uid > 0
        ).all()
        if not tasks:
            continue
        limbos = list(map(lambda x: x.limbo_user.login, tasks))

        for user in project["users"]:
            login = user["login"]
            if login in limbos:
                user["active"] = "Suspended"
                limbos = [x for x in limbos if x != login]

        if len(limbos) > 0:
            add = list(filter(lambda x: x.limbo_user.login in limbos, tasks))
            new_users = list(map(lambda x: x.limbo_user.to_dict(), add))
            for user in new_users:
                user["active"] = "Suspended"
            project["users"].extend(new_users)
    return projects


def get_project_by_name(name):
    from base.database.schema import Project

    projects = Project.query.all()
    for project in projects:
        if project.get_name() != name:
            continue
        return project
    raise ValueError("Failed to find a project with name '%s'" % name)


def get_project_record(pid):
    from base.database.schema import Project

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
    p_name = project.get_name()
    p_info = get_project_consumption([p_name])
    if not p_info:
        use = 0
    else:
        use = p_info[p_name]["total"]
    maximum = project.resources.cpu
    if not use:
        usage = 0
    else:
        usage = "{0:.1%}".format(float(use) / float(maximum))
    return Extend(project=project, hours=cpu, reason=note, present_use=use,
                  usage_percent=usage, present_total=maximum, extend=extend,
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
    from base.database.schema import Project
    projects = map(lambda x: x.get_name(), Project.query.all())
    return sorted(list(projects))


def get_project_overview():
    from base.database.schema import Project

    def extract_info(rec):
        name = rec.get_name()
        start = rec.resources.created.strftime("%Y-%m-%d")
        finish = rec.resources.ttl.strftime("%Y-%m-%d")
        total = rec.resources.cpu
        responsible = rec.responsible.login
        return "%s %s %s %s %s" % (name, start, finish, total, responsible)

    projects = Project.query.all()
    return list(map(lambda x: extract_info(x), projects))


def get_project_info(start=None, end=None, p_ids=None):
    from base.database.schema import Project

    if not p_ids:
        p_ids = current_user.project_ids()
    tmp = []
    for pid in p_ids:
        project = Project().query.filter_by(id=pid).first()
        if not project:
            continue
        if current_user != project.get_responsible():
            continue
        tmp.append(project.to_dict())
    if not tmp:
        return flash("No active projects found for user '%s'" %
                     current_user.login)

    tmp_project = list(map(lambda x: x["name"], tmp))
    conso = get_project_consumption(tmp_project, start, end)
    if not conso:
        return tmp

    for project in tmp:
        name = project["name"]
        if name in conso:
            total = conso[name]["total"]
            project["consumption"] = total
            project["usage"] = "{0:.1%}".format(
                float(total) / float(project["resources"]["cpu"]))
        else:
            project["consumption"] = 0
            project["usage"] = 0

        for user in project["users"]:
            username = user["login"]
            if name not in conso:
                user["consumption"] = 0
                continue
            if username not in conso[name]:
                user["consumption"] = 0
                continue
            user["consumption"] = conso[name][username]

    return tmp


def get_project_consumption(projects, start=None, end=None):
    if not start:
        start = accounting_start()
    if not end:
        end = dt.now().strftime("%m/%d/%y-%H:%M")

    name = ",".join(projects)
    cmd = ["sreport", "cluster", "AccountUtilizationByUser", "-t", "hours"]
    cmd += ["-nP", "format=Account,Login,Used", "Accounts=%s" % name]
    cmd += ["start=%s" % start, "end=%s" % end]
    run = " ".join(cmd)
    result, err = ssh_wrapper(run)
    if not result:
        return flash("No project consumption information found")

    tmp = {}
    for item in result:
        item = item.strip()
        project, user, conso = item.split("|")
        if project not in tmp:
            tmp[project] = {}
        if not user:
            tmp[project]["total"] = int(conso)
        else:
            tmp[project][user] = int(conso)
    return tmp
