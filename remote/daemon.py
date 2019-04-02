#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging as log

from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
from subprocess import Popen, PIPE
from threading import Timer
from optparse import OptionParser
from os.path import exists
from configparser import ConfigParser as Config
from warnings import filterwarnings
from smtplib import SMTP, SMTPException
from email.message import EmailMessage
from socket import gethostname

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"

filterwarnings(action='ignore', module='.*paramiko.*')
parser = OptionParser()
parser.add_option("-c", "--config",
                  action="store",
                  help="Path to the file with configuration")
parser.add_option("-i", "--interval",
                  action="store",
                  type=int,
                  default=5,
                  help="Number of minutes between the working cycles")
parser.add_option("-l", "--log",
                  action="store",
                  choices=["debug", "info", "warning", "error", "critical"],
                  help="Sets the threshold for the logger to given level",
                  default="warning")
(options, args) = parser.parse_args()

level = options.log
level = level.lower()
formatter = "%(asctime)s - %(levelname)s - %(message)s"

if "debug" == level:
    log.basicConfig(level=log.DEBUG, format=formatter)
elif "info" == level:
    log.basicConfig(level=log.INFO, format=formatter)
elif "error" == level:
    log.basicConfig(level=log.ERROR, format=formatter)
elif "critical" == level:
    log.basicConfig(level=log.CRITICAL, format=formatter)
else:
    log.basicConfig(level=log.WARNING, format=formatter)
log.info("Temp")

cfg_file = options.config
if not cfg_file:
    log.critical("Option 'config' is not optional")
    exit(99)
if not exists(cfg_file):
    log.critical("Config file '%s' does not exists or having bad permissions"
                 % cfg_file)
    exit(100)

cycle_seconds = options.interval * 60
log.debug("Cycle interval set to '%s' seconds" % cycle_seconds)
log.debug("Reading configuration file '%s'" % cfg_file)

CONFIG = Config()
CONFIG.read(cfg_file)

ERRORS = []


def send_mail(subject, message):
    init = get_config("Mail")

    msg = EmailMessage()
    msg.set_content(message)

    if not subject:
        subject = "Default subject"
    hostname = gethostname()
    subject += " from %s" % hostname
    msg["Subject"] = subject
    msg["From"] = init.get("from")
    msg["To"] = init.get("to")

    try:
        s = SMTP('localhost')
        s.send_message(msg)
        s.quit()
        log.debug("Successfully sent an email")
    except SMTPException as err:
        log.debug("Failed to send email: %s" % err)


def execute(argz):
    cmd = " ".join(argz)
    log.debug("Executing command: %s" % cmd)
    command = Popen(argz, stderr=PIPE, stdout=PIPE)
    (out, err) = command.communicate()

    out = out.strip().decode()
    log.debug("Command's output: %s" % str(out))
    err = err.strip().decode()
    log.debug("Command's error: %s" % str(err))
    if err:
        ERRORS.append("Command:\n'%s'\nStdErr:\n'%s'\nStdOut:\n'%s'"
                      % (cmd, err, out))
    if not command.returncode == 0:
        if err:
            log.error(err)
        else:
            log.error("Command '%s' exit code is not null" % cmd)
    return out, err


def remote_cmd(ssh):
    host = ssh["hostname"]
    login = ssh["username"]
    key = ssh["key"]
    cmd = ssh["cmd"]

    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    log.debug("Executing remote command: %s" % cmd)
    try:
        client.connect(host, username=login, password="", key_filename=key)
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.readlines()
        log.debug("StdOut: %s" % out)
        err = stderr.readlines()
        log.debug("StdErr: %s" % err)
    except AuthenticationException:
        log.error("Can't connect to server %s" % host)
        return
    finally:
        client.close()
    if err:
        log.error("Error while executing remote code: %s" % err)
        return False
    return out


def is_master():
    cmd = ["systemctl", "status", "slurmctld.service"]
    log.debug("Command: %s" % " ".join(cmd))
    stdout, stderr = execute(cmd)
    log.debug("StdOut: %s" % stdout)
    log.debug("StdErr: %s" % stderr)
    if "active (running)" not in stdout:
        return False
    return True


def get_consumption(name):
    cmd = ["sreport", "-nP", "cluster", "AccountUtilizationByUser"]
    cmd += ["Start=2018-01-01", "account=%s" % name]
    cmd += ["format=Accounts,Login,Used"]
    stdout, stderr = execute(cmd)
    if not stdout:
        return False
    recs = stdout.split("\n")
    log.debug("Split to strings: %s" % recs)
    rec = list(filter(lambda x: "||", recs))[0]  # must be  alist of one element
    log.debug("Raw line of project's consumption: %s" % rec)
    conso_str = rec.split("|")[2]
    log.debug("Consumption as a string: %s" % conso_str)
    try:
        return int(conso_str)
    except Exception as err:
        log.error("failed to convert value %s to int: %s" % (conso_str, err))
        return False


