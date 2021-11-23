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


def resources_update_midnight(pid=None, force=False, every=False):
    """
    Updates the total consumption of the projects with valid resources.
    Consumption start is time of resource creation, consumption finish is 00:00
    of current day
    :param pid: update just a single project with a given pid
    :param force: update all registered projects
    :param every: attempts to update every project
    :return: HTTP 200 OK
    """
    if pid:
        projects = [Project.query.filter_by(id=pid).first()]
    elif every:
        projects = Project.query.all()
    else:
        projects = Project.query.filter_by(active=True).all()
    end = dt.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    if not force:
        resources = filter(lambda x: x.resources, projects)
        projects = list(filter(lambda x: x.resources.ttl > end, resources))

    dates = group_for_consumption(projects)
    for start, value in dates.items():
        accounts = ",".join(list(map(lambda x: x.get_name(), value)))
        result, cmd = slurm_consumption_raw(accounts, start, end.strftime("%Y-%m-%dT%H:%M"))
        if not result:
            continue
        conso = slurm_parse_project_conso(result)
        names = conso.keys()
        for project in value:
            name = project.get_name()
            if name not in names:
                continue
#            project.resources.consumption_ts = end
#            project.resources.consumption = conso[name]["total consumption"]
#            project.resources.consumption_raw = conso[name]
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
