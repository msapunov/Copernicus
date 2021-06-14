from flask import current_app as app, flash
from datetime import datetime as dt
from unicodedata import normalize
from tempfile import gettempdir, mkdtemp
from os import walk
from os.path import join as join_dir, exists
from base64 import b64encode
import logging as log
from flask_login import current_user
from base import db
from base.pages import (
    check_int,
    check_str,
    check_json,
    calculate_ttl,
    calculate_usage)
from base.database.schema import Resources, Project
from base.classes import Extensions
from base.pages import ssh_wrapper
from logging import debug, error


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def slurm_nodes_status():
    """
    Function issued a sinfo command to get the reasons for down, drained, fail
    or failing state of a node.
    Command is sinfo -R --format='%100E|%19H|%30N|%t'
    Output to parse: Not responding |2020-07-25T22:39:23|skylake106|down*
    :return: dictionary where nodes names are the keys
    """
    cmd = ["sinfo", "-R", "--format='%100E|%19H|%30N|%t'"]
    run = " ".join(cmd)
    data, err = ssh_wrapper(run)
    if not data:
        debug("No data received, returning empty dictionary")
        return {}
    result = []
    for line in data:
        if ("REASON" or "TIMESTAMP" or "NODELIST" or "STATE") in line:
            debug("Skipping headline: %s" % line)
            continue
        info = line.split("|")
        if len(info) != 4:
            error("Wrong format: %s" % line)
            continue
        reason = info[0].strip()
        date = info[1].replace("T"," ").strip()
        node = info[2].strip()
        stat = info[3].strip()
        result.append({
            "date": date, "reason": reason, "status": stat, "node": node})
    return result


def project_check_resources(project):
    err = []
    if not project.resources:
        err.append("No resources attached to project %s" % project)
    if not project.resources.cpu:
        err.append("No CPU set in project resources for %s" % project)
    if err:
        error("; ".join(err))
        flash("<br>".join(err))
        return False
    return True


def projects_consumption(projects):
    projects = list(filter(lambda x: project_check_resources(x), projects))
    result = {}
    for project in projects:
        if not project.resources.consumption_ts:
            project.resources.consumption_ts = dt.now(tz=None).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0)
        if project.resources.consumption_ts not in result:
            result[project.resources.consumption_ts] = []
        result[project.resources.consumption_ts].append(project.get_name())
    slurm = {}
    for key, value in result.items():
        name = ",".join(value)
        start = key.strftime("%Y-%m-%dT%H:%M")
        finish = dt.now().strftime("%Y-%m-%dT%H:%M")
        slurm_raw, cmd = slurm_consumption_raw(name, start, finish)
        slurm.update(slurm_parse_project_conso(slurm_raw))
    for project in projects:
        name = project.get_name()
        if name not in slurm.keys():
            project.consumed = project.resources.consumption
        else:
            project.consumed = project.resources.consumption + slurm[name]
        cpu = project.resources.cpu
        project.consumed_use = calculate_usage(project.consumed, cpu)
    return projects


def project_get_info(every=None, user_is_responsible=None, usage=True):
    if every:
        projects = Project.query.all()
    else:
        pids = current_user.project_ids()
        query = Project.query.filter(Project.id.in_(pids))
        if user_is_responsible:
            projects = query.filter(Project.responsible == current_user).all()
        else:
            projects = query.all()
    if not projects:
        if every:
            raise ValueError("No projects found!")
        else:
            raise ValueError("No projects found for user '%s'" %
                             current_user.login)
    if not usage:
        return projects
    return projects_consumption(projects)


def slurm_parse_project_conso(slurm_raw_output):
    """
    Parsing the output of sreport command looking for account, not user,
    consumption. Normally it's the line with || in it
    :param slurm_raw_output: list of lines produced by sreport command
    :return: dictionary, where project name is the key, consumption is the value
    """
    output = {}
    if not slurm_raw_output:
        return output
    for item in slurm_raw_output:
        if "||" not in item:  # skip user consumption
            continue
        items = item.strip().split("||")
        project_name = items[0].strip()
        conso = int(items[1].strip())
        debug("SLURM account '%s' consumption: %s" % (project_name, conso))
        output[project_name] = conso
    return output


