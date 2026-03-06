from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
from paramiko import RSAKey, ECDSAKey, Ed25519Key
from paramiko import SSHException, BadHostKeyException
from flask import current_app as app, flash, request, render_template, g
from time import mktime
from datetime import datetime as dt, timezone
from dateparser import parse as dt_parse
from parsedatetime import Calendar
from dateutil.relativedelta import relativedelta
from os.path import join as join_dir, exists
from base64 import b64encode
from webdav3.client import Client
from weasyprint import HTML
from configparser import ConfigParser
from logging import error, debug, warning, critical
from pathlib import Path, PurePosixPath
from string import ascii_letters, digits
from struct import unpack
from subprocess import check_output, STDOUT, CalledProcessError
from os import urandom
from re import compile, match
from babel import Locale
from babel.dates import format_date
import locale


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def get_field_value(form, name):
    field = form._fields.get(name)
    if not field:
        return None
    value = field.data
    if isinstance(value, str):
        value = value.strip()
        if not value:  # empty after stripping
            return None
        if len(value) > 1028:
            return None
        if any(ord(c) < 32 and c not in ("\n", "\r", "\t") for c in value):
            return None
    return value


def upload_to_cloud(remote_dir, path):
    """
    Function which uploads a file to OwnCloud instance
    :param remote_dir: String. Name of the remote directory to store files in.
    :param path: String. Path to file to upload.
    :return: None. Does not return anything — its return value should be None
    """
    local = Path(path)
    if not local.exists() or not local.is_file():
        raise ValueError(f"'{path}' doesn't exists or not a file")
    url = app.config.get("OWN_CLOUD_URL", None)
    login = app.config.get("OWN_CLOUD_LOGIN", None)
    password = app.config.get("OWN_CLOUD_PASSWORD", None)
    if not all([url, login, password]):
        raise ValueError("Missing WebDAV configuration: URL, login, or password.")
    options = {
        "webdav_hostname": url,
        "webdav_login": login,
        "webdav_password": password
    }
    client = Client(options)
    remote_dir = "/" + remote_dir.strip("/")
    if not client.check(remote_dir):
        raise ValueError(f"Remote directory '{remote_dir}' does not exists")
    remote = str(PurePosixPath(remote_dir) / local.name)
    debug(f"Uploading file '{path}' to '{remote}'")
    client.upload_sync(remote_path=remote, local_path=local.as_posix())


def process_register_user(user_as_string):
    name, surname, email, login = None, None, None, None
    parts = user_as_string.split(";")
    for i in parts:
        if "First Name:" in i:
            name = i.replace("First Name:", "").strip()
        elif "Last Name:" in i:
            surname = i.replace("Last Name:", "").strip()
        elif "E-mail:" in i:
            email = i.replace("E-mail:", "").strip()
        elif "Login:" in i:
            login = i.replace("Login:", "").strip()
        else:
            continue
    return name, surname, email, login


def ssh_public(key_file):
    argz = ["ssh-keygen", "-l", "-f", key_file]
    cmd = " ".join(argz)
    debug("Executing command: %s" % cmd)
    result = False
    err = False
    try:
        result = check_output(argz, stderr=STDOUT, universal_newlines=True)
    except CalledProcessError as e:
        err = "Error while executing the command '%s': %s" % (cmd, e.output)
    except Exception as e:
        err = "Exception while executing command '%s': %s" % (cmd, e)
    return result, err


def ssh_wrapper(cmd, host=None):
    debug("ssh_wrapper(%s)" % cmd)
    if not host:
        host = app.config["SSH_SERVER"]
    login = app.config["SSH_USERNAME"]
    key_file = app.config["SSH_KEY"]
    for key_type in (RSAKey, ECDSAKey, Ed25519Key):
        try:
            key = key_type.from_private_key_file(key_file)
            break
        except SSHException:
            continue
    else:
        raise ValueError("Unsupported or invalid private key")
    timeout = app.config.get("SSH_TIMEOUT", 60)
    port = app.config.get("SSH_PORT", 22)
    debug("Connecting to %s:%s with username %s and key %s" %
          (host, port, login, key_file))
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        client.connect(host, username=login, pkey=key, timeout=timeout,
                       port=port)
    except AuthenticationException:
        error("Failed to connect to %s" % host)
        client.close()
        return [], []
    except BadHostKeyException:
        error("Host key given by %s did not match with expected" % host)
        client.close()
        return [], []
    except Exception as e:
        error("Failed to establish a connection to %s due following error: %s"
              % (host, e))
        client.close()
        return [], []
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.readlines()
    errors = stderr.readlines()
    client.close()
    debug("Out: %s" % output)
    debug("Err: %s" % errors)
    return output, errors


