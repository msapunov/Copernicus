from flask import current_app, request, flash, redirect, url_for, g
from flask_login import current_user, logout_user
from pathlib import Path
from logging import debug, error
from functools import wraps
from base import db
from base.email import Mail
from base.database.schema import User, Tasks
from base.utils import normalize_word
from base.functions import generate_password, full_name
from string import ascii_letters

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import formatdate


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
    users = User.query.all()
    logins = list(map(lambda x: x.login, users))

    name = normalize_word(name)
    name = "".join(filter(lambda x: x in ascii_letters, name)).lower()
    surname = normalize_word(surname)
    surname = "".join(filter(lambda x: x in ascii_letters, surname)).lower()

    i = 1
    guess = None
    while i < len(name):
        guess = name[0:i] + surname
        if guess not in logins:
            return guess
        i += 1
    raise ValueError("Seems that user with login '%s' has been already"
                     " registered in our database" % guess)


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

    def accept(self):
        self.task.decision = "accept"
        Mail().task_accepted(self.task).send()
        return self.process()

    def ignore(self):
        self.task.decision = "ignore"
        return self.process()

    def reject(self):
        self.task.decision = "reject"
        Mail().task_rejected(self.task).send()
        return self.process()

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

    def process(self):
        self.task.processed = True
        self.task.approve = current_user
        db.session.commit()
        return self.task


class TaskQueue:

    def __init__(self):
        self.task = Tasks(author=current_user, processed=False, done=False)
        self.u_name = None  # User login name. String
        self.p_name = None  # Project name. String

    def user(self, user_obj):
        self.u_name = user_obj.login
        self.task.user = user_obj
        return self

    def project(self, project_obj):
        self.p_name = project_obj.get_name()
        self.task.project = project_obj
        return self

    def key_upload(self, key):
        if not self.u_name:
            raise ValueError("User is  not set. Can't upload SSH key")
        self.task.action = "ssh|user|%s||%s" % (self.u_name, key)
        self.task.processed = True
        return self.commit()

    def user_create(self, user): #!!!
        if not self.p_name:
            raise ValueError("Can't add a user to none existent project")
        description = user.task_description()
        self.task.action = "create|user|%s|%s|%s" % (user.login, self.p_name,
                                                     description)
        return self.commit()

    def responsible_create(self, user):
        if not self.p_name:
            raise ValueError("Can't add a user to none existent project")
        description = user.task_description()
        self.task.action = "create|resp|%s|%s|%s" % (user.login, self.p_name,
                                                     description)
        return self.commit()

    def user_activate(self, user):
        if not self.project:
            raise ValueError("Can't activate user for none existent project")
        if not hasattr(user, "password"):
            user.password = generate_password()
        description = "login: %s and name: %s and surname: %s and email: %s" \
                      " AND PASSWORD %s" % (user.login, user.name, user.surname,
                                            user.email, user.password)
        self.task.action = "activate|user|%s|%s|%s" % (user.login, self.p_name,
                                                       description)
        self.task.user = user
        return self.commit()

    def user_assign(self, user):
        if not self.project:
            raise ValueError("Can't assign a user to none existent project")
        login = user.login
        description = "Assign user %s to project %s" % (login, self.p_name)
        self.task.action = "assign|user|%s|%s|%s" % (login, self.p_name,
                                                     description)
        self.task.user = user
        return self.commit()

    def responsible_assign(self, user):
        if not self.project:
            raise ValueError("Can't assign a new responsible to none existent"
                             " project")
        login = user.login
        description = "Assign responsible %s to project %s" % (login,
                                                               self.p_name)
        self.task.action = "assign|resp|%s|%s|%s" % (login, self.p_name,
                                                     description)
        self.task.user = user
        return self.commit()

    def user_update(self, data):
        if not self.task.user:
            raise ValueError("Can't update information of unset user")
        tmp_user = self.task.user
        login = tmp_user.login
        act = []
        for key, value in data.items():
            if hasattr(tmp_user, key):
                act.append("%s: %s" % (key, value))
        act = " and ".join(act)
        self.task.action = "update|user|%s|%s|%s" % (login, "", act)
        return self.commit()

    def user_remove(self, user):
        if not self.project:
            raise ValueError("Can't delete a user from none existent project")
        login = user.login
        description = "Remove user %s from project %s" % (login, self.p_name)
        self.task.action = "remove|user|%s|%s|%s" % (login, self.p_name,
                                                     description)
        self.task.user = user
        return self.commit()

    def project_create(self):
        if not self.p_name:
            raise ValueError("Can't create undefined project")
        ref = self.task.project.ref
        description = ("Create new project " + self.p_name +
                       " based on request " + ref.project_id() +
                       " with CPU " + str(self.task.project.resources.cpu))
        self.task.action = "create|proj||%s|%s" % (self.p_name, description)
        return self.commit()

    def project_suspend(self):
        if not self.p_name:
            raise ValueError("Can't suspend undefined project")
        description = "Suspending project %s" % self.p_name
        self.task.action = "suspend|proj||%s|%s" % (self.p_name, description)
        return self.commit()

    def commit(self):
        double = Tasks().query.filter_by(
            action=self.task.action, done=False
        ).first()
        if double:
            raise ValueError("Same previous task found ID: %s" % double.id)
        if "admin" in current_user.permissions():
            self.task.processed = True
        db.session.add(self.task)
        db.session.commit()
        return self
