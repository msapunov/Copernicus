"""Business logic for the statistic page: project rendering and type listing."""

from logging import debug

from flask import render_template, url_for

from base import db
from base.database.schema import Project


def render_project(name):
    """Render the expanded HTML for a project in the statistic view.

    Includes accounting URL, user registry URL, and history modal.

    Args:
        name: Project name.

    Returns:
        Concatenated HTML string.
    """
    project = Project.query.filter_by(name=name).first()
    acc_url = url_for("admin.web_admin_accounting_project", name=name)
    user_url = url_for("admin.web_login_registry", login="")
    history_url = url_for("project.web_project_history", project_name=project.name)
    history = render_template(
        "modals/common_show_history.html", rec=project, url=history_url
    )
    row = render_template(
        "bits/statistic_expand_row.html",
        project=project,
        accounting_url=acc_url,
        user_url=user_url,
    )
    return row + history


def project_types():
    """Get distinct project types from the database.

    Returns:
        List of type strings.
    """
    types = []
    for t in db.session.query(Project.type).distinct():
        tmp = t.type.strip()
        if not tmp:
            continue
        types.append(tmp)
    debug(f"Got project types: {types}")
    return types
