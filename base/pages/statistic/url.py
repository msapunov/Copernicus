"""URL routes for the statistic blueprint: project stats, accounting,
activation, and suspension.
"""

from flask import jsonify, render_template
from flask_login import login_required

from base.database.schema import Accounting, Project
from base.pages import grant_access
from base.pages.project.magic import set_state
from base.pages.statistic.magic import project_types, render_project
from base.pages.statistic import bp

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


@bp.route("/statistic/accounting", methods=["POST"])
@bp.route("/statistic/accounting/<string:name>", methods=["POST"])
@login_required
@grant_access("admin", "responsible", "tech")
def project_info(name=None):
    """Return accounting data for one or all projects.

    Args:
        name: Optional project name to filter by.

    Returns:
        JSON with consumption data per project.
    """
    if name:
        projects = Project.query.filter_by(name=name).all()
    else:
        projects = Project.query.filter_by(active=True).all()
    data = {
        i.name: {
            "consumption": i.account(),
            "total": i.resources.cpu if i.resources else 0,
        }
        for i in projects
    }
    return jsonify(data=data)


@bp.route("/statistic/activate/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_project_activate(pid):
    """Activate a project.

    Args:
        pid: Project ID.

    Returns:
        JSON with updated project dictionary.
    """
    return jsonify(data=set_state(pid, True))


@bp.route("/statistic/suspend/<int:pid>", methods=["POST"])
@login_required
@grant_access("admin")
def web_admin_project_suspend(pid):
    """Suspend a project.

    Args:
        pid: Project ID.

    Returns:
        JSON with updated project dictionary.
    """
    return jsonify(data=set_state(pid, False))


@bp.route("/statistic/all", methods=["POST"])
@login_required
@grant_access("admin", "tech")
def web_statistic_all():
    """Return consumption data for all projects and the latest accounting date.

    Returns:
        JSON with project consumption and last accounting date.
    """
    data = {i.name: i.account() for i in Project.query.all()}
    last = (Accounting.query.distinct(Accounting.date)
            .order_by(Accounting.date.desc()).first()).date
    return jsonify(data=data, finish=last.strftime("%Y-%m-%dT%H:%M"))


@bp.route("/statistic/list", methods=["POST"])
@login_required
@grant_access("admin")
def web_statistic_list():
    """Return a list of all projects with full details.

    Returns:
        JSON with list of project dictionaries.
    """
    return jsonify(data=list(map(lambda x: x.to_dict(), Project.query.all())))


@bp.route("/statistic/expand/<string:name>", methods=["POST"])
@login_required
@grant_access("admin", "manager")
def web_admin_bits_user_info(name):
    """Render the expanded view for a project in the statistic page.

    Args:
        name: Project name.

    Returns:
        Rendered HTML.
    """
    return render_project(name)


@bp.route("/statistic/<string:name>", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_statistic_name(name):
    """Render the statistic page for a single project.

    Args:
        name: Project name.

    Returns:
        Rendered statistic.html template.
    """
    info = render_project(name)
    return render_template("statistic.html", project=info)


@bp.route("/statistic", methods=["GET", "POST"])
@bp.route("/statistic.html", methods=["GET", "POST"])
@login_required
@grant_access("admin")
def web_statistic_index():
    """Render the main statistic page.

    Returns:
        Rendered statistic.html template with project types.
    """
    types = project_types()
    return render_template("statistic.html", project_types=types)
