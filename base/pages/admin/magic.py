from hashlib import md5
from flask import g, render_template, url_for
from flask_login import current_user
from base import db
from base.pages import check_str, TaskQueue
from base.pages.project.magic import get_project_by_name
from base.pages.admin.form import (action_pending,
                                   edit_pending,
                                   visa_pending,
                                   create_pending,
                                   contact_pending,
                                   edit_responsible,
                                   edit_user,
                                   new_user,
                                   edit_task,
                                   contact_user)
from base.pages.admin.form import activate_user
from base.pages.user.magic import user_by_id
from base.pages.user.form import edit_info, set_password, PassForm
from base.database.schema import (User, LogDB, Project, Tasks, ACLDB, Register,
                                  Accounting)
from base.email import Mail, UserMailingList, ResponsibleMailingList
from base.classes import UserLog, RequestLog, TmpUser, ProjectLog, Task
from base.functions import bytes2human
from logging import error, debug
from operator import attrgetter
from datetime import timedelta, datetime as dt
from base.functions import ssh_wrapper

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def process_user_form(form):
    prenom = form.prenom.data.lower()
    surname = form.surname.data.lower()
    email = form.email.data.lower()
    login = form.login.data.lower()
    if login == "none":
        return None
    if login == "select":
        username = form.exist.data
        if username not in g.user_list:
            raise ValueError("Failed to find '%s' among registered users"
                             % username)
        user = User.query.filter_by(login=username).one()
        user.action = "assign"
    else:
        user = User()
        user.login=login
        user.name=prenom
        user.surname=surname
        user.email=email
        user.created=dt.now()
        user.acl=ACLDB()
        db.session.add(user)
        user.action = "create"
    if "True" == form.responsible.data:
        user.acl.is_responsible = True
        user.resp = True
    else:
        user.resp = False
    return user


def account_days(days=30, project=None, user=None):
    today = dt.today().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = [today - timedelta(days=i) for i in range(days)]
    every = Accounting.query.filter(
        Accounting.project == project,
        Accounting.user == user
    )
    if len(dates) > 0:
        every = every.filter(Accounting.date >= dates[-1])
    else:
        every = every.filter(Accounting.date == today)
    every = every.order_by(Accounting.date.desc()).limit(days).all()
    every_data = list(map(lambda x: {x.date.strftime("%Y-%m-%d 00:00"): x.cpu}, every))
    every_keys = list(map(lambda x: x.date.strftime("%Y-%m-%d 00:00"), every))

    for date in dates:
        date = date.strftime("%Y-%m-%d 00:00")
        if date not in every_keys:
            every_data.append({date: 0})
    return every_data


def last_user(data):
    """
    Process data returned by last command and updates seen field in User record
    :param data: String. Output of last command in linux
    :return: None
    """
    lines = data.split("\n")
    for line in lines:
        if "Never" in line:
            continue
        items = line.split()
        if len(items) < 6:
            continue
        login = items[0]
        raw = " ".join(items[-6:])
        try:
            date = dt.strptime(raw, "%a %b %d %H:%M:%S %z %Y")
        except Exception as err:
            error("Failed to convert to datetime: %s" % err)
            continue
        user = User.query.filter_by(login=login).first()
        if not user:
            continue
        user.seen = date
    db.session.commit()


def unprocessed_dict():
    result = []
    for p in unprocessed():
        res = p.to_dict()
        if p.status == "sent" or p.status == "resent":
            created = p.ts.replace(tzinfo=None)
            three = dt.now() - timedelta(days=3*30)
            if created < three:
                res["visa_expired"] = True
        result.append(res)
    return result


