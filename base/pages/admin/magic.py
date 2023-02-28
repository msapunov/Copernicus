from hashlib import md5
from flask import g, render_template, current_app as app
from flask_login import current_user
from base import db
from base.pages import (send_message,
                        check_str,
                        Task as TaskOld,
                        TaskQueue)
from base.pages.project.magic import get_project_by_name
from base.pages.admin.form import action_pending, visa_pending, contact_pending
from base.pages.admin.form import activate_user
from base.pages.board.magic import create_resource
from base.pages.user.magic import user_by_id
from base.pages.user.form import edit_info
from base.database.schema import User, Register, LogDB, Project, Tasks, Register
from base.email import Mail
from base.classes import UserLog, RequestLog, TmpUser, ProjectLog, Task
from logging import error, debug
from operator import attrgetter
from datetime import datetime as dt
from base.functions import project_config, ssh_wrapper

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def register_message(rid, form):
    """
    Send message to new registered project responsible. Takes request record ID
    and wtforms object as argument extract data from it and construct dict with
    keys "title", "body" and "destination". Finally in calls pending_message
    method of Mail object with email dict as an argument for this method.
    :param rid: Int. ID of new project request record
    :param form: Object. Copy of WTForms form object
    :return:
    """
    record = get_registration_record(rid)
    pid = record.project_id()
    email = {"title": "[%s] %s" % (pid, form.title.data),
             "body": form.message.data,
             "destination": record.responsible_email}
    return Mail().pending_message(email)


def unprocessed():
    query = Register.query.filter_by(processed=False)
    if "admin" in g.permissions:
        return query.all()

    approve = []
    config = project_config()
    for type in config.keys():
        acl = config[type].get("acl", [])
        if current_user.login in acl:
            approve.append(type)
        elif set(acl).intersection(set(g.permissions)):
            approve.append(type)
    return query.filter(Register.type.in_(approve)).all()


def render_registry(user):
    tasks = Tasks.query.filter_by(user=user).all()
    details = user.details()
    if tasks:
        details["todo"] = list(map(lambda x: x.description(), tasks))
    row = render_template("bits/registry_expand_row.html", user=details)
    edit_form = edit_info(user)
    row += render_template("modals/user_edit_info.html", form=edit_form)
    if not user.active:
        a_form = activate_user(user)
        act = render_template("modals/registry_activate_user.html", form=a_form)
        return row + act
    return row


def render_pending(rec):
    rec.meso = rec.project_id()
    rec.name = "'%s' (%s)" % (rec.title, rec.meso)
    status = rec.status.upper() if rec.status else "NONE"
    if "APPROVED" in status:
        visa = visa_pending(rec)
        top = render_template("modals/admin_visa_pending.html", rec=visa)
    elif "VISA SENT" in status:
        visa = visa_pending(rec)
        top = render_template("modals/admin_visa_received.html", rec=rec)
        top += render_template("modals/admin_visa_pending.html", rec=visa)
    elif "VISA RECEIVED" in status:
        top = render_template("modals/admin_create_project.html", rec=rec)
    elif "VISA SKIPPED" in status:
        top = render_template("modals/admin_create_project.html", rec=rec)
    else:
        top = render_template("modals/admin_approve_pending.html", rec=rec)
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


def visa_comment(rec, sent=True):
    visa_ts = rec.accepted_ts.replace(
        microsecond=0
    ).isoformat("_").replace(":", "-")
    if sent:
        msg = "%s: Visa sent to %s" % (visa_ts, rec.responsible_email)
    else:
        msg = "%s: Visa step has been skipped" % visa_ts
    comments = rec.comment.split("\n")
    comment_list = list(map(lambda x: x.strip(), comments))
    comment_list.append(msg)
    return "\n".join(comment_list)


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


#  Project registration logic below


def accept_message(register, msg):
    to = register.responsible_email
    name = register.responsible_first_name
    surname = register.responsible_last_name
    mid = register.project_id()
    title = "Your project request '%s' has been accepted" % mid
    prefix = "Dear %s %s,\nYour project request '%s' has been accepted by" \
             " scientific committee" % (name, surname, mid)
    if msg:
        msg = prefix + " with following comment:\n" + msg
    else:
        msg = prefix
    return message(to, msg, title)


def reject_message(register, msg):
    to = register.responsible_email
    name = register.responsible_first_name
    surname = register.responsible_last_name
    mid = register.project_id()
    title = "Your project request '%s' has been rejected" % mid
    prefix = "Dear %s %s,\nYour project request '%s' has been rejected with" \
             " following comment:\n\n" % (name, surname, mid)
    msg = prefix + msg
    return message(to, msg, title)