def extract_ext_data(rec):
    try:
        rid, hours, project = rec.split("|")
    except Exception as err:
        log.error("Failed to extract data from record %s: %s" % (rec, err))
        return None
    project = project.strip()
    rid = rid.strip()
    try:
        hours = int(hours)
    except Exception as err:
        log.error("Failed to convert %s to int: %s" % (hours, err))
        return None
    return {"limit": hours * 60, "id": rid, "name": project}


def new_ext_limit(rec):
    project = rec["name"]
    limit = rec["limit"]
    conso = get_consumption(project)
    if not conso:
        log.error("Failed to get project's consumption!")
        return None
    log.debug("Consumption in minutes: %s" % conso)
    rec["new"] = conso + limit
    log.debug("New limit in minutes: %s" % rec["new"])
    return rec


def enforce_limit(rec):
    name = rec["name"]
    new = rec["new"]
    msg = "Enforcing new limit of %s minutes for project %s" % (new, name)
    log.info(msg)
    rec["log"] = msg
    base = ["sacctmgr", "-i", "modify", "qos", name]
    cmd1 = base + ["set", "GrpCPUMins=%s" % new]
    cmd2 = base + ["set", "GrpSubmitJobs=-1"]

    stdout, stderr = execute(cmd1)
    if not stdout:
        return False
    rec["cmd1"] = " ".join(cmd1)

    stdout, stderr = execute(cmd2)
    if not stdout:
        return False
    rec["cmd2"] = " ".join(cmd2)

    return rec


def ext_log(rec):
    return "%s:\n%s\n" % (rec["log"], rec["cmd1"])


def update_ext_db(ssh, rec):
    rid = rec["id"]
    host = ssh["hostname"]
    user = ssh["username"]
    key = ssh["key"]
    cmd = ssh["cmd"] % rid
    log.debug("Updating remote DB record with the id: %s" % rid)
    remote_cmd({"hostname": host, "username": user, "key": key, "cmd": cmd})
    return True


def extension():
    log.info("Processing project extensions")
    init = get_config("Extension")
    hostname = init.get("hostname")
    username = init.get("username")
    key = init.get("key")
    cmd = init.get("command")
    log.debug("hostname: %s, username: %s, key: %s, command: %s" %
              (hostname, username, key, cmd))

    dirty = remote_cmd({"hostname": hostname, "username": username, "key": key,
                        "cmd": cmd})

    data_dirty = list(map(lambda x: x.strip(), dirty))
    log.debug("Stripped data: %s" % data_dirty)
    data = list(filter(lambda x: len(x) > 0, data_dirty))
    log.debug("Positive length data: %s" % data)
    recs = list(filter(lambda x: x.split()[0].isdigit(), data))
    if not recs:
        log.info("No project extensions found")
        return
    log.debug("Meaningful data: %s" % recs)
    todo_dirty = list(map(lambda x: extract_ext_data(x), recs))
    log.debug("Extracted dirty data: %s" % todo_dirty)
    todo = list(filter(lambda x: x, todo_dirty))
    log.debug("Extracted clean data: %s" % todo)
    new_dirty = list(map(lambda x: new_ext_limit(x), todo))
    log.debug("Dirty new limits: %s" % new_dirty)
    new = list(filter(lambda x: x, new_dirty))
    log.debug("Clean  new limits: %s" % new)
    result = list(map(lambda x: enforce_limit(x), new))
    filter_result = list(filter(lambda x: x, result))
    if not filter_result:
        log.error("Seems there was an error during project extension")
        return
    log_message = "\n".join(list(map(lambda x: ext_log(x), filter_result)))
    send_mail("Extension report", "Project extension \n\n" + log_message)
    cmd = init.get("update")
    ssh = {"hostname": hostname, "username": username, "key": key, "cmd": cmd}
    list(map(lambda x: update_ext_db(ssh, x), filter_result))
    log.info("Done with project extension processing")
    return


def get_config(section):
    if not CONFIG.has_section(section):
        log.critical("Expect to have section %s in config file" % section)
        return
    return dict(CONFIG.items(section))


class Watchdog:

    def __init__(self, seconds, function):
        self.t = seconds
        self.hFunction = function
        self.thread = Timer(self.t, self.handle_function)

    def handle_function(self):
        self.hFunction()
        self.thread = Timer(self.t, self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

    def cancel(self):
        self.thread.cancel()


def run():
    if not is_master():
        log.critical("Running on not master instance. Terminating")
        return
    log.debug("Running on a master instance")
    extension()
    if ERRORS:
        send_mail("Error report", "\n".join(ERRORS))


run()
# task = Watchdog(cycle_seconds, run)
# task.start()