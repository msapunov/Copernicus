from flask import render_template
from flask_login import login_required
from base.pages import grant_access
from base.functions import resources_update_statistics, project_get_info
from base.pages.user import bp


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/statistic/update", methods=["GET"])
@login_required
@grant_access("admin", "tech")
def web_statistic_update():
    resources_update_statistics(force=True)
    return "", 200


@bp.route("/statistic.html", methods=["GET"])
@login_required
@grant_access("admin")
def web_statistic_index():
    return render_template("statistic.html", data=project_get_info(every=True))