def message(to, msg, title=None):
    by_who = app.config["EMAIL_PROJECT"]
    cc = app.config["EMAIL_PROJECT"]
    if not title:
        title = "Concerning your project"
    return send_message(to, by_who, cc, title, msg)


def reg_accept(pid, note):
    rec = get_registration_record(pid)
    #  TEMP code start here
    p = db.session.query(Project).filter(Project.title.ilike(rec.title)).first()
    if not p:
        raise ValueError("Project with title %s not in ProjectDB!" % rec.title)
    created = p.resources.created
    ProjectLog(p).created(created)
    #  TEMP code ends here
    rec.accepted = True
    rec.accepted_ts = created
    rec.comment = reg_message(rec.comment, "accept") + note
    rec.processed = True
    rec.accepted_ts = created
    db.session.commit()
    RequestLog(rec).accept()
    return accept_message(rec, note)


def reg_reject(pid, note):
    rec = get_registration_record(pid)
    rec.processed = True
    rec.accepted = False
    rec.comment = reg_message(rec.comment, "reject") + note
    rec.accepted_ts = dt.now()
    rec.processed_ts = dt.now()
    db.session.commit()
    RequestLog(rec).reject()
    return reject_message(rec, note)


def reg_message(txt, selector):
    full_name = current_user.full_name()
    if selector == "accept":
        msg = "Project creation request accepted by %s" % full_name
    elif selector == "approve":
        msg = "Project software requirements approved by %s" % full_name
    elif selector == "reject":
        msg = "Project creation request rejected by %s\nReason:\n" % full_name
    elif selector == "ignore":
        msg = "Project creation request ignored by %s" % full_name
    else:
        raise ValueError("Selector %s does not supported" % selector)
    if txt:
        return "%s\n%s" % (txt, msg)
    return msg


def get_registration_record(pid):
    register = Register.query.filter_by(id=pid).first()
    if not register:
        raise ValueError("Project registration request with id %s not found"
                         % pid)
    return register


def get_ltm(data):
    user_tmp = data["user"]
    users = map(lambda x: check_str(x), user_tmp)
    title = check_str(data["title"])
    msg = check_str(data["message"])
    return users, title, msg


def is_user_exists(record):
    from base.database.schema import User

    name = record["name"] if "name" in record else False
    surname = record["surname"] if "surname" in record else False
    email = record["email"] if "email" in record else False
    login = record["login"] if "login" in record else False

    if login:
        result = User.query.filter_by(login=login).first()
    elif email:
        result = User.query.filter_by(email=email).first()
    elif name and surname:
        result = User.query.filter_by(name=name, surname=surname).first()
    else:
        result = User.query.filter_by(login=login, email=email, name=name,
                                      surname=surname).first()

    if result:
        print(result.id)
        record["exists"] = True
    else:
        record["exists"] = False
    return record


def user_create_by_admin(form):
    email = form.email.data.strip().lower()
    if User.query.filter_by(email=email).first():
        raise ValueError("User with e-mail %s has been registered already"
                         % email)

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

    real = filter(lambda x: True if x != "None" else False, form.project.data)
    names = list(real)
    if not names:
        raise ValueError("Can't create a user in not existing project: %s" %
                         ", ".join(form.project.data))
    for name in names:
        project = get_project_by_name(name)
        tid = TaskQueue().project(project).user_create(user).task.id
        TaskOld(tid).accept()
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


def registration_user_new(form):
    pid = form.pid.data
    rec = get_registration_record(pid)
    name = form.user_first_name.data.strip()
    surname = form.user_last_name.data.strip()
    email = form.user_email.data.strip()
    if getattr(form, "user_login", None):
        login = form.user_login.data.strip()
    else:
        login = ""
    new_user = "First Name: %s; Last Name: %s; E-mail: %s; Login: %s" % \
               (name, surname, email, login)
    users = rec.users.split("\n")
    users.append(new_user)
    rec.users = "\n".join(users)
    db.session.commit()
    RequestLog(rec).user_add(new_user)
    return rec.to_dict()


def registration_user_update(form):
    pid = form.pid.data
    uid = form.uid.data
    rec = get_registration_record(pid)
    name = form.user_first_name.data
    surname = form.user_last_name.data
    email = form.user_email.data
    login = form.user_login.data if getattr(form, "user_login", None) else ""
    users = rec.users.split("\n")
    for user in users:
        tmp = md5(user.encode()).hexdigest()
        if tmp != uid:
            continue
        users.remove(user)
        new_user = 'First Name: %s; Last Name: %s; E-mail: %s; Login: %s' % \
                   (name, surname, email, login)
        users.append(new_user)
        RequestLog(rec).user_change(new_user)
    rec.users = "\n".join(users)
    db.session.commit()
    return rec.to_dict()


