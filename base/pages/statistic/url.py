from flask import render_template, jsonify, request
from flask_login import login_required
from base.pages import grant_access
from base.pages.user import bp
from base.pages.statistic.magic import (
    consumption_update,
    dump_projects_database,
    project_types)
from base.pages.project.magic import set_state
from base.database.schema import Project
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


@bp.route("/statistic/update/hourly", methods=["POST", "GET"])
@login_required
@grant_access("admin", "tech")
def web_statistic_update_hourly():
    end = dt.now().replace(minute=0, second=0, microsecond=0,
                           tzinfo=timezone.utc)
    projects = Project.query.filter_by(active=True).all()
    resources_update(projects, end=end)
    return "Hourly statistic update", 200


@bp.route("/statistic/update/nightly", methods=["POST", "GET"])
@login_required
@grant_access("admin", "tech")
def web_statistic_update_nightly():
    end = dt.now().replace(hour=0, minute=0, second=0, microsecond=0,
                           tzinfo=timezone.utc)
    projects = Project.query.all()
    resources_update(projects, force=True, end=end)
    return "Nightly statistic update", 200


@bp.route("/statistic/activate/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_project_activate(pid):
    return jsonify(data=set_state(pid, True).with_usage())


@bp.route("/statistic/suspend/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_project_suspend(pid):
    return jsonify(data=set_state(pid, False).with_usage())


@bp.route("/statistic/consumption/<string:name>", methods=["POST"])
@login_required
@grant_access("admin")
def web_statistic_consumption(name):
    project = Project.query.filter_by(name=name).first()
    if not project:
        raise ValueError("Failed to find a project with name '%s'" % name)
    return jsonify(data=project.consumption().with_usage().to_dict())


@bp.route("/statistic/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_statistic_list():
    all_projects = Project.query.all()
    projects = resources_update(all_projects)
    if not projects:
        return jsonify(data=[])
    return jsonify(data=list(map(lambda x: x.with_usage().to_dict(), projects)))


@bp.route("/statistic.html", methods=["GET"])
@login_required
@grant_access("admin")
def web_statistic_index():
    types = project_types()
    return render_template("statistic.html", project_types=types)