def unprocessed():
    """
        Retrieves unprocessed Register objects from the database.

        Returns a list of Register objects that have their 'processed' attribute
        set to False. If the user is an admin (as indicated by 'admin' being
        present in the 'g.permissions' list), all unprocessed Register objects
        are returned. Otherwise, only Register objects that have a 'type' value
        that is included in the 'approve' list are returned. The 'approve' list
        is generated based on the user's login and the ACL (Access Control List)
        defined in the project configuration.

        Returns:
            list: A list of Register objects that are unprocessed and approved
            based on the user's permissions and ACL.
    """
    status = ["created", "ignored", "rejected"]
    query = Register.query.filter(Register.status.is_(None)
                                  | ~Register.status.in_(status))
    if "admin" in g.permissions:
        return query.all()

    approve = []
    for project_type in g.project_config.keys():
        acl = g.project_config[project_type].get("acl", [])
        if current_user.login in acl:
            approve.append(project_type)
        elif set(acl).intersection(set(g.permissions)):
            approve.append(project_type)
    return query.filter(Register.type.in_(approve)).all()


def render_registry(user):
    tasks = Tasks.query.filter_by(user=user).all()
    details = user.details()
    if tasks:
        details["todo"] = list(map(lambda x: x.description(), tasks))
    project_url = url_for("user.web_statistic_name", name="")
    row = render_template("bits/registry_expand_row.html", user=details,
                          project_url=project_url)
    row += render_template("modals/registry_reset_password.html", form=details)
    row += render_template("modals/registry_send_welcome.html", form=details)
    edit_form = edit_info(user)
    row += render_template("modals/user_edit_info.html", form=edit_form)
    set_form = set_password(user)
    row += render_template("modals/registry_set_password.html", form=set_form)
    msg = contact_user(user)
    row += render_template("modals/common_send_message.html", form=msg)
    if not user.active:
        a_form = activate_user(user)
        act = render_template("modals/registry_activate_user.html", form=a_form)
        return row + act
    return row


def render_task(task):
    row = render_template("bits/task_expand_row.html", task=task)
    row += render_template("modals/tasks_accept_task.html", task=task.to_dict())
    row += render_template("modals/tasks_ignore_task.html", task=task.to_dict())
    row += render_template("modals/tasks_reject_task.html", task=task.to_dict())
    form = edit_task(task)
    row += render_template("modals/tasks_edit_task.html", task=task, form=form)
    return row


def render_pending(rec):
    rec.meso = rec.project_id()
    rec.name = "'%s' (%s)" % (rec.title, rec.meso)
    status = rec.status.upper() if rec.status else "NONE"
    if "APPROVED" in status:
        visa = visa_pending(rec)
        top = render_template("modals/admin_visa_pending.html", rec=visa)
    elif "SENT" in status:
        visa = visa_pending(rec)
        top = render_template("modals/admin_visa_received.html", rec=rec)
        top += render_template("modals/admin_visa_pending.html", rec=visa)
    elif "RECEIVED" in status:
        create = create_pending(rec)
        top = render_template("modals/admin_create_project.html",
                              forms=create, project_id=rec.project_id(),
                              name=rec.id)
    elif "SKIPPED" in status:
        create = create_pending(rec)
        top = render_template("modals/admin_create_project.html",
                              forms=create, project_id=rec.project_id(),
                              name=rec.id)
    else:
        top = render_template("modals/admin_approve_pending.html", rec=rec)
    if status not in ["SENT", "RECEIVED"]:
        edit = edit_pending(rec)
        top += render_template("modals/admin_edit_pending.html", form=edit)
        resp = edit_responsible(rec)
        top += render_template("modals/admin_edit_responsible.html", form=resp)
        user_forms = edit_user(rec.users)
        top += render_template("modals/admin_edit_user.html", forms=user_forms,
                               project_id=rec.project_id(), name=rec.id)
        nu = new_user(rec)
        top += render_template("modals/admin_add_user.html", form=nu)
    reset = render_template("modals/admin_reset_pending.html", rec=rec)
    action = action_pending(rec)
    reject = render_template("modals/admin_reject_pending.html", form=action)
    ignore = render_template("modals/admin_ignore_pending.html", rec=rec)
    form = contact_pending(rec)
    mail = render_template("modals/common_send_message.html", form=form)
    logs = list(map(lambda x: x.brief(), RequestLog(rec).list()))
    row = render_template("bits/pending_expand_row.html",
                          pending=rec.to_dict(),
                          logs=logs)
    return row + top + reset + reject + ignore + mail


