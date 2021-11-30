from logging import debug, error
import flask_excel as excel
from datetime import datetime as dt, timezone

from flask import current_app
from base import db
from base.database.schema import Project
from base.functions import (
    project_get_info,
    group_for_consumption,
    slurm_consumption_raw,
    slurm_parse_project_conso)


def resources_update(projects, force=False, end=dt.now()):
    """
    Updates the total consumption of the projects with valid resources.
    Consumption start is time of resource creation, consumption finish is 00:00
    of current day
    :param pid: update just a single project with a given pid
    :param force: Boolean. Default False. If True then consumption will be
    recalculated from resource creation date.
    :param every: Boolean. Default False. Attempts to update every register
    project, not only active
    :param nightly: Boolean. Default True. Set end time to 00:00 pf everyday.
    Otherwise end time sets to 00 minutes of current hour
    :return: HTTP 200 OK
    """
    if pid:
        projects = [Project.query.filter_by(id=pid).first()]
    elif every:
        projects = Project.query.all()
    else:
        projects = Project.query.filter_by(active=True).all()
    if nightly:
        end = dt.now().replace(hour=0, minute=0, second=0, microsecond=0,
                               tzinfo=timezone.utc)
    else:
        end = dt.now().replace(minute=0, second=0, microsecond=0,
                               tzinfo=timezone.utc)

    dates = group_for_consumption(projects, recalculate=force)
    for start, value in dates.items():
        if start == end:
            debug("Start date %s and finish %s is same" % (start, end))
            continue
        accounts = ",".join(list(map(lambda x: x.get_name(), value)))
        begin = start.strftime("%Y-%m-%dT%H:%M")
        finish = end.strftime("%Y-%m-%dT%H:%M")
        result, cmd = slurm_consumption_raw(accounts, begin, finish)
        if not result:
            debug("No result is no consumption? Should updated")
            continue
        conso = slurm_parse_project_conso(result)
        names = conso.keys()
        for project in value:
            name = project.get_name()
            if name not in names:
                continue
            project.resources.consumption_ts = end
            consumption = int(conso[name]["total consumption"])
            if force:
                project.resources.consumption = consumption
            else:
                project.resources.consumption += consumption
            project.resources.consumption_raw = str(conso[name])
            debug("Updated resource with ID: %s" % project.resources.id)
    db.session.commit()
    return "", 200


def dump_projects_database(extension_type):
    if extension_type not in ["csv", "ods", "xls", "xlsx"]:
        raise ValueError("Unsupported format: %s" % extension_type)
    dirty_projects = project_get_info(every=True, usage=False)
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
    return excel.make_response_from_records(output, file_type=extension_type, file_name=filename)


def project_types():
    """
    Get distinct values of Project.type
    :return: list of distinct types
    """
    types = []
    for t in db.session.query(Project.type).distinct():
        tmp = t.type.strip()
        if not tmp:
            continue
        types.append(tmp)
    debug("Got project types: %s" % types)
    return types
