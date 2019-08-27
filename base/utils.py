from flask import current_app
from datetime import datetime as dt
from flask_login import current_user
from base.database.schema import LogDB


class ProjectLog:

    def __init__(self, project, send=True):
        self.project = project
        self.log = LogDB(author=current_user, project=project)
        self.send = send

    def responsible_added(self, user):
        self.log.event = "Added a new project responsible %s with login %s" % (
            user.full_name(), user.login)
        return self._commit_user(user)

    def responsible_assign(self, user):
        self.log.event = "Made a request to assign new responsible %s"\
                         % user.full_name()
        return self._commit_user(user)

    def user_added(self, user):
        self.log.event = "Added a new user %s with login %s" % (
            user.full_name(), user.login)
        return self._commit_user(user)

    def user_assign(self, user):
        self.log.event = "Made a request to assign a new user %s"\
                         % user.full_name()
        return self._commit_user(user)

    def user_assigned(self, user):
        self.log.event = "User %s has been attached" % user.full_name()
        return self._commit_user(user)

    def user_deleted(self, user):
        self.log.event = "User %s (%s) has been deleted" % (
            user.full_name(), user.login)
        return self._commit_user(user)

    def user_del(self, user):
        self.log.event = "Made a request to delete user %s" % user.full_name()
        return self._commit_user(user)

    def _commit_user(self, user):
        self.log.user = user
        return self._commit()

    def extend(self, extension):
        self.log.event = "Made a request to extend project for %s hour(s)"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def extended(self, extension):
        self.log.event = "Extension request for %s hour(s) has been processed"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def activate(self, extension):
        self.log.event = "Made an activation request"
        self.log.extension = extension
        return self._commit()

    def transform(self, extension):
        self.log.event = "Made a request to transform from type A to type B"
        self.log.extension = extension
        return self._commit()

    def accept(self, extension):
        self.log.event = "Extend request for %s hours is accepted"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def ignore(self, extension):
        self.log.event = "Extend request for %s hours is ignored"\
                         % extension.hours
        self.log.extension = extension
        self.send = False
        return self._commit()

    def reject(self, extension):
        self.log.event = "Extend request for %s hours is rejected"\
                         % extension.hours
        self.log.extension = extension
        return self._commit()

    def event(self, message):
        self.log.event = message.lower()
        return self._commit()

    def _commit(self):
        from base import db
        db.session.add(self.log)
        db.session.commit()
        message = "%s: %s" % (self.project.get_name(), self.log.event)
        if self.send:
            if not self.project.responsible:
                raise ValueError("project %s has no responsible attached!" %
                                 self.project.get_name())
            if not self.project.responsible.email:
                raise ValueError("project %s responsible nas no email!" %
                                 self.project.get_name())
            #send_message(self.project.responsible.email, message=message)
        return message


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
    DAY = current_app.config["ACC_START_DAY"]
    MONTH = current_app.config["ACC_START_MONTH"]

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
