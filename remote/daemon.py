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
from sqlite3 import connect

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
    log.critical("Config file '%s' does not exists or having wrong permissions"
                 % cfg_file)
    exit(100)

cycle_seconds = options.interval * 60
log.debug("Cycle interval set to '%s' seconds" % cycle_seconds)
log.debug("Reading configuration file '%s'" % cfg_file)


class Tasks:
    def __init__(self, db, cfg):
        self.db = db
        self.cfg = cfg

    def upload(self):
        pass

    def new(self):
        pass

    def execute(self):
        pass


def init_db(cfg):
    log.debug("Initiating database from configuration file")
    if not cfg.has_section("DB"):
        log.error("DB section absent in config")
        medium = ":memory:"
    else:
        medium = cfg("DB", "path", ":memory:")
    log.info("Database initiated at %s" % medium)
    conn = connect(medium)
    log.debug("Connected to the database")
    c = conn.cursor()
    log.debug("Got DB cursor")
    c.execute("""CREATE TABLE IF NOT EXISTS tasks
                 (rollno real, name text, class real)""")
    return conn


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
    log.debug("Starting cycle")
#    if not is_master():
#        log.critical("Running on a slave instance. Terminating")
#        return True
    log.debug("Running on a master instance. All good")
    config = Config()
    config.read(cfg_file)
    log.debug("Configuration read successful")
    db = init_db(config)
    log.debug("Database connection established")
    tasks = Tasks(db, config)
    try:
        tasks.upload()
        log.debug("Upload tasks step is done")
        tasks.new()
        log.debug("New tasks step is done")
        tasks.execute()
        log.debug("Execute tasks step is done")
    except Exception as err:
        log.error("Failure during tasks processing: %s" % err)
        return False
    finally:
        db.close()
        log.debug("Closing database connection")
    log.info("Finishing cycle")
    return True


run()
# task = Watchdog(cycle_seconds, run)
# task.start()