def slurm_consumption_raw(name, start, finish):
    """
    Build a remote query to SLURM DB to obtain a project's CPU consumption.
    :param name: Account name, in out case it's a project's name
    :param start: starting date for accounting query
    :param finish: end date for accounting query should be now by default
    :return: Raw result of sreport command
    """
    cmd = ["sreport", "cluster", "AccountUtilizationByUser", "-t", "hours"]
    cmd += ["-nP", "format=Account,Login,Used", "Accounts=%s" % name]
    cmd += ["start=%s" % start, "end=%s" % finish]
    run = " ".join(cmd)
    data, err = ssh_wrapper(run)
    if not data:
        debug("No data received, nothing to return")
        return None, run
    debug("Got raw consumption values for project %s: %s" % (name, data))
    return data, run


def resource_consumption(project, start=None, end=None):
    """
    Parse the raw output of scontrol command to get a project's consumption
    :param name: name of the project
    :param start: starting date for accounting query
    :param end: end date for accounting query should be now by default
    :return: Return project's consumption as integer
    """
    name = project.get_name()
    if not name:
        error("Project %s has no name!" % project)
        return 0
    if not start:
        start = project.resources.created
    start = start.strftime("%Y-%m-%d-%H:%M:%S")
    if not end:
        end = dt.now()
    end = end.strftime("%Y-%m-%d-%H:%M:%S")
    raw = slurm_consumption_raw(name, start, end)
    if not raw:
        debug("Returning 0")
        return 0
    result = slurm_parse_project_conso(raw)
    if name not in result:
        debug("Failed to find consumption of %s in raw data: %s" % (name, raw))
        return 0
    return result[name]


def resources_group_by_date(projects):
    """
    Grouping projects by last update time. If no last update time found,
    resources creation date is used
    :param projects: List of projects
    :return: Dict where keys are last update time and value is the list of
    project names
    """
    if not isinstance(projects, list):
        projects = [projects]
    dates = {}
    for project in projects:
        if not project.resources:
            error("No resources attached to project", project)
            continue
        if project.resources.consumption_ts:
            start = project.resources.consumption_ts.strftime("%Y-%m-%dT%H:%M")
        else:
            start = project.resources.created.strftime("%Y-%m-%dT%H:%M")
        if start not in dates:
            dates[start] = []
        dates[start].append(project)
    return dates


def resources_update_statistics(pid=None, force=False):
    """
    Updates the total consumption of the projects with valid resources.
    :param pid: update just a single project with a given pid
    :param force: update all registered projects
    :return: HTTP 200 OK
    """
    if pid:
        projects = [Project.query.filter_by(id=pid).first()]
    else:
        projects = Project.query.all()
    end = dt.now(tz=None).replace(microsecond=0)
    if not force:
        resources = filter(lambda x: x.resources, projects)
        projects = list(filter(lambda x: x.resources.ttl > end, resources))

    dates = resources_group_by_date(projects)
    for start, value in dates.items():
        names = list(filter(lambda x: True if x.name else False, value))
        accounts = ",".join(list(map(lambda x: x.name, names)))
        result, cmd = slurm_consumption_raw(accounts, start, end)
        if not result:
            continue
        conso_by_project = slurm_parse_project_conso(result)
        for project in value:
            name = project.name
            out = list(filter(lambda x: True if name in x else False, result))
            out.append("\n").append(cmd)
            project.resources.consumption_raw = "".join(out)
            project.resources.consumption_ts = end
            if name in conso_by_project:
                conso = conso_by_project[name]
            else:
                conso = 0
            previous = project.resources.consumption
            if previous and previous > 0:
                project.resources.consumption = previous + conso
            else:
                project.resources.consumption = conso

#            if name not in conso_by_project:
#                conso = 0
#            else:
#                conso = conso_by_project[project]
#            if

#    for project in projects:
#        project.resources.consumption = resource_consumption(project, end=end)
#        project.resources.consumption_ts = end
#    if db.session.dirty:
#        db.session.commit()
    return "", 200


def ignore_extension(eid):
    return Extensions(eid).reject("Extension request has been ignored")


def reject_extension(eid):
    data = check_json()
    note = check_str(data["comment"])
    if not note:
        raise ValueError("Please indicate reason for rejection extension")
    record = Extensions(eid)
    return record.reject(note)


def create_resource(project, cpu):
    return Resources(
        approve=current_user,
        valid=True,
        cpu=cpu,
        type=project.type,
        project=project.get_name(),
        ttl=calculate_ttl(project),
        treated=False
    )