def all_users():
    """
    Query all the users, check if there is a task associated with a user and
    set a todo property to True for such user and then apply info_acl method
    to all the users in a list.
    :return: List. List of users info dicts
    """
    dirty = list(filter(lambda x: x.user, Tasks().waiting()))
    users = User.query.all()
    for task in dirty:
        idx = users.index(task.user)
        if not hasattr(users[idx], "todo"):
            users[idx].todo = True
    return list(map(lambda x: x.info_acl(), User.query.all()))


def event_log():
    return list(map(lambda x: x.to_web(), LogDB.query.all()))


def get_registration_record(pid):
    register = Register.query.filter_by(id=pid).first()
    if not register:
        raise ValueError("Project registration request id %s not found" % pid)
    return register


def get_ltm(data):
    user_tmp = data["user"]
    users = map(lambda x: check_str(x), user_tmp)
    title = check_str(data["title"])
    msg = check_str(data["message"])
    return users, title, msg


def user_create_by_admin(form):
    email = form.email.data.strip().lower()
    if User.query.filter_by(email=email).first():
        raise ValueError("User with e-mail %s has been registered already"
                         % email)

    real = filter(lambda x: True if x != "None" else False, form.project.data)
    names = list(real)
    if not names:
        raise ValueError("Can't create a user in not existing project: %s" %
                         ", ".join(form.project.data))

    user = TmpUser()
    user.name = form.name.data.strip().lower()
    user.surname = form.surname.data.strip().lower()
    user.email = email
    user.login = form.login.data.strip().lower()
    user.active = True if form.active.data else False
    user.is_user = True if form.is_user.data else False
    user.is_responsible = True if form.is_responsible.data else False
    user.is_manager = True if form.is_manager.data else False
    user.is_tech = True if form.is_tech.data else False
    user.is_admin = True if form.is_admin.data else False
    user.is_committee = True if form.is_committee.data else False

    for name in names:
        project = get_project_by_name(name)
        tid = TaskQueue().project(project).user_create(user).task.id
        Task(tid).accept()  # TODO: Do some tests!
        msg = "Add a new user: %s '%s %s <%s>'" % (
            user.login, user.name, user.surname, user.email)
        ProjectLog(project).event(msg)
    return "Add creation of the user %s for %s to the execution queue" % (
        user.login, ", ".join(form.project.data))


def user_changed_prop(obj, frm):
    """

    :param obj:
    :param frm:
    :return:
    """
    info, acl, act = {}, {}, None
    for name in ["login", "name", "surname", "email", "test"]:
        if name not in frm:
            continue
        data = getattr(frm, name).data.strip().lower()
        if getattr(obj, name).lower() != data:
            info[name] = data
    for i in ["user", "responsible", "manager", "tech", "committee", "admin"]:
        name = "is_%s" % i
        if name not in frm:
            continue
        data = getattr(frm, name).data
        if getattr(obj.acl, name) != data:
            acl[name] = data
    if "active" in frm and (obj.active != frm.active.data):
        act = frm.active.data
    names = filter(lambda x: True if x != "None" else False, frm.project.data)
    projects = list(set(obj.project_names()) ^ set(list(names)))
    UserLog(obj).info_update(info=info, acl=acl, projects=projects, active=act)
    return info, acl, projects, act


def user_acl_update(user, acl):
    for name, value in acl.items():
        setattr(user, name, value)
    db.session.commit()
    UserLog(user).acl(acl)
    return "ACL modifications has been saved to the database"


def user_project_update(user, projects):
    old = user.project_names()
    idz = []
    for name in projects:
        project = Project.query.filter_by(name=name).first()
        if not project:
            continue
        if name in old:
            task = TaskQueue().project(project).user_remove(user)
        else:
            task = TaskQueue().project(project).user_assign(user)
        idz.append(task.task.id)
    s, ids = "s" if len(idz) > 1 else "", ", ".join(map(str, idz))
    return "Project change task%s with id%s has been created: %s" % (s, s, ids)