def show_configuration():
    """
    This function get the instance path associated with the current app and
    creates a dictionary where each cfg file is a key, And the value is the
    content of that cfg file
    :return: Dictionary. Content of cfg file(s)
    """
    cfg = {}
    path = Path(app.instance_path)
    files = list(filter(lambda x: x.is_file(), path.iterdir()))
    config = ConfigParser(allow_no_value=True)
    for file in files:
        nom = str(file)
        print("File name: %s" % nom)
        try:
            with open(nom) as fd:
                text = fd.read()
        except UnicodeDecodeError as err:
            error("%s - not a text file: %s" % (nom, err))
            continue
        try:
            config.read_string(text, source=nom)
        except Exception as err:
            error("%s - not a configuration file: %s" % (nom, err))
            continue
        cfg[file.name] = text
    return cfg


def calculate_ttl(project):
    """
    Calculates time based on finish and duration options from project config.
    Primary usage is to set a date until which resources will be available
    :param project: Object. Copy of the Project object
    :return: Datetime.
    """
    candidates = []
    now = dt.now().replace(tzinfo=timezone.utc)
    duration = get_duration(project)
    if duration:
        candidates.append(now + duration)
    finish = get_finish(project)
    if finish:
        candidates.append(finish)
    if not candidates:
        raise ValueError(f"No duration or finish date found for {project}!")
    else:
        ttl = max(candidates)
    if now > ttl:
        error(f"Calculated finish time {ttl} is in the past! Add 1 year")
        ttl = ttl + relativedelta(years=1)
    debug(f"Calculated TTL for project {project}: {ttl}")
    return ttl


def full_name(name, surname):
    """
    Build a properly capitalized full name from name and surname,
    preserving separators like dash, apostrophe, space, slash, comma, or dot.

    Each part of the name separated by common punctuation is capitalized,
    and the separators are preserved in the final result.

    :param name: First name (can be None/False)
    :param surname: Surname (can be None/False)
    :return: Full name string with proper capitalization
    """
    name_parts = compile(r"([/.,'\s-])")

    def capital(value):
        if not value:
            return ""
        parts = name_parts.split(str(value))
        return "".join(p.capitalize() if not name_parts.match(p) else p
                       for p in parts)

    normalized_parts = [capital(n) for n in (name, surname) if n]
    return " ".join(normalized_parts)


def generate_password(pass_len=16):
    """
    Create alphanumeric password of given length
    :param pass_len: Int. Number of symbols password must consist of.
    Default length is 16 symbols
    :return: String. Password
    """
    symbols = ascii_letters + digits + "!@#$%^&*"
    password = []
    for x in unpack('%dB' % (pass_len,), urandom(pass_len)):
        idx = round(x * len(symbols) / 256) - 1
        password.append(symbols[idx])
    return ''.join(password)


def write_pdf(html, name):
    """
    Convert html document to PDF and return file path where the document is
    saved
    :param html: String. HTML document to convert
    :param name: String. Name of the resulting PDF document
    :return: String. Path to a PDF file
    """
    if not name.endswith(".pdf"):
        name = name + ".pdf"
    path = Path(app.get_tmpdir(), name)
    debug("The resulting PDF will be saved to: %s" % path)
    try:
        HTML(string=html, base_url=path.parent.as_posix()).write_pdf(path)
    except TypeError:
        try:
            pdf = HTML(string=html, base_url=path.parent.as_posix()).write_pdf()
            with open(path, "wb") as f:
                f.write(pdf)
        except Exception as e:
            raise ValueError(f"Error during PDF generation: {e}")
    except Exception as e:
        raise ValueError(f"Error during PDF generation: {e}")
    debug("PDF converted and saved successfully")
    return path


def create_visa(record, signature="signature.png"):
    """
    Generates html using as templates values from configuration file and
    provided record and then convert it to pdf files
    :param record: Object. Instance of project register class
    :return: List. List of resulting files
    """
    cfg = project_config()
    project_type = record.type.lower()
    if project_type not in cfg:
        raise ValueError("Project type '%s' not in config" % project_type)
    else:
        config = cfg[project_type]
    end = config.get("finish_dt", None)
    duration = config.get("duration_dt", None)
    if end and duration:
        ttl = end if end > duration else duration
    elif duration:
        ttl = duration
    elif end:
        ttl = end
    else:
        raise ValueError("Failed to calculate project duration")
    record.signature = file_as_string("signature.png")
    record.base_url = request.url_root
    path = []
    project_id = record.project_id()
    date = dt.now().strftime("%Y-%m-%d-%H-%M-%S")
    for loc, name in config.get("visa", {}).items():
        try:
            record.dt = format_date(dt.now(), format='short', locale=loc)
            record.ttl = format_date(ttl, format='long', locale=loc)
            lang = Locale.parse(loc).get_language_name().lower()
        except Exception as e:
            error(f"Invalid locale '{loc}': {e}. Skipping formatting.")
            continue
        html = render_template("%s" % name, data=record)
        path.append(write_pdf(html, f"{project_id}-{lang}-{date}.pdf"))
    return path


