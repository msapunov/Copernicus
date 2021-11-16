from flask import current_app as app, flash, request, render_template
from datetime import datetime as dt, timezone
from tempfile import gettempdir, mkdtemp
from os import walk
from os.path import join as join_dir, exists
from base64 import b64encode
from recurrent.event_parser import RecurringEvent
from configparser import ConfigParser
from logging import error, debug, warning, critical
from pdfkit import from_string
from pathlib import Path
from string import ascii_letters, digits
from struct import unpack
from os import urandom
import locale

from flask_login import current_user
from base.pages import calculate_usage
from base.database.schema import Project
from base.pages import ssh_wrapper
from base.utils import is_text

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def show_configuration():
    """
    This function get tje instance path associated with the current app and
    creates a dictionary where each cfg file is a key, And the value is the
    content of that cfg file
    :return: Dictionary. Content of cfg file(s)
    """
    cfg = {}
    path = Path(app.instance_path)
    files = list(filter(lambda x: x.is_file(), path.iterdir()))
    text_files = list(filter(lambda x: is_text(x), files))
    config = ConfigParser(allow_no_value=True)
    for fichier in text_files:
        nom = str(fichier)
        try:
            config.read(nom, encoding="utf-8")
        except Exception as err:
            error("%s - not a configuration file: %s" % (nom, err))
            text_files.remove(fichier)
    for cfg_file in text_files:
        name = cfg_file.name
        if "ssh" in name:
            warning("Skipping ssh key: %s" % cfg_file)
            continue
        if name not in cfg:
            with open(str(cfg_file)) as fd:
                cfg[name] = fd.read()
    return cfg


def calculate_ttl(project):
    """
    Calculates time based on finish and duration options from project config.
    Primary usage is to set a date until which resources will be available
    :param project: Object. Copy of the Project object
    :return: Datetime.
    """
    now = dt.now().replace(tzinfo=timezone.utc)
    config = project_config()
    project_type = project.type.lower()
    end = config[project_type].get("finish_dt", None)
    duration = config[project_type].get("duration_dt", None)
    debug("Options values for Finish: %s and for Duration %s" % (end, duration))
    if end and duration:
        ttl = end if end > duration else duration
    elif duration:
        ttl = duration
    elif end:
        ttl = end
    else:
        error("Failed to calculate TTL no options found. Fallback to now()")
        ttl = now
    if now > ttl:
        critical("Calculated time value is in the past!")
        raise ValueError("Calculated time is in the past")
    debug("Calculated time value for %s: %s" % (project, ttl))
    return ttl


def generate_password(pass_len):
    """
    Create alphanumeric password of given length
    :param pass_len: Int. Number of symbols password must consist of
    :return: String. Password
    """
    symbols = ascii_letters + digits
    password = []
    for x in unpack('%dB' % (pass_len,), urandom(pass_len)):
        idx = round(x * len(symbols) / 256) - 1
        password.append(symbols[idx])
    return ''.join(password)


def generate_pdf(html, base):
    """
    Convert html document to PDF and return file path where the document is
    saved
    :param html: String. HTML document to convert
    :param base: String. Base template for name generation
    :return: String. Path to a PDF file
    """
    ts = str(dt.now().isoformat(sep="-")).replace(":", "-")
    name = "%s_%s.pdf" % (base, ts)
    name = name.replace("\\", "-").replace("/", "-")
    path = str(Path(get_tmpdir(app), name))
    debug("The resulting PDF will be saved to: %s" % path)
    pdf = from_string(html, path)
    debug("If PDF converted successfully: %s" % pdf)
    if not pdf:
        raise ValueError("Failed to convert a file to pdf")
    return path


def create_visa(record):
    """
    Generates html using as templates values from configuration file and
    provided record and then convert it to pdf files
    :param record: Object. Instance of project register class
    :return: List. List of resulting files
    """
    config = project_config()
    project_type = record.type.lower()
    end = config[project_type].get("finish_dt", None)
    duration = config[project_type].get("duration_dt", None)
    if end and duration:
        ttl = end if end > duration else duration
    elif duration:
        ttl = duration
    elif end:
        ttl = end
    else:
        ttl = None
    record.dt = dt.now().strftime("%d/%m/%Y")
    record.ttl = ttl.strftime("%d %B %Y")
    record.signature = file_as_string("signature.png")
    record.base_url = request.url_root
    loc = app.config.get("LOCALE", "C.UTF-8")
    locale.setlocale(locale.LC_ALL, loc)
    path = []
    for i in config[project_type].get("visa", []):
        html = render_template("%s" % i, data=record)
        path.append(generate_pdf(html, "%s_%s" % (record.project_id(), i)))
    return path