def registration_user_del(pid, uid):
    rec = get_registration_record(pid)
    users = rec.users.split("\n")
    for user in users:
        tmp = md5(user.encode()).hexdigest()
        if tmp != uid:
            continue
        users.remove(user)
        RequestLog(rec).user_del(user)
    rec.users = "\n".join(users)
    db.session.commit()
    return rec.to_dict()


def registration_record_edit(rid, form):
    rec = get_registration_record(rid)
    not_str = ["cpu"]
    props = ["title", "type", "description", "scientific_fields", "cpu",
             "genci_committee", "numerical_methods", "computing_resources",
             "project_management", "project_motivation", "article_1",
             "article_2", "article_3", "article_4", "article_5"]
    msg = ["Updated"]
    for prop in props:
        old = getattr(rec, prop)
        field = getattr(form, prop)
        if prop not in not_str:
            new = field.data.strip()
        else:
            new = field.data
        if old != new:
            setattr(rec, prop, new)
            msg.append("%s: %s -> %s" % (field.label.text, old, new))
    if db.session.dirty:
        db.session.commit()
        msg = "\n".join(msg)
        RequestLog(rec).request_change(msg)
        return render_pending(rec)
    raise ValueError("No modifications has been detected!")


def registration_user_add(rid, form):
    rec = get_registration_record(rid)
    name = form.prenom.data.strip()
    surname = form.surname.data.strip()
    email = form.email.data.strip()
    if getattr(form, "login", None):
        login = form.login.data.strip()
    else:
        login = ""
    user = "First Name: %s; Last Name: %s; E-mail: %s; Login: %s" % \
           (name, surname, email, login)
    users = rec.users.split("\n")
    users.append(user)
    rec.users = "\n".join(users)
    db.session.commit()
    RequestLog(rec).user_add(user)
    return render_pending(rec)


def registration_user_update(rid, forms):
    rec = get_registration_record(rid)
    users = []
    if len(forms) > 0:
        for form in forms:
            name = form.prenom.data
            surname = form.surname.data
            email = form.email.data
            login = form.login.data if getattr(form, "login", None) else ""
            user = "First Name: %s; Last Name: %s; E-mail: %s; Login: %s" % \
                   (name, surname, email, login)
            users.append(user)
    new = "\n".join(users)
    if rec.users != new:
        RequestLog(rec).user_change(new)  # TODO nicer messages with changes
        rec.users = new
        db.session.commit()
    return render_pending(rec)


def registration_responsible_edit(rid, form):
    rec = get_registration_record(rid)
    props = {"responsible_first_name": "prenom",
             "responsible_last_name": "surname",
             "responsible_email": "email",
             "responsible_position": "position",
             "responsible_lab": "lab",
             "responsible_phone": "phone"}
    msg = ["Updated"]
    for key, value in props.items():
        old = getattr(rec, key)
        field = getattr(form, value)
        new = field.data.strip()
        if old != new:
            setattr(rec, key, new)
            msg.append("%s: %s -> %s" % (field.label.text, old, new))
    if db.session.dirty:
        db.session.commit()
        msg = "\n".join(msg)
        RequestLog(rec).request_change(msg)
        return render_pending(rec)
    raise  ValueError("No modifications has been detected!")


def user_info_update_new(form):
    """

    :param form:
    :return:
    """
    uid = form.uid.data
    user = user_by_id(uid)
    info, acl, project, active = user_changed_prop(user, form)
    if not info and not acl and not project and not active:
        return user.details(), "No modifications has been detected"
    msg = []
    if acl:
        msg.append(user_acl_update(user, acl))
    if project:
        msg.append(user_project_update(user, project))
    if info:
        msg.append("User information has been updated in the DB")
    result = "\n".join(msg)
    return user.details(), result


