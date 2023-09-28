from flask import render_template, jsonify, request, abort
from flask_login import login_required
from base.functions import consumption
from base.pages import grant_access
from base.pages.user import bp
from base.pages.statistic.magic import (
    accounting_run,
    consumption_update,
    dump_projects_database,
    project_types)
from base.pages.project.magic import set_state
from base.database.schema import Project, Accounting
from datetime import datetime as dt
from json import loads, JSONDecodeError


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/projects.csv", methods=["GET"])
@login_required
@grant_access("admin")
def web_projects_csv():
    return dump_projects_database("csv", request)


@bp.route("/projects.ods", methods=["GET"])
@login_required
@grant_access("admin")
def web_projects_ods():
    return dump_projects_database("ods", request)


@bp.route("/projects.xls", methods=["GET"])
@login_required
@grant_access("admin")
def web_projects_xls():
    return dump_projects_database("xls", request)


@bp.route("/statistic/update", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def web_statistic_update():
    accounting_run()
    return "Statistic updated", 200


@bp.route("/statistic/activate/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_project_activate(pid):
    return jsonify(data=set_state(pid, True))


@bp.route("/statistic/suspend/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_project_suspend(pid):
    return jsonify(data=set_state(pid, False))


@bp.route("/statistic/consumption/<string:name>", methods=["POST"])
@login_required
@grant_access("admin")
def web_statistic_consumption(name):
    project = Project.query.filter_by(name=name).first()
    if not project:
        raise ValueError("Failed to find a project with name '%s'" % name)
    result = consumption(name, project.resources.created, project.resources.ttl)
    if result:
        project.resources.consumption = result[name]["total consumption"]
    return jsonify(data=project.to_dict())


@bp.route("/statistic/all", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def web_statistic_all():
    data = list(map(lambda x: {x.name: x.account()}, Project.query.all()))
    last = (Accounting.query.distinct(Accounting.date)
            .order_by(Accounting.date.desc()).first()).date
    return jsonify(data=data, finish=last.strftime("%Y-%m-%dT%H:%M"))


@bp.route("/statistic/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_statistic_list():
    return jsonify(data=list(map(lambda x: x.to_dict(), Project.query.all())))


@bp.route("/statistic.html", methods=["GET"])
@login_required
@grant_access("admin")
def web_statistic_index():
    types = project_types()
    return render_template("statistic.html", project_types=types)