def project_parse_cfg_options(cfg, section):
    """
    Parse project configuration. Use of recurrent lib to parse fuzzy time values
    :param cfg: Configuration object
    :param section: Section in the configuration object, i.e. project type
    :return: Dictionary. Keys are: "duration_text", "duration_dt", "extendable",
            "finish_text", "finish_dt", "cpu", "finish_notice_text", "acl",
            "finish_notice_dt", "transform", "description", "evaluation_text",
            "evaluation_dt", "evaluation_notice_text", "evaluation_notice_dt"
    """
    r = RecurringEvent()
    cpu = cfg.getint(section, "cpu", fallback=None)
    description = cfg.get(section, "description", fallback=None)
    duration = cfg.get(section, "duration", fallback=None)
    if duration:
        duration_dt = r.parse(duration).replace(tzinfo=timezone.utc)
    else:
        duration_dt = None
    end = cfg.get(section, "finish_date", fallback=None)
    if end:
        end_dt = r.parse(end).replace(tzinfo=timezone.utc)
    else:
        end_dt = None
    end_notice = cfg.get(section, "finish_notice", fallback=None)
    if end_notice and end_dt:
        tmp = RecurringEvent(end_dt).parse(end_notice)
        end_notice_dt = tmp.replace(tzinfo=timezone.utc)
    else:
        end_notice_dt = None
    trans = cfg.get(section, "transform", fallback=None)
    if trans:
        transform = list(map(lambda x: x.strip(), trans.split(",")))
    else:
        transform = []
    acl = cfg.get(section, "acl", fallback=[])
    if acl:
        acl = list(map(lambda x: x.strip(), acl.split(",")))
    acl.append("admin")

    eva = cfg.get(section, "evaluation_date", fallback=None)
    if eva:
        evaluation = list(map(lambda x: x.strip(), eva.split(",")))
    else:
        evaluation = []
    if evaluation:
        tmp = list(map(lambda x: r.parse(x), evaluation))
        eva_dt = list(map(lambda x: x.replace(tzinfo=timezone.utc), tmp))
    else:
        eva_dt = None

    eva_notice = cfg.get(section, "evaluation_notice", fallback=None)
    if eva_notice and eva_dt:
        tmp = list(map(lambda x: RecurringEvent(x).parse(eva_notice), eva_dt))
        eva_text_dt = list(map(lambda x: x.replace(tzinfo=timezone.utc), tmp))
    else:
        eva_text_dt = None
    extendable = cfg.get(section, "extendable", fallback=False)

    visa_names = cfg.get(section, "visa", fallback=None)
    if visa_names:
        visa = list(map(lambda x: x.strip(), visa_names.split(",")))
    else:
        visa = []
    return {"duration_text": duration, "duration_dt": duration_dt, "acl": acl,
            "finish_text": end, "finish_dt": end_dt, "cpu": cpu, "visa": visa,
            "finish_notice_text": end_notice, "extendable": extendable,
            "finish_notice_dt": end_notice_dt,
            "transform": transform, "description": description,
            "evaluation_text": evaluation, "evaluation_dt": eva_dt,
            "evaluation_notice_text": eva_notice,
            "evaluation_notice_dt": eva_text_dt}


def project_config():
    """
    Parsing file defined in PROJECT_CONFIG option of main application config.
    Otherwise trying to find project.cfg file
    :return: Dict. Each project type (i.e. subsection in config file) having
    options returned by project_parse_cfg_options function
    """
    result = {}
    cfg_file = app.config.get("PROJECT_CONFIG", "project.cfg")
    cfg_path = join_dir(app.instance_path, cfg_file)
    if not exists(cfg_path):
        warning("Projects configuration file doesn't exists. Using defaults")
        return result
    cfg = ConfigParser()
    cfg.read(cfg_path)
    projects = cfg.sections()
    for project in projects:
        name = project.lower()
        result[name] = project_parse_cfg_options(cfg, project)
    debug("Project configuration: %s" % result)
    return result


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
        date = dt.strptime(info[1].strip(), "%Y-%m-%dT%H:%M:%S")
        node = info[2].strip()
        stat = info[3].strip()
        result.append({
            "date": date.strftime("%Y-%m-%d %X %Z"),
            "date_full": date.strftime("%c"),
            "reason": reason,
            "status": stat,
            "node": node})
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
            conso = slurm[name]["total consumption"]
            project.consumed = project.resources.consumption + conso
        cpu = project.resources.cpu
        project.consumed_use = calculate_usage(project.consumed, cpu)
    return projects