def update_user_acl(user, form):
    acl = {}
    for i in ["user", "responsible", "manager", "tech", "committee", "admin"]:
        name = "is_%s" % i
        if name not in form:
            continue
        new = getattr(form, name).data
        old = getattr(user.acl, name)
        if old != new:
            setattr(user.acl, name, new)
            acl[name] = new
    if not acl:
        return
    db.session.commit()
    UserLog(user).acl(acl)
    return "ACL modifications has been saved to the database"


def update_user_project(user, form):
    names = filter(lambda x: True if x != "None" else False, form.project.data)
    new = list(set(user.project_names()) ^ set(list(names)))
    old = user.project_names()
    idz = []
    for name in new:
        project = Project.query.filter_by(name=name).first()
        if not project:
            continue
        if name in old:
            project.users.remove(user)
            task = TaskQueue().project(project).user_remove(user)
        else:
            project.users.append(user)
            task = TaskQueue().project(project).user_assign(user)
        idz.append(task.task.id)
    if not idz:
        return
    db.session.commit()
    s, ids = "s" if len(idz) > 1 else "", ", ".join(map(str, idz))
    return "Project change task%s with id%s %s has been created" % (s, s, ids)


def update_user_details(user, form):
    info = {}
    for name in ["login", "name", "surname", "email", "activate"]:
        if name not in form:
            continue
        data = getattr(form, name).data.strip().lower()
        if getattr(user, name).lower() == data:
            continue
        setattr(user, name, data)
        info[name] = data
    if not info:
        return
    db.session.commit()
    if "activate" in info.keys():
        task = TaskQueue().user(user).user_activate(info)
    else:
        task = TaskQueue().user(user).user_update(info)
    UserLog(user).info_update(info=info)
    return "User info update with id '%s' has been created" % task.id


def user_info_update(form):
    uid = form.uid.data
    user = user_by_id(uid)
    msg = []
    for result in [update_user_acl(user, form), update_user_project(user, form),
                   update_user_details(user, form)]:
        if not result:
            continue
        msg.append(result)
    result = "\n".join(msg)
    return user.details(), result


def user_delete(uid):
    user = user_by_id(uid)
    login = user.login
    projects = user.project
    User.query.filter_by(id=uid).delete()
    db.session.commit()
    for project in projects:
        msg = "User %s has been removed from the UserDB by admins" % login
        ProjectLog(project).event(msg)
    return "User %s has been removed from the database" % login


def user_send_welcome(uid):
    user = user_by_id(uid)
    user.passwd = user.reset_password()
    Mail().user_new(user).start()
    return "Welcome message for user %s has been sent" % user.login


def user_set_pass(uid):
    form = PassForm()
    if not form.validate_on_submit():
        raise ValueError(form.errors)
    user = user_by_id(uid)
    user.set_password(form.password.data)
    UserLog(user).password_changed()
    return "Password for user %s has been set successfully" % user.login


def user_reset_pass(uid):
    user = user_by_id(uid)
    passwd = user.reset_password()
    UserLog(user).password_reset(passwd)


def user_create(task):
    if not task.project:
        raise ValueError("Project reference is empty, can't create user")
    tmp_user = TmpUser().from_description(task.action)
    if "TEMPORARY USER" in tmp_user.comment:
        return ProjectLog(task.project).user_created(task)  # Ugly!!
    user = User.query.filter_by(login=tmp_user.login).first()
    if not user:
        user = User()
        user.login=tmp_user.login
        user.name=tmp_user.name
        user.surname=tmp_user.surname
        user.email=tmp_user.email
        user.active=True
        user.project=[task.project]
        user.created=dt.now()
        user.acl=ACLDB(is_user=tmp_user.is_user,
                       is_responsible=tmp_user.is_responsible,
                       is_tech=tmp_user.is_tech,
                       is_manager=tmp_user.is_manager,
                       is_committee=tmp_user.is_committee,
                       is_admin=tmp_user.is_admin)
        db.session.add(user)
    if user not in task.project.users:
        task.project.users.append(user)
    if not getattr(user, "passwd", None):
        user.passwd = user.reset_password()
    Mail().user_new(user).start()
    UserMailingList().add(user.email, user.full_name())
    if user.acl.is_responsible:
        task.project.responsible = user
        ResponsibleMailingList().add(user.email, user.full_name())
    return ProjectLog(task.project).user_created(task)  # Ugly!


