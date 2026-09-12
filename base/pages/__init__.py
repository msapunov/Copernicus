"""Shared utilities for page blueprints: access control, user lookups,
and task processing.
"""

from functools import wraps
from logging import debug, error
from string import ascii_letters

from flask import flash, g, redirect, request, url_for
from flask_login import current_user, logout_user

from base import db
from base.database.schema import Tasks, User
from base.email import Mail
from base.functions import full_name
from base.functions import normalize_word


def grant_access(*roles):
    def log_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            url = request.full_path
            for role in roles:
                if role in g.permissions:
                    return f(*args, **kwargs)
            if request.is_json:
                return "Permissions denied based on user role", 403
            error("Available user roles doesn't permit to access URL: %s" % url)
            flash("Permissions denied to access URL: %s" % url)
            logout_user()
            return redirect(url_for("login.login"))
        return decorated_function
    return log_required


def check_str(raw_note):
    note = str(raw_note)
    if (not note) or (len(note) < 1):
        raise ValueError("Provided string can't be empty")
    return note


def user_by_details(name, surname, email, login=None):
    name = normalize_word(name)
    name = "".join(filter(lambda x: x in ascii_letters, name)).lower()
    surname = normalize_word(surname)
    surname = "".join(filter(lambda x: x in ascii_letters, surname)).lower()
    email = email.lower()
    login1 = name[0] + surname
    login2 = surname[0] + name
    result = [User.query.filter_by(login=login1).all(),
              User.query.filter_by(login=login2).all(),
              User.query.filter_by(email=email).all(),
              User.query.filter_by(name=name, surname=surname).all(),
              User.query.filter_by(name=surname, surname=name).all()]
    if login:
        result.append(User.query.filter_by(login=login).all())
    not_empty = list(filter(lambda x: x != [], result))
    every = [item for sublist in not_empty for item in sublist]
    return list(set(every))


def generate_login(name, surname):
    users = User.query.filter_by(archived=None).all()
    logins = list(map(lambda x: x.login, users))

    name = normalize_word(name)
    name = "".join(filter(lambda x: x in ascii_letters, name)).lower()
    surname = normalize_word(surname)
    surname = "".join(filter(lambda x: x in ascii_letters, surname)).lower()

    i = 1
    while i <= len(name):
        guess = name[0:i] + surname
        debug(f"{guess} is among {", ".join(logins)}. Next guess")
        if guess not in logins:
            return guess
        i += 1
    raise ValueError(f"Failed to generate unique login for {name} {surname}")


def process_new_user(rec):
    class Tmp:
        pass
    user = Tmp()
    parts = rec.split(";")
    if not parts or len(parts) < 3:
        return user
    for i in parts:
        if "First Name:" in i:
            user.name = i.replace("First Name:", "").strip()
        elif "Last Name:" in i:
            user.surname = i.replace("Last Name:", "").strip()
        elif "E-mail:" in i:
            user.email = i.replace("E-mail:", "").strip()
        elif "Login:" in i:
            user.login = i.replace("Login:", "").strip()
        else:
            continue
    user.uid = "".join(filter(lambda x: x in ascii_letters, user.email)).lower()
    user.full = full_name(user.name, user.surname)
    user.direct= generate_login(user.name, user.surname)
    user.inverse = generate_login(user.surname, user.name)
    if not user.login:
        is_user = user_by_details(user.name, user.surname, user.email)
        if is_user:
            user.login = is_user[0].login
    if not user.login:
        user.direct_check = "checked"
    else:
        user.select_check = "checked"
    return user


def check_json():  # TODO: remove - replace
    if not request.is_json:
        raise ValueError("Expecting application/json requests")
    data = request.get_json()
    if not data:
        raise ValueError("Empty JSON request received")
    debug("Incoming JSON: %s" % data)
    return data


class Task:

    def __init__(self, tid):
        task = Tasks().query.filter_by(id=tid).first()
        if not task:
            raise ValueError("No task with id %s found" % tid)
        self.task = task
        self.id = task.id

    def description(self):
        return self.task.description()

    def accept(self, comment=None):
        self.task.decision = "accept"
        Mail().task_accepted(self.task, comment).send()
        return self.process(comment)

    def ignore(self, comment=None):
        self.task.decision = "ignore"
        return self.process(comment)

    def reject(self, comment=None):
        self.task.decision = "reject"
        Mail().task_rejected(self.task, comment).send()
        return self.process(comment)

    def action(self):
        return self.task.action

    def update(self, form):
        for prop in ["processed", "done", "decision"]:
            value = getattr(form, prop).data
            if value == "true":
                value = True
            elif value == "false":
                value = False
            elif value == "none":
                value = None
            setattr(self.task, prop, value)
        db.session.commit()
        return self.task

    def process(self, comment=None):
        self.task.processed = True
        self.task.approve = current_user
        if comment:
            self.task.comment = comment
        else:
            self.task.comment = "Task processed by %s" % current_user.full()
        db.session.commit()
        return self.task