def get_arguments():
    data = check_json()
    eid = check_int(data["eid"])
    note = check_str(data["comment"])
    ext = check_str(data["extension"]).lower()
    debug("Extension flag is set to: %s" % ext)
    extension = False
    if ext == "true":
        extension = True
    cpu = check_int(data["cpu"])
    debug("Got CPU value: %s" % cpu)
    if cpu < 0:
        raise ValueError("CPU value is absent, or a negative value!")

    return eid, note, cpu, extension


def image_string(name):
    img_path = join_dir(app.instance_path, name)
    if not exists(img_path):
        raise ValueError("Image %s doesn't exists" % img_path)
    with open(img_path, "rb") as img_file:
        return b64encode(img_file.read()).decode("ascii")


def get_tmpdir(app):
    """
    Check if application specific directory has been already created and create
    said directory if it doesn't exists. If directory started with prefix is
    already there the function returns first element from the directory list
    :param app: Current flask application
    :return: String. Name of the temporary application specific directory.
    """
    prefix = get_tmpdir_prefix(app)
    dirs = [x[0] for x in walk(gettempdir())]
    exists = list(filter(lambda x: True if prefix in x else False, dirs))
    if exists:
        dir_name = exists[0]
        log.debug("Found existing directory: %s" % dir_name)
    else:
        dir_name = mkdtemp(prefix=prefix)
        log.debug("Temporary directory created: %s" % dir_name)
    return dir_name


def get_tmpdir_prefix(app):
    """
    Construct the prefix for the temporary directory based on SECRET_KEY
    parameter from configuration file
    :param app: Current application
    :return: String
    """
    return "%s_copernicus_" % app.config.get("SECRET_KEY", "XXX")[0:3]


def save_file(req, directory, file_name=False):
    """
    Saving incoming file HTTP request to provided directory under original or
    provided filename
    :param req: Incoming file HTTP request
    :param directory: Directory where to save the file from incoming request
    :param file_name: Default is False. By default the file is saved under name
    extracted from file http request.
    :return: Dictionary
    """
    if "file" not in req.files:
        raise ValueError("File expected!")
    file = req.files["file"]
    if file.filename == '':
        raise ValueError("No selected file")
    log.debug("File name from incoming request: %s" % file.filename)
    if not file_name:
        file_name = file.filename
    else:
        if "." not in file_name and "." not in file.filename:
            file_name = "%s.unknown" % file_name
        elif "." not in file_name and "." in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            log.debug("Deducted file extensions: %s" % ext)
            file_name = "%s.%s" % (file_name, ext)
    name = join_dir(directory, file_name)
    log.debug("Saving file from incoming request to: %s" % name)
    file.save(name)
    return {"saved_name": file_name, "incoming_name": file.filename}


def normalize_word(word):
    word = word.replace("'", "")
    word = normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")
    return word


"""
Bytes-to-human / human-to-bytes converter.
Based on: http://goo.gl/kTQMs
Working with Python 2.x and 3.x.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""

# see: http://goo.gl/kTQMs
SYMBOLS = {
    'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}


def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on format.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs

      >>> bytes2human(0)
      '0.0 B'
      >>> bytes2human(0.9)
      '0.0 B'
      >>> bytes2human(1)
      '1.0 B'
      >>> bytes2human(1.9)
      '1.0 B'
      >>> bytes2human(1024)
      '1.0 K'
      >>> bytes2human(1048576)
      '1.0 M'
      >>> bytes2human(1099511627776127398123789121)
      '909.5 Y'

      >>> bytes2human(9856, symbols="customary")
      '9.6 K'
      >>> bytes2human(9856, symbols="customary_ext")
      '9.6 kilo'
      >>> bytes2human(9856, symbols="iec")
      '9.6 Ki'
      >>> bytes2human(9856, symbols="iec_ext")
      '9.6 kibi'

      >>> bytes2human(10000, "%(value).1f %(symbol)s/sec")
      '9.8 K/sec'

      >>> # precision can be adjusted by playing with %f operator
      >>> bytes2human(10000, format="%(value).5f %(symbol)s")
      '9.76562 K'
    """
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)

def accounting_start():
    DAY = app.config["ACC_START_DAY"]
    MONTH = app.config["ACC_START_MONTH"]

    now = dt.now()
    year = now.year
    month = now.month
    day = now.day
    if (month < MONTH) or ((month == MONTH) and (day <= DAY)):
        year -= 1
    year -= 2000
    mth = str(MONTH).zfill(2)
    day = str(DAY).zfill(2)
    return "%s/%s/%s-00:00" % (mth, day, year)