def parse_moment(value):
    """
    Parses a human-readable date string and returns a datetime object at midnight UTC.

    :param value: str, human-readable date (e.g., "1st Feb", "15 November")
    :return: datetime at midnight UTC, or None if parsing fails
    """
    # noinspection PyTypeChecker
    moment = dt_parse(value, settings={"TIMEZONE": "UTC",
                                       "PREFER_DATES_FROM": "current_period",
                                       "NORMALIZE": True,
                                       "RETURN_AS_TIMEZONE_AWARE": True})
    if not moment:
        error(f"Failed to parse value: {value}")
        return None
    debug(f"Parsed value '{value}' as {moment.isoformat()}")
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def get_finish(project):
    """
    Calculates the project's allocation finish datetime considering:
      - finish value
      - renewal as extension windows
      - year-wrap scenarios
    Returns a datetime object representing the actual finish date.

    :param project: document instance with `type` attribute
    :return: datetime at midnight UTC
    """
    now = dt.now(timezone.utc)
    cfg = g.project_config.get(project.type, {})
    finish_raw = cfg.get("finish", None)
    debug(f"Got configuration value for finish option: {finish_raw}")
    if not finish_raw:
        return None
    finish = parse_moment(finish_raw)
    if not finish:
        return None
    update_raw = cfg.get("renew_start", None)
    debug(f"Got configuration value for renew_start option: {update_raw}")
    if not update_raw:
        return finish
    update = parse_moment(update_raw)
    if not update:
        return finish
    debug("Renewal applies to the same cycle as finish")
    if update > finish:
        update = update - relativedelta(years=1)
    in_window = update <= now <= finish
    debug(f"Project in renewal window: {in_window}")
    if in_window:
        debug("Calculated TTL finishing next year")
        return finish + relativedelta(years=1)
    debug("Calculated TTL finishing this year")
    return finish


def get_duration(project):
    cfg = g.project_config
    duration = cfg.get(project.type, {}).get("duration", None)
    debug(f"Got value '{duration}' for duration from config for {project}")
    if not duration:
        return None
    duration = duration.strip("'")
    m = match(r"(\d+)\s*(day|week|month|year)s?", duration)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return {
        "day": relativedelta(days=n),
        "week": relativedelta(weeks=n),
        "month": relativedelta(months=n),
        "year": relativedelta(years=n)
    }[unit]


def parse_value(key, value, cal):
    value = value.strip()
    lower = value.lower()
    extra = {}

    bool_true = {"true", "yes", "1", "on"}
    bool_false = {"false", "no", "0", "off"}
    always_string = {"description"}
    if key in always_string:
        return value, extra
    if lower in bool_true:
        return True, extra
    if lower in bool_false:
        return False, extra

    try:
        return int(value), extra
    except ValueError:
        pass
    try:
        return float(value), extra
    except ValueError:
        pass

    if "," in value:
        items = []
        for v in value.split(","):
            parsed_item, item_extra = parse_value(key, v.strip(), cal)
            items.append(parsed_item)
            if item_extra:
                extra.update(item_extra)
        return items, extra
    return value, extra