def projects_consumption_new(projects):
    projects = list(filter(lambda x: project_check_resources(x), projects))
    result = {}
    for project in projects:
        if not project.resources.consumption_ts:
            start = project.resources.created
        else:
            start = project.resources.consumption_ts
        if start not in result:
            result[start] = []
        result[start].append(project.get_name())
    conso = {}
    for key, value in result.items():
        name = ",".join(value)
        start = key.strftime("%Y-%m-%dT%H:%M")
        finish = dt.now().strftime("%Y-%m-%dT%H:%M")
        slurm_raw, cmd = slurm_consumption_raw(name, start, finish)
        conso.update(slurm_parse_project_conso(slurm_raw))
    for project in projects:
        name = project.get_name()
        if name in conso.keys():
            new_conso = conso[name]["total consumption"]
        else:
            new_conso = 0
        if project.resources.consumption and new_conso:
            project.consumed = project.resources.consumption + new_conso
        else:
            project.consumed = project.resources.consumption
        cpu = project.resources.cpu
        project.consumed_use = calculate_usage(project.consumed, cpu)
    return projects


def project_get_info(every=None, user_is_responsible=None, usage=True):
    if every:
        projects = Project.query.all()
    else:
        if user_is_responsible:
            projects = Project.query.filter_by(responsible=current_user).all()
        else:
            projects = current_user.project
    if not projects:
        if every:
            raise ValueError("No projects found!")
        else:
            raise ValueError("No projects found for user '%s'" %
                             current_user.full())
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
            items = item.strip().split("|")
        else:
            items = item.strip().split("||")
        name = items[0].strip()
        if len(items) == 3:
            login = items[1].strip()
        else:
            login = None
        conso = int(items[-1].strip())
        if name not in output:
            output[name] = {}
        if login:
            output[name][login] = conso
        else:
            output[name]["total consumption"] = conso
        debug("SLURM account '%s' consumption: %s" % (name, output))
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
    :param project: Object. Instance of a project object
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
    raw, cmd = slurm_consumption_raw(name, start, end)
    if not raw:
        debug("Returning 0")
        return 0
    result = slurm_parse_project_conso(raw)
    if name not in result:
        debug("Failed to find consumption of %s in raw data: %s" % (name, raw))
        return 0
    return result[name]["total consumption"]


def resources_group_by_created(projects):
    """
    Grouping projects by resource created time
    :param projects: List or String. List of projects is str converts to list
    :return: Dict where keys are created time and value is the list of
    project records
    """
    if not isinstance(projects, list):
        projects = [projects]
    dates = {}
    for project in projects:
        if not project.resources:
            error("No resources attached to project", project)
            continue
        start = project.resources.created.strftime("%Y-%m-%dT%H:%M")
        if start not in dates:
            dates[start] = []
        dates[start].append(project)
    return dates


def file_as_string(name):
    """
    Encoding a file to Base64 format
    :param name: Name of a file to encode
    :return: String. String in Base64 format
    """
    img_path = join_dir(app.instance_path, name)
    if not exists(img_path):
        raise ValueError("File %s doesn't exists" % img_path)
    with open(img_path, "rb") as img_file:
        return b64encode(img_file.read()).decode("ascii")


def get_tmpdir(application):
    """
    Check if application specific directory has been already created and create
    said directory if it doesn't exists. If directory started with prefix is
    already there the function returns first element from the directory list
    :param application: Current flask application
    :return: String. Name of the temporary application specific directory.
    """
    prefix = get_tmpdir_prefix(application)
    dirs = [x[0] for x in walk(gettempdir())]
    exists = list(filter(lambda x: True if prefix in x else False, dirs))
    if exists:
        dir_name = exists[0]
        debug("Found existing directory: %s" % dir_name)
    else:
        dir_name = mkdtemp(prefix=prefix)
        debug("Temporary directory created: %s" % dir_name)
    return dir_name


def get_tmpdir_prefix(application):
    """
    Construct the prefix for the temporary directory based on SECRET_KEY
    parameter from configuration file
    :param application: Current application
    :return: String
    """
    return "%s_copernicus_" % application.config.get("SECRET_KEY", "XXX")[0:3]


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
    debug("File name from incoming request: %s" % file.filename)
    if not file_name:
        file_name = file.filename
    else:
        if "." not in file_name and "." not in file.filename:
            file_name = "%s.unknown" % file_name
        elif "." not in file_name and "." in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            debug("Deducted file extensions: %s" % ext)
            file_name = "%s.%s" % (file_name, ext)
    name = join_dir(directory, file_name)
    debug("Saving file from incoming request to: %s" % name)
    file.save(name)
    return {"saved_name": file_name, "incoming_name": file.filename}


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