def user_publickey(self):
    """
    Send message after public key has been uploaded on the server
    Return: Object. Mail object
    """
    user = self.task.user
    key = self.get_description()
    return UserLog(user).key_uploaded(key)
    return "New password has been sent to %s" % user.full()


def process_task(tid, result):
    record = Tasks().query.filter_by(id=tid).first()
    if record.done:
        raise ValueError(f"Task {tid} has been processed already")
    act = record.action.split("|")[0]
    ent = record.action.split("|")[1]
    req = ["activate", "create", "assign", "update", "remove", "change", "ssh"]
    if act not in req:
        raise ValueError("The action '%s' is not supported" % act)
    task = Task(record)
    if act == "create" and ent == "user":
        task.user_create()
    elif act == "create" and ent == "resp":
        task.user_create()
    elif act == "create" and ent == "proj":
        task.project_create()
    elif act == "update" and ent == "user":
        task.user_update()
    elif act == "update" and ent == "proj":
        pass
    elif act == "activate" and ent == "user":
        task.user_activate()
    elif act == "assign" and ent == "user":
        task.user_assign()
    elif act == "assign" and ent == "resp":
        task.responsible_assign()
    elif act == "remove" and ent == "user":
        task.user_delete()
    elif act == "ssh" and ent == "user":
        task.user_publickey()
    return task.done(result)


def task_history(reverse=True):
    # Returns a list of all tasks registered in the system. by default
    # the records are sorted by date in descending order
    tasks = sorted(Tasks.query.all(), key=attrgetter("created"),
                   reverse=reverse)
    return list(map(lambda x: x.to_dict(), tasks)) if tasks else []


class TaskManager:

    def __init__(self):
        self.query = Tasks().query
        self.tasks = Tasks

    def todo(self):
        # Returns a list of tasks which has been processed by admins but haven't
        # been performed by a script
        self.query = self.query.filter(
            self.tasks.processed == True
        ).filter(
            self.tasks.decision == "accept"
        ).filter(
            self.tasks.done == False
        )
        tasks = self.query.all()
        return list(map(lambda x: x.api(), tasks)) if tasks else []

    def list(self):
        # Returns a list of unprocessed tasks, i.e. a task has been created by
        # a user but admins haven't had time yet to check it out
        tasks = Tasks.query.filter(
            Tasks.processed != True).filter(Tasks.done != True
        ).all()
        return list(map(lambda x: x.to_dict(), tasks)) if tasks else []


def get_server_cpu(server):
    cmd = "S_COLORS=never mpstat | grep all"
    result, err = ssh_wrapper(cmd, host=server)
    error(f"{server} {result}")
    if err:
        raise ValueError("Error retrieving:" % err)
    info = str(result[0]).strip("\n").split()
    if len(info) > 12:
        raise ValueError("Wrong format of mpstat command")

    time = info[0].strip()
    idle = float(info[-1].strip().replace(",", "."))
    return {"time": time, "idle": idle}


def get_server_info(server):
    out = {"server": server, "uptime": "", "users": []}
    cmd = "echo cores:`nproc` && uptime -p && free -b | grep -v total && uptime"
    cmd += "| awk '/average/ {OFS=\":\"; print \"Load\",$(NF-2),$(NF-1),$NF}'"
    cmd += "&& who | cut -d' ' -f1 | sort -u && echo Time: `date +%s`"
    result, err = ssh_wrapper(cmd, host=server)
    if not result:
        error("Error getting information from the remote server: %s" % err)
        return out

    up = memory_data = swap_data = load_data = now = ""
    cores = 1
    for i in result:
        if "Load" in i:
            load_data = i.replace("Load:", "").strip()
        elif "minutes" in i:
            up = i.replace("up", "").strip()
        elif "Mem" in i:
            memory_data = i
        elif "Swap" in i:
            swap_data = i
        elif "Time" in i:
            now = i.replace("Time:", "").strip()
        elif "cores" in i:
            cores = i.replace("cores:", "").strip()
        else:
            out["users"].append(i.strip())

    for key, value in parse_load(load_data, cores).items():
        out[key] = value
    for key, value in parse_memory(memory_data).items():
        out[key] = value
    for key, value in parse_swap(swap_data).items():
        out[key] = value
    out["uptime"] = up
    out["time"] = parse_timestamp(now)
    return out