def project_config_options(cfg, section):
    """
    Parse project configuration from config object.
    Use of parsedatetime lib to parse fuzzy time values
    :param cfg: Configuration object
    :param section: Section in the configuration object, i.e. project type
    :return: Dictionary. Keys are: "duration_text", "duration_dt", "extendable",
            "finish_text", "finish_dt", "cpu", "finish_notice_text", "acl",
            "finish_notice_dt", "transform", "description", "evaluation_text",
            "evaluation_dt", "evaluation_notice_text", "evaluation_notice_dt",
            "finish_report"
    """
    cal = Calendar()

    def parse_list(text):
        return [x.strip() for x in text.split(",")] if text else []

    def parse_datetime(text):
        if not text:
            return None
        if "," in text:
            parts = [x.strip() for x in text.split(",")]
            return [parse_datetime(x) for x in parts]
        date, status = cal.parse(text)
        if status == 0:
            return None
        return dt.fromtimestamp(mktime(date), timezone.utc)

    visa = {}
    for key, val in cfg.items(section):
        if "visa" in key:
            if "." in key:
                prefix, lang = key.split('.', 1)
            else:
                lang = "en_US"  # fallback locale
            visa[lang] = val

    return {
        "description": cfg.get(section, "description", fallback=None),
        "cpu": cfg.getint(section, "cpu", fallback=None),
        "transform": parse_list(cfg.get(section, "transform", fallback="")),
        "acl": parse_list(cfg.get(section, "acl", fallback="")) + ["admin"],
        "extendable": cfg.getboolean(section, "extendable", fallback=False),
        "suspend": cfg.getboolean(section, "suspend", fallback=True),

        "duration_text": cfg.get(section, "duration", fallback=None),
        "duration_dt": parse_datetime(cfg.get(section, "duration", fallback=None)),

        "finish_text": cfg.get(section, "finish", fallback=None),
        "finish_dt": parse_datetime(cfg.get(section, "finish", fallback=None)),

        "finish_notice_text": cfg.get(section, "finish_notice", fallback=None),
        "finish_notice_dt": parse_datetime(cfg.get(section, "finish_notice", fallback=None)),

        "finish_report_text": cfg.get(section, "finish_report", fallback=None),
        "finish_report_dt": parse_datetime(cfg.get(section, "finish_report", fallback=None)),

        "evaluation_text": parse_list(cfg.get(section, "evaluation_date", fallback="")),
        "evaluation_dt": parse_datetime(cfg.get(section, "evaluation_date", fallback="")),

        "evaluation_notice_text": cfg.get(section, "evaluation_notice", fallback=None),
        "evaluation_notice_dt": parse_datetime(cfg.get(section, "evaluation_notice", fallback=None)),

        "visa": visa
    }


def load_config():
    config = {}
    cfg_file = app.config.get("PROJECT_CONFIG", "project.cfg")
    cfg_path = join_dir(app.instance_path, cfg_file)
    if not exists(cfg_path):
        warning("Projects configuration file doesn't exists. Using defaults")
        return config
    cfg = ConfigParser()
    cfg.optionxform = str
    cfg.read(cfg_path)
    cal = Calendar()
    for section in cfg.sections():
        section_data = {}
        for key, raw_value in cfg.items(section):
            value, extra = parse_value(key, raw_value, cal)
            section_data[key] = value
            if extra:
                section_data.update(extra)
        config[section.strip().lower()] = section_data
    return config


def project_config():
    """
    Parsing file defined in PROJECT_CONFIG option of main application config.
    Otherwise, trying to find project.cfg file
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
    cfg.optionxform = str
    cfg.read(cfg_path)
    projects = cfg.sections()
    for project in projects:
        name = project.lower()
        result[name] = project_config_options(cfg, project)
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
        try:
            date = dt.strptime(info[1].strip(), "%Y-%m-%dT%H:%M:%S")
        except ValueError as err:
            error("Error parsing date '%s': %s" % (info[1].strip(), err))
            date = None
        node = info[2].strip()
        stat = info[3].strip()
        result.append({
            "date": date.strftime("%Y-%m-%d %X %Z") if date else "Unknown",
            "date_full": date.strftime("%c") if date else "Unknown",
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


def slurm_parse(slurm_raw_output):
    """
    Parsing the output of sreport command looking for account and users,
    consumption.
    :param slurm_raw_output: list of lines produced by sreport command
    :return: dictionary of dictionaries, where project name is the key in first
    dictionary, consumption is the value
    """
    output = {}
    if not slurm_raw_output:
        return output
    meaningful = list(filter(lambda x: "|" in x, slurm_raw_output))
    for item in meaningful:
        debug("Parsing line: %s" % item)
        if "||" not in item:  # user consumption
            items = item.strip().split("|")
        else:
            items = item.strip().split("||")
        name = items[0].strip()
        if len(items) == 3:
            login = items[1].strip()
        else:
            login = None
        try:
            conso = int(items[-1].strip())
        except ValueError as err:
            error("Exception converting '%s' to int: %s" % (items[-1], err))
            continue
        if name not in output:
            output[name] = {}
        if login:
            output[name][login] = conso
            debug("SLURM consumption for %s - %s: %s" % (name, login, conso))
        else:
            output[name]["total consumption"] = conso
            debug("SLURM consumption for %s: %s" % (name, conso))
    return output


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


"""
Bytes-to-human / human-to-bytes converter.
Based on: https://goo.gl/kTQMs
Working with Python 2.x and 3.x.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""

# see: https://goo.gl/kTQMs
SYMBOLS = {
    'customary': ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext': ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                      'zetta', 'iotta'),
    'iec': ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext': ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                'zebi', 'yobi'),
}


def bytes2human(n, layout='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human-readable string based on format.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: https://goo.gl/kTQMs

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
        prefix[s] = 1 << (i + 1) * 10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return layout % locals()
    return layout % dict(symbol=symbols[0], value=n)
