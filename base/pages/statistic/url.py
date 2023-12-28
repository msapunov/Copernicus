from flask import render_template, jsonify, request, abort
from flask_login import login_required
from base.pages import grant_access
from base.pages.user import bp
from base.pages.statistic.magic import (
    render_project,
    dump_projects_database,
    project_types)
from base.pages.project.magic import set_state
from base.database.schema import Project, Accounting


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/statistic/accounting", methods=["POST"])
@bp.route("/statistic/accounting/<string:name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible", "tech")
def project_info(name=None):
    if name:
        projects = Project.query.filter_by(name=name).all()
    else:
        projects = Project.query.filter_by(active=True).all()
    data = {
        i.name: {
            "consumption": i.account(),
            "total": i.resources.cpu if i.resources else 0
        } for i in projects
    }
    return jsonify(data=data)


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


@bp.route("/statistic/all", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def web_statistic_all():
    data = {i.name: i.account() for i in Project.query.all()}
    last = (Accounting.query.distinct(Accounting.date)
            .order_by(Accounting.date.desc()).first()).date
    return jsonify(data=data, finish=last.strftime("%Y-%m-%dT%H:%M"))


@bp.route("/statistic/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_statistic_list():
    return jsonify(data=list(map(lambda x: x.to_dict(), Project.query.all())))


@bp.route("/statistic/<string:name>", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_statistic_name(name):
    info = render_project(name)
    return render_template("statistic.html", project=info)


@bp.route("/statistic", methods=["GET", "POST"])
@bp.route("/statistic.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_statistic_index():
    types = project_types()
    return render_template("statistic.html", project_types=types)
