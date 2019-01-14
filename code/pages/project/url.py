from flask import render_template, flash, request, jsonify
from flask_login import login_required, current_user
from code.pages.user import bp
from code.pages.user.magic import ssh_wrapper
from code.utils import bytes2human, accounting_start
from datetime import datetime as dt


@bp.route("/project/extend", methods=["POST"])
@login_required
def web_project_extend():
    from code import db
    from code.database.schema import ExtendDB, Project

    data = request.get_json()
    if not data:
        return flash("Expecting application/json requests")

    raw_pid = data["project"]
    try:
        pid = int(raw_pid)
    except Exception as e:
        return jsonify( message = "Failed to parse project id: %s" % e)
    if (not pid) or (pid < 1):
        return jsonify(message="Project id must be a positive number: %s" % pid)

    raw_cpu = data["cpu"]
    try:
        cpu = int(raw_cpu)
    except Exception as e:
        return jsonify(message="CPU hours is not integer: %s" % e)
    if (not cpu) or (cpu < 1):
        return jsonify(message="CPU hours must be a positive number: %s" % cpu)

    raw_note = data["note"]
    try:
        note = str(raw_note)
    except Exception as e:
        return jsonify(message="Failure processing motivation field: %s" % e)

    project = Project().query.filter_by(id=pid).first()
    if not project:
        return jsonify(message="Failed to find a project with id: %s" % pid)
    extend = ExtendDB().query.filter(ExtendDB.project == project).one()
    if not extend:
        extend = ExtendDB(project=project)
    extend.demand = cpu
    extend.reason = note
    db.session.commit()
    send_extend_mail(project, extend)
    return jsonify(message="Project extension has been registered successfully")


@bp.route("/project/history", methods=["POST"])
@login_required
def web_project_history():
    from code.database.schema import LogDB

    data = request.get_json()
    if not data:
        return flash("Expecting application/json requests")
    raw_pid = data["project"]
    try:
        pid = int(raw_pid)
    except Exception as e:
        return render_template("500.html", error = str(e))
        #return jsonify("Failed to parse project id: %s" % e)
    recs = LogDB().query.filter(LogDB.project_id == pid).all()
    result = list(map(lambda x: x.to_dict(), recs))
    return jsonify(result)


@bp.route("/project.html", methods=["GET"])
@login_required
def project_index():
    start = accounting_start()
    end = dt.now().strftime("%m/%d/%y-%H:%M")
    projects = get_project_info(start, end)
    now = dt.now()
    if now.month != 1:
        renew = False
    else:
        renew = now.year
    data = {"projects": projects, "renew": renew}
    return render_template("project.html", data=data)


def get_project_info(start, end):
    from code.database.schema import Project

    p_ids = current_user.project_ids()
    tmp = []
    for pid in p_ids:
        project = Project().query.filter_by(id=pid).first()
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


def get_project_consumption(projects, start, end):
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
