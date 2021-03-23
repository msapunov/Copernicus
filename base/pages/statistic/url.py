from flask import render_template, jsonify
from flask_login import login_required
from base.functions import resources_update_statistics, project_get_info
from base.pages import grant_access
from base.pages.user import bp
from base.pages.statistic.magic import dump_projects_database, project_types


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/projects.csv", methods=["GET"])
@login_required
@grant_access("admin")
def web_projects_csv():
    return dump_projects_database("csv")


@bp.route("/projects.ods", methods=["GET"])
@login_required
@grant_access("admin")
def web_projects_ods():
    return dump_projects_database("ods")


@bp.route("/projects.xls", methods=["GET"])
@login_required
@grant_access("admin")
def web_projects_xls():
    return dump_projects_database("xls")


@bp.route("/statistic/update", methods=["GET"])
@login_required
@grant_access("admin", "tech")
def web_statistic_update():
    resources_update_statistics(force=True)
    return "", 200


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


@bp.route("/statistic/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_statistic_list():
    projects = list(filter(lambda x: x, project_get_info(every=True)))
    stat = list(map(lambda x: x.with_usage(), projects)) if projects else []
    return jsonify(data=stat)


@bp.route("/statistic.html", methods=["GET"])
@login_required
@grant_access("admin")
def web_statistic_index():
    types = project_types()
    return render_template("statistic.html", project_types=types)
