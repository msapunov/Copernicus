from flask import render_template, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from code.pages.user import bp
from code.pages.user.magic import ssh_wrapper
from code.utils import bytes2human, accounting_start
from datetime import datetime as dt
from flask_mail import Message


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
    project_email(subj, [project.responsible.email], msg)


def send_activate_mail(project, extend):
    subj = "Request to activate project %s" % project.name
    msg = """
    Dear %s
    You have requested to activate your suspended project %s
    The reason for activation is:
      %s
    Your request will be examined shortly
    """ % (project.responsible.full_name(), project.name, extend.reason)
    project_email(subj, [project.responsible.email], msg)


def project_email(subject, recipients, text_body):
    from code import mail

    sender = current_app.config["EMAIL_PROJECT"]
    tech = [current_app.config["EMAIL_TECH"]]
    msg = Message(subject, sender=sender, recipients=recipients, cc=tech)
    postfix = "If this email has been sent to you by mistake, please report " \
              "to: %s" % tech
    msg.body = text_body + postfix
    mail.send(msg)


def check_pid(data):
    raw_pid = data["project"]
    try:
        pid = int(raw_pid)
    except Exception as e:
        return jsonify(message="Failed to parse project id: %s" % e)
    if (not pid) or (pid < 1):
        return jsonify(message="Project id must be a positive number: %s" % pid)
    return pid


def check_cpu(data):
    raw_cpu = data["cpu"]
    try:
        cpu = int(raw_cpu)
    except Exception as e:
        return jsonify(message="CPU hours is not integer: %s" % e)
    if (not cpu) or (cpu < 1):
        return jsonify(message="CPU hours must be a positive number: %s" % cpu)
    return cpu


def check_motivation(data):
    raw_note = data["note"]
    try:
        note = str(raw_note)
    except Exception as e:
        return jsonify(message="Failure processing motivation field: %s" % e)
    if not note:
        return jsonify(message="Motivation field can't be empty")
    return note


@bp.route("/project/reactivate", methods=["POST"])
@login_required
def web_project_reactivate():
    from code import db
    from code.database.schema import ExtendDB, Project

    data = request.get_json()
    if not data:
        return flash("Expecting application/json requests")

    pid = check_pid(data)
    note = check_motivation(data)

    project = Project().query.filter_by(id=pid).first()
    if not project:
        return jsonify(message="Failed to find a project with id: %s" % pid)
    if project.active:
        return jsonify(message="Failed to re-activate already active project")

    p_name = project.get_name()
    p_info = get_project_consumption([p_name])
    extend = ExtendDB(project=project, hours=0, reason=note,
                      present_use=p_info[p_name]["total"],
                      present_total = project.resources.cpu, activate=True)

    db.session.add(extend)
    ProjectLog(project).activate(extend)
    db.session.commit()
    send_activate_mail(project, extend)
    return jsonify(message="Project activation request has been registered"
                           " successfully")


@bp.route("/project/extend", methods=["POST"])
@login_required
def web_project_extend():
    from code import db
    from code.database.schema import ExtendDB, Project

    data = request.get_json()
    if not data:
        return flash("Expecting application/json requests")

    pid = check_pid(data)
    cpu = check_cpu(data)
    note = check_motivation(data)

    project = Project().query.filter_by(id=pid).first()
    if not project:
        return jsonify(message="Failed to find a project with id: %s" % pid)

    p_name = project.get_name()
    p_info = get_project_consumption([p_name])

    extend = ExtendDB(project=project, hours=cpu, reason=note,
                      present_use=p_info[p_name]["total"],
                      present_total = project.resources.cpu)

    db.session.add(extend)
    ProjectLog(project).extend(extend)
    db.session.commit()
    send_extend_mail(project, extend)
    return jsonify(message="Project extension has been registered successfully")


@bp.route("/project/history", methods=["POST"])
@login_required
def web_project_history():
    from code.database.schema import LogDB

    data = request.get_json()
    if not data:
        return jsonify(message="Expecting application/json requests")
    raw_pid = data["project"]
    try:
        pid = int(raw_pid)
    except Exception as e:
        return jsonify(message="Failed to parse project id: %s" % e)
    recs = LogDB().query.filter(LogDB.project_id == pid).all()
    result = list(map(lambda x: x.to_dict(), recs))
    return jsonify(result)


@bp.route("/project.html", methods=["GET"])
@login_required
def web_project_index():
    projects = get_project_info()
    now = dt.now()
    if now.month != 1:
        renew = False
    else:
        renew = now.year
    data = {"projects": projects, "renew": renew}
    return render_template("project.html", data=data)


def get_project_info(start=None, end=None):
    from code.database.schema import Project

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

class ProjectLog():

    def __init__(self, project):
        from code.database.schema import LogDB
        self.log = LogDB(author = current_user, project=project)

    def extend(self, extension):
        self.log.event = "extension request"
        self.log.extension = extension
        self._commit()

    def activate(self, extension):
        self.log.event = "activation request"
        self.log.extension = extension
        self._commit()

    def _commit(self):
        from code import db
        db.session.add(self.log)
#        db.session.commit()