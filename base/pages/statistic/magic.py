from logging import debug
import flask_excel as excel
from flask import current_app, render_template, url_for
from base import db
from base.database.schema import Project


def render_project(name):
    project = Project.query.filter_by(name=name).first()
    acc_url = url_for("admin.web_admin_accounting_project", name=name)
    user_url = url_for("admin.web_login_registry", login="")
    history_url = url_for("project.web_project_history", project_name=project.name)
    history = render_template("modals/common_show_history.html", rec=project,
                              url=history_url)
    row = render_template("bits/statistic_expand_row.html", project=project,
                          accounting_url=acc_url, user_url=user_url)
    return row + history


def dump_projects_database(extension_type, request):
    """
    Select all available projects in the database excluding the projects
    without responsible or registration reference and return the data in a
    file formatted according to extension_type parameter
    :param extension_type: String. File format to store the data. Could be
    one of following: csv, ods, xls, xlsx
    :return: HTTP response
    """
    if extension_type not in ["csv", "ods", "xls", "xlsx"]:
        raise ValueError("Unsupported format: %s" % extension_type)
    select = request.args.get("projects", None)
    if not select:
        dirty_projects = Project.query.all()
    else:
        names = select.split(",")
        dirty_projects = Project.query.filter(Project.name.in_(names)).all()
    projects = []
    for project in dirty_projects:
        if not project.responsible:
            continue
        if not project.ref:
            continue
        projects.append(project)
    output = sorted(list(map(lambda x: x.pretty_dict(), projects)),
                    key=lambda x: x["id"])
    excel.init_excel(current_app)
    filename = "projects." + extension_type
    return excel.make_response_from_records(output, file_type=extension_type,
                                            file_name=filename)


def project_types():
    """
    Get distinct values of Project.type
    :return: List. List of distinct types
    """
    types = []
    for t in db.session.query(Project.type).distinct():
        tmp = t.type.strip()
        if not tmp:
            continue
        types.append(tmp)
    debug("Got project types: %s" % types)
    return types
