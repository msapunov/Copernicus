from logging import debug
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