def registration_info_update(form):
    props = ["title", "cpu", "type", "responsible_first_name",
             "responsible_last_name", "responsible_email",
             "responsible_position", "responsible_lab", "responsible_phone"]
    rid = form.rid.data
    rec = get_registration_record(rid)
    msg = ["Updated"]
    for name in props:
        if name not in form:
            continue
        old = getattr(rec, name)
        item = getattr(form, name)
        new = item.data
        if isinstance(new, str):
            new = new.strip()
            if name is not "title":
                new = new.lower()
        if old != new:
            setattr(rec, name, new)
            msg.append("%s: %s -> %s" % (item.label.text, old, new))
    if db.session.dirty:
        db.session.commit()
        msg = "\n".join(msg)
        RequestLog(rec).request_change(msg)
        return rec.to_dict(), msg
    return rec.to_dict(), "No modifications has been detected"


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


def user_reset_pass(uid):
    user = user_by_id(uid)
    passwd = user.reset_password()
    UserLog(user).password_reset(passwd)
    return "Password for user %s has been changed" % user.login


def process_task(tid, result):
    task = Task(Tasks().query.filter_by(id=tid).first())
    act = task.get_action()
    ent = task.get_entity()

    if act == "create" and ent == "user":
        task.user_create()
    elif act == "create" and ent == "resp":
        task.user_create()
    elif act == "create" and ent == "proj":
        #  After project creation, automatically create a task to create
        #  a responsible and users
        pass
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
    return task.done(result)  # TODO: result of task should be an argument for done methode


class TaskManager:

    def __init__(self):
        from base.database.schema import Tasks

        self.query = Tasks().query
        self.tasks = Tasks

    def history(self, reverse=True):
        # Returns a list of all tasks registered in the system. by default
        # the records are sorted by date in descending order
        tasks = sorted(self.query.all(), key=attrgetter("created"),
                       reverse=reverse)
        return list(map(lambda x: x.to_dict(), tasks)) if tasks else []

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
        self.query = self.query.filter(
            (self.tasks.processed == False) | (self.tasks.processed == None)
        ).filter(
            (self.tasks.done == False) | (self.tasks.done == None)
        )
        tasks = self.query.all()
        return list(map(lambda x: x.to_dict(), tasks)) if tasks else []


def get_server_info(server):
    tmp = {}
    result, err = ssh_wrapper("uptime && free -m", host=server)
    if not result:
        error("Error getting information from the remote server: %s" % err)
        return tmp

    uptime_data = memory_data = swap_data = ""
    for i in result:
        if "load average" in i:
            uptime_data = i
        elif "Mem" in i:
            memory_data = i
        elif "Swap" in i:
            swap_data = i

    uptime = parse_uptime(uptime_data)
    swap = parse_swap(swap_data)
    memory = parse_memory(memory_data)
    total = dict(list(memory.items()) + list(swap.items()))
    return {"server": server, "uptime": uptime, "mem": total}


def parse_uptime(result):
    tmp = {}
    output = result.split(",")
    for i in output:
        if "users" in i:
            users = i.replace("users", "")
            users = users.strip()
            try:
                users = int(users)
            except Exception as err:
                error("Failed to convert to int: %s" % err)
                continue
            tmp["users"] = users
        if "load average" in i:
            idx = output.index(i)
            i = "|".join(output[idx:])
            load = i.replace("load average: ", "")
            load = load.strip()
            loads = load.split("|")
            tmp["load_1"] = loads[0]
            tmp["load_5"] = loads[1]
            tmp["load_15"] = loads[2]
    return tmp


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
            tmp["swap_total"] = swap_total
            tmp["swap_avail"] = swap_available
            tmp["swap_used"] = swap_used
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
            tmp["mem_total"] = mem_total
            tmp["mem_avail"] = mem_available
            tmp["mem_used"] = mem_used
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


def create_project(rid):
    record = get_registration_record(rid)
    reg_name = record.project_id()
    if not record.approve:
        raise ValueError("Project %s has to be approved first!" % reg_name)
    if not record.accepted:
        raise ValueError("Project %s has to be accepted first!" % reg_name)
    record.processed = True
    db.session.commit()
    raise ValueError("Registration record marked as processed. Don't forget to create project!")
    project = Project(
        title=record.title,
        description=record.description,
        scientific_fields=record.scientific_fields,
        genci_committee=record.genci_committee,
        numerical_methods=record.numerical_methods,
        computing_resources=record.computing_resources,
        project_management=record.project_management,
        project_motivation=record.project_motivation,
        active=False,
        comment="Initial commit",
        ref=record,
        privileged=False,
        type=record.type,
        created=dt.now()
    )
    db.session.commit()
    name = project.get_name()
    project.resources = create_resource(project, record.cpu)
