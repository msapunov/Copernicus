from logging import debug
import flask_excel as excel
from datetime import datetime as dt, timedelta, timezone

from flask import current_app
from base import db
from base.database.schema import Project, Accounting, User
from base.functions import (
    ssh_wrapper,
    slurm_parse)


def process_accounting_data(date, result):
    """
    Function which parse incoming dict created after SLURM sreport and create
    Accounting record for accounting table
    @param date: DateTime. Argument for Accounting record
    @param result: Dictionary. Result of sreport parsing
    @return: DateTime. First argument for function call for further processing
    """
    for name, value in result.items():
        if name == "root":
            db.session.add(Accounting(date=date,
                                      cpu=value["total consumption"]))
            continue
        project = Project.query.filter_by(name=name).first()
        if not project or not project.active:
            continue
        if date.replace(tzinfo=timezone.utc) < project.resources.created:
            continue
        for login, cpu in value.items():
            if login == "total consumption":
                db.session.add(Accounting(resources=project.resources,
                                          project=project, date=date, cpu=cpu))
            else:
                user = User.query.filter_by(login=login).first()
                if user:
                    db.session.add(Accounting(resources=project.resources,
                                              project=project, user=user,
                                              date=date, cpu=cpu))
    db.session.commit()
    debug("Finish processing for date: %s" % date)
    return date


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