def parse_timestamp(unix_ts):
    try:
        ts = int(unix_ts)
    except ValueError as e:
        return unix_ts
    dt_object = dt.fromtimestamp(ts)
    return dt_object.strftime('%Y-%m-%d %H:%M')


def parse_load(result, cores=1):
    try:
        load_1, load_5, load_15 = result.split(":")
    except ValueError as e:
        return {"load_1": 0, "load_5": 0, "load_15": 0}
    load_1 = "{0:.1%}".format(float( load_1.strip(",") ) / float(cores))
    load_5 = "{0:.1%}".format(float( load_5.strip(",") ) / float(cores))
    load_15 = "{0:.1%}".format(float( load_15.strip(",") ) / float(cores))
    return {"load_1": load_1, "load_5": load_5, "load_15": load_15}


def parse_swap(result):
    tmp = {}
    output = result.split(",")
    for i in output:
        if "Swap" in i:
            swap = i.split()
            swap_total = int(swap[1].strip())
            swap_available = int(swap[3].strip())
            swap_used = swap_total - swap_available
            swap_usage = "{0:.1%}".format(float(swap_used) /
                                          float(swap_total))
            tmp["swap_total"] = bytes2human(swap_total)
            tmp["swap_available"] = bytes2human(swap_available)
            tmp["swap_used"] = bytes2human(swap_used)
            tmp["swap_usage"] = swap_usage
    return tmp


def parse_memory(result):
    tmp = {}
    output = result.split(",")
    for i in output:
        if "Mem" in i:
            memory = i.split()
            mem_total = int(memory[1].strip())
            mem_available = int(memory[6].strip())
            mem_used = mem_total - mem_available
            mem_usage = "{0:.1%}".format(float(mem_used) / float(mem_total))
            tmp["mem_total"] = bytes2human(mem_total)
            tmp["mem_available"] = bytes2human(mem_available)
            tmp["mem_used"] = bytes2human(mem_used)
            tmp["mem_usage"] = mem_usage
    return tmp


def space_info():
    """
    Run df -h command on a remote server and return parsed information as a list
    of dictionaries. Dictionary format is:
    {"filesystem": ...,
        "size": ...,
        "used": ...,
        "available": ...,
        "use": ...,
        "mountpoint": ...}
    :return: List of dict
    """
    result, err = ssh_wrapper("df -h")
    if not result:
        raise ValueError("Error getting disk space information: %s" % err)

    space = []
    for record in result:
        if "Filesystem" in record:
            continue
        keywords = ["/home", "/save", "/trinity/shared", "/scratch",
                    "/scratchfast", "/scratchw"]
        filesystem, size, used, avail, use, mountpoint = record.split()
        if mountpoint.strip() not in keywords:
            continue
        space.append({"filesystem": filesystem.strip(),
                      "size": size.strip(),
                      "used": used.strip(),
                      "available": avail.strip(),
                      "use": use.strip(),
                      "mountpoint": mountpoint.strip()})
    return space


def slurm_partition_info():
    result, err = ssh_wrapper("sinfo -s")
    if not result:
        raise ValueError("Error getting partition information: %s" % err)

    partition = []
    for record in result:
        if "PARTITION" in record:
            continue
        name, avail, time, nodes, nodelist = record.split()
        name = name.strip()
        nodes = nodes.strip()
        allocated, idle, other, total = nodes.split("/")
        partition.append({"name": name, "allocated": allocated, "idle": idle,
                          "other": other, "total": int(total)})
    return partition
