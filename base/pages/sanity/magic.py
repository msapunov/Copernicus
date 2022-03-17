from datetime import datetime as dt, timezone
from base import db
from base.database.schema import Project
from base.classes import ProjectLog
from logging import debug

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def warn_expired(projects=None, config=None, deadline=None):
    """
    Check if end of life of a project resources within time interval from
    configuration option 'finish_notice' and if a warning has been already sent
    or not.
    Sent warning message if it's not done yet.
    :return: Nothing
    """
    now = dt.now().replace(tzinfo=timezone.utc)
    if not projects:
        projects = sane_projects()
    for rec in projects:
        finish = rec.resources.ttl
        warn = config[rec.type].finish_notice_dt
        if warn <= now < finish:
            debug("Expiring %s, %s" % (rec.name, finish.isoformat()))
            debug("Checking if warning has been send already")
            log = ProjectLog(rec)
            logs = log.after(warn).list()
            debug("List of log events found: %s" % logs)
            was_sent = list(filter(lambda x: "Expiring" in x.event, logs))
            debug("Events with word Expiring found: %s" % was_sent)
            if not was_sent:
                debug("Sending warning cause no previous warning events found")
                log.expire_warning()
    db.session.commit()
    return


def suspend_expired(projects=None, config=None, deadline=None):
    """
    Suspend expired projects. Check if ttl value of assigned resources has been
    expired if deadline is None. If deadline is set then ttl of assigned
    resources has been checked against provided deadline value
    @return: List. List of suspended projects
    """
    if not projects:
        projects = sane_projects()
    if not deadline and not config:
        deadline = dt.now().replace(tzinfo=timezone.utc)
    result = list(filter(lambda x: x.resources.ttl < deadline, projects))
    for project in result:
        project.active = False
        ProjectLog(project).expired()
#    db.session.commit()
    return result


def sane_projects():
    """
    Query DB for all the projects and return active projects with responsible
    and reference records.
    @return: List. List of sane projects
    """
    projects = Project.query.all()
    active = filter(lambda x: x.active, projects)
    responsible = filter(lambda x: x.responsible, active)
    sane = filter(lambda x: x.ref, responsible)
    return sane
