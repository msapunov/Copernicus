#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging as log

from threading import Timer
from optparse import OptionParser
from os.path import exists
from configparser import ConfigParser as Config


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


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
log.info("Checking if the system users are in sync with UserDB")

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


def execute(argz):
    log.debug("Executing command: %s" % " ".join(argz))
    command = Popen(argz, stderr=PIPE, stdout=PIPE)
    (out, err) = command.communicate()

    out = out.strip()
    log.debug("Command's output: %s" % str(out))
    err = err.strip()
    log.debug("Command's output: %s" % str(err))

    if not command.returncode == 0:
        if err:
            log.error(err)
        else:
            log.error("Command '%s' exit code is not null" % " ".join(argz))
    return out, err


def master():
    cmd = ["systemctl", "status", "slurmctld.service"]
    stdout, stderr = execute(cmd)
    print(stdout)
    print(stderr)
    if "active (running)" not in stdout:
        return False
    return True


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

    if not master():
        log.critical("Running on not master instance. Terminating")
        return
    log.debug("Running on a master instance")


    config = Config()
    config.read(cfg_file)

    section = "Management"
    if not config.has_section(section):
        log.critical("Expect to have section %s in config file" % section)
        return

    db_type = config.get(section, "type").strip().lower()
    db_user = config.get(section, "user").strip().lower()
    db_host = config.get(section, "host").strip().lower()
    db_name = config.get(section, "name").strip().lower()
    db_url = "%s://%s@%s/%s" % (db_type, db_user, db_host, db_name)
    log.debug("URL for the database: %s" % db_url)


task = Watchdog(cycle_seconds, run)
task.start()
