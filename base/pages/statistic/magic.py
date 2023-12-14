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


def consumption_query(begin=timedelta(days=1), finish=dt.now()):
    """
    Construct sreport command to get consumption on a given interval of time.
    By default, the interval is from yesterday to today, from midnight
    to midnight.
    @param begin: DateTime, by default is yesterday
    @param finish: DateTime, by default is today
    @return: Result of slurm_parse function which is dictionary of dictionaries,
     where project name is the key in first dictionary, consumption is the value
    """
    start = begin.strftime("%Y-%m-%d")
    end = finish.strftime("%Y-%m-%d")
    cmd = ["sreport", "cluster", "AccountUtilizationByUser", "-t", "hours"]
    cmd += ["-nP", "format=Account,Login,Used", ]
    cmd += ["start=%sT00:00:00" % start, "end=%sT00:00:00" % end]
    result, err = ssh_wrapper(" ".join(cmd))
    if not result:
        debug("Error getting information from the remote server: %s" % err)
        return None
    return slurm_parse(result)


def consumption_update():
    """
    Updates the total consumption for the projects with valid resources.
    Consumption start is time of resource creation if force parameter is True.
    If force is False then start time will be the value of consumption_ts field
    associated with resource. If end date is not provided then current date and
    time will be used.
    :return: List. List of updated resources objects
    """
    projects = Project.query.filter_by(active=True).all()
    for project in projects:
        project.resources.consumption = project.account()
    if db.session.dirty:
        db.session.commit()
    return projects


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
