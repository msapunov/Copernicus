from datetime import datetime as dt
from flask import flash, current_app, jsonify, request
from flask_login import current_user
from base import db
from base.utils import accounting_start
from base.database.schema import Extend
from base.pages import ProjectLog
from base.pages import ssh_wrapper, check_int, check_str, send_message
from base.pages.board.magic import create_resource


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def process_extension(eid):
    ext = Extend.query.filter_by(id=eid).first()
    if not ext:
        raise ValueError("Failed to find extension record with id '%s'" % ext)
    date = dt.now().replace(microsecond=0).isoformat(" ")
    if not ext.extend:
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
    return jsonify(message=ProjectLog(ext.project).extended(ext))


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
    from base.database.schema import Extend

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
        usage = "{0:.1%}".format(float(use)/float(maximum))
    return Extend(project=project, hours=cpu, reason=note, present_use=use,
                  usage_percent=usage, present_total=maximum, extend=extend,
                  exception=exception)


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


def project_email(to, title, msg):
    by_who = current_app.config["EMAIL_PROJECT"]
    return jsonify(data=send_message(to, by_who=by_who, title=title,
                                     message=msg))


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
                float(total)/float(project["resources"]["cpu"]))
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
