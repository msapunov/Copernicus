from flask import request, render_template, current_app as app
from flask_login import current_user
from base import db
from base.pages import (check_int,
                        ssh_wrapper,
                        send_message,
                        check_str,
                        Task,
                        ProjectLog,
                        TaskQueue,
                        ResponsibleMailingList,
                        UserMailingList,
                        calculate_ttl)
from base.pages.project.magic import get_project_by_name
from base.pages.user.magic import get_user_record, user_by_id
from base.utils import get_tmpdir
from base.database.schema import User, ACLDB, Register, LogDB, Project
from base.email import Mail
from logging import error, debug
from operator import attrgetter
from datetime import datetime as dt
from pdfkit import from_string
from pathlib import Path
from base.utils import image_string
import locale


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def parse_register_record(rec):
    result = rec.to_dict()
    result["dt"] = dt.now().strftime("%d/%m/%Y")
    result["ttl"] = calculate_ttl(rec).strftime("%d %B %Y")
    result["type"].upper()
    result["signature"] = image_string("signature.png")
    result["base_url"] = request.url_root
    u_list = Mail().cfg.get("DEFAULT", "USER_LIST", fallback=None)
    r_list = Mail().cfg.get("DEFAULT", "RESPONSIBLE_LIST", fallback=None)
    result["user_list"] = "(%s)" % u_list if u_list else ""
    result["resp_list"] = "(%s)" % r_list if r_list else ""
    return result


def generate_pdf(html, rec):
    ts = str(dt.now().replace(microsecond=0).isoformat("_")).replace(":", "-")
    name = "%s_visa_%s.pdf" % (rec.project_id(), ts)
    path = str(Path(get_tmpdir(app), name))
    debug("The resulting PDF will be saved to: %s" % path)
    pdf = from_string(html, path)
    debug("If PDF converted successfully: %s" % pdf)
    if not pdf:
        raise ValueError("Failed to convert a file to pdf")
    return path


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


def skip_visa(pid):
    record = get_registration_record(pid)
    name = record.project_id()
    if not record.approve:
        raise ValueError("Project %s has to be approved first!" % name)
    record.accepted = True
    record.accepted_ts = dt.now()
    record.comment = visa_comment(record, sent=False)
    db.session.commit()
    return record.comment


def create_visa(pid, force=False):
    record = get_registration_record(pid)
    name = record.project_id()
    if not record.approve:
        raise ValueError("Project %s has to be approved first!" % name)
    if record.accepted and not force:
        raise ValueError("Visa for the project %s has been already sent" % name)
    result = parse_register_record(record)
    loc = app.config.get("LOCALE", "C.UTF-8")
    locale.setlocale(locale.LC_ALL, loc)
    html = render_template("visa.html", data=result)
    path = generate_pdf(html, record)
    Mail().registration(record).send_visa(path)
    Path(path).unlink()
    debug("Temporary file %s was deleted" % path)
    record.accepted = True
    record.accepted_ts = dt.now()
    record.comment = visa_comment(record, sent=True)
    db.session.commit()
    return record.comment


def event_log():
    recs = LogDB().query.all()
    sorted_recs = sorted(recs, key=attrgetter("created"), reverse=True)
    return list(map(lambda x: x.to_web(), sorted_recs))


def task_mail(action, task):
    description = task.description()
    tid = task.id
    to = app.config["EMAIL_TECH"]
    title = "Task id '%s' has been %sed" % (tid, action)
    msg = "Task '%s' with id '%s' has been %s" % (description, tid, action)
    return message(to, msg, title)


#  Project registration logic below


def remote_project_creation_magic(name, users):
    task_file = app.config["TASKS_FILE"]
    task = str({"project": name, "users": users})
    with open(task_file, "w") as fd:
        fd.write(task)
    return True


def get_responsible(data):
    from base.database.schema import User

    if not data.responsible_id:
        raise ValueError("Responsible's ID is missing")
    rid = check_int(data["responsible_id"])

    resp = User.query.filter_by(User.id == rid).first()
    if not resp:
        raise ValueError("No responsible's record in DB with id: %s" % rid)
    return resp


def get_users(data):
    from base.database.schema import User

    if not data.responsible_id:
        raise ValueError("Responsible's ID is missing")
    uids = map(lambda x: check_int(x), data["users"])

    users = []
    for uid in uids:
        user = User.query.filter_by(User.id == uid).first()
        if not user:
            error("No responsible's record in DB with id: %s" % uid)
            continue
        users.append(user)
    return users


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


def approve_message(register):
    to = app.config["EMAIL_PROJECT"]
    by_who = app.config["EMAIL_TECH"]
    cc = app.config["EMAIL_TECH"]
    mid = register.project_id()
    title = "Project request '%s' has been approved by tech team" % mid
    msg = "Software requirements of project request '%s' can be satisfied " \
          "and required application(s) can be or already installed" % mid
    return send_message(to, by_who, cc, title, msg)


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


def project_type(register):
    if register.type_a:
        return "a"
    elif register.type_b:
        return "b"
    elif register.type_c:
        return "c"
    elif register.type_h:
        return "h"
    elif register.type_p:
        return "p"
    else:
        raise ValueError("Failed to determine project's type")


def project_assign_resources(register, approve):
    from base.database.schema import Resources
    resource = Resources(
        approve=approve,
        valid=True,
        cpu=register.cpu,
        type=project_type(register),
    )
    return resource


def project_creation_magic(register, users, approve):
    from base.database.schema import Project

    project = Project(
        title=register.title,
        description=register.description,
        scientific_fields=register.scientific_fields,
        genci_committee=register.genci_committee,
        numerical_methods=register.numerical_methods,
        computing_resources=register.computing_resources,
        project_management=register.project_management,
        project_motivation=register.project_motivation,
        active=True,
        type=project_type(register),
        approve=approve,
        ref=register,
        privileged=True if project_type is "h" else False,
        responsible=users["responsible"],
        users=users["users"]
    )
    return project


def reg_approve(pid):
    rec = get_registration_record(pid)
    rec.approve = True
    rec.approve_ts = dt.now()
    rec.comment = reg_message(rec.comment, "approve")
    db.session.commit()
    return approve_message(rec)


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
    return accept_message(rec, note)


def reg_reject(pid, note):
    rec = get_registration_record(pid)
    rec.processed = True
    rec.accepted = False
    rec.comment = reg_message(rec.comment, "reject") + note
    rec.accepted_ts = dt.now()
    rec.processed_ts = dt.now()
    db.session.commit()
    return reject_message(rec, note)


def reg_ignore(pid):
    rec = get_registration_record(pid)
    rec.processed = True
    rec.accepted = False
    rec.comment = reg_message(rec.comment, "ignore")
    rec.accepted_ts = dt.now()
    rec.processed_ts = dt.now()
    db.session.commit()
    return rec.comment


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


class TmpUser:
    def __init__(self):
        self.login = None
        self.name = None
        self.surname = None
        self.email = None
        self.active = True
        self.is_user = True
        self.is_responsible = False
        self.is_manager = False
        self.is_tech = False
        self.is_committee = False
        self.is_admin = False

    def task_ready(self):
        u_part = "login: %s and name: %s and surname: %s and email: %s" % (
            self.login, self.name, self.surname, self.email)
        a_part = "user: %s, responsible: %s, manager: %s, tech: %s, " \
                 "committee: %s, admin: %s" % (
            self.is_user, self.is_responsible, self.is_manager,self.is_tech,
            self.is_committee, self.is_admin)

        return "%s WITH ACL %s WITH STATUS %s" % (u_part, a_part, self.active)


def user_create_by_admin(form):

    email = form.email.data.strip().lower()
    if User.query.filter(User.email == email).first():
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
        Task(tid).accept()
        msg = "Add a new user: %s '%s %s <%s>'" % (
            user.login, user.name, user.surname, user.email)
        ProjectLog(project).event(msg)
    return "Add creation of the user %s for %s to the execution queue" % (
        user.login, ", ".join(form.project.data))


def user_info_update(form):
    uid = form.uid.data
    user = user_by_id(uid)

    user.name = form.name.data.strip().lower()
    user.surname = form.surname.data.strip().lower()
    user.email = form.email.data.strip().lower()
    user.active = True if form.active.data else False
    user.acl.is_user = True if form.is_user.data else False
    user.acl.is_responsible = True if form.is_responsible.data else False
    user.acl.is_manager = True if form.is_manager.data else False
    user.acl.is_tech = True if form.is_tech.data else False
    user.acl.is_committee = True if form.is_committee.data else False
    user.acl.is_admin = True if form.is_admin.data else False

    names = filter(lambda x: True if x != "None" else False, form.project.data)
    if names:
        user.project = list(map(lambda x: get_project_by_name(x), names))
    else:
        user.project = []

    db.session.commit()
    return user.details()


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
    tid = TaskQueue().user(user).password_reset().task.id
    Task(tid).accept()
    return "Password reset task has been added to execution queue"


def group_users():
    result = {}

    from base.database.schema import User
    users_obj = User.query.all()
    users_obj = sorted(users_obj, key=attrgetter("login"))
    users = map(lambda x: {"id": x.id, "login": x.login, "name": x.name,
                           "surname": x.surname, "status": x.active,
                           "user": x.acl.is_user, "manager": x.acl.is_manager,
                           "tech": x.acl.is_tech, "admin": x.acl.is_admin,
                           "responsible": x.acl.is_responsible, "mail": x.email,
                           "committee": x.acl.is_committee}, users_obj)

    roles = ["user", "manager", "tech", "admin", "committee", "responsible"]
    for user in list(users):
        first = user["login"][0]
        if first not in result:
            result[first] = []
        result[first].append(user)
        for i in roles:
            if not user[i]:
                continue
            if i not in result:
                result[i] = []
            result[i].append(user)
    return result


def task_update_user(login, user_data):
    data = user_data.split(" and ")

    info = {"surname": "", "name": "", "email": ""}
    for i in data:
        if "surname" in i:
            info["surname"] = i.replace("surname: ", "").strip()
        elif "name" in i:
            info["name"] = i.replace("name: ", "").strip()
        elif "email" in i:
            info["email"] = i.replace("email: ", "").strip()

    user = get_user_record(login)

    if "email" in info:
        old_email = user.email
    else:
        old_email = None

    for key, value in info.items():
        if hasattr(user, key):
            setattr(user, key, value)

    if old_email:
        UserMailingList().change(old_email, user.email, user.full_name())
        if user.acl.is_responsible:
            ResponsibleMailingList().change(old_email, user.email,
                                            user.full_name())


def _parse_acl_info(raw):

    tmp = {}
    roles = ["user", "responsible", "manager", "tech", "committee", "admin"]
    data = raw.split(", ")
    for i in data:
        for j in roles:
            if j not in i:
                tmp[j] = False
                continue
            cond = i.replace("%s: " % j, "").strip()
            tmp[j] = True if cond == "True" else False

    return tmp["user"], tmp["responsible"], tmp["manager"], tmp["tech"],\
           tmp["committee"], tmp["admin"]


def _parse_user_info(raw):
    data = raw.split(" and ")
    login = surname = name = email = None
    for i in data:
        if "login" in i:
            login = i.replace("login: ", "")
        elif "surname" in i:
            surname = i.replace("surname: ", "")
        elif "name" in i:
            name = i.replace("name: ", "")
        elif "email" in i:
            email = i.replace("email: ", "")
    if not login:
        raise ValueError("Failed to parse login value")
    if not surname:
        raise ValueError("Failed to parse surname value")
    if not name:
        raise ValueError("Failed to parse name value")
    if not email:
        raise ValueError("Failed to parse email value")
    return login, surname, name, email


def task_create_user(p_name, user_data, responsible=None):
    project = get_project_by_name(p_name)

    if "WITH ACL" not in user_data:
        user_data += " WITH ACL user: True"

    user_part, service_part = user_data.split(" WITH ACL ")
    login, surname, name, email = _parse_user_info(user_part)

    if " WITH STATUS " not in service_part:
        service_part += " WITH STATUS True"

    acl_part, active_part = service_part.split(" WITH STATUS ")
    is_user, is_responsible, is_manager, is_tech, is_committee,\
    is_admin = _parse_acl_info(acl_part)
    active = True if active_part == "True" else False

    acl = ACLDB(is_user=is_user, is_responsible=is_responsible, is_tech=is_tech,
                is_manager=is_manager, is_committee=is_committee,
                is_admin=is_admin)

    user = User(login=login, name=name, surname=surname, email=email, acl=acl,
                active=active, project=[project], created=dt.now())

    db.session.add(acl)
    db.session.add(user)
    return ProjectLog(project).user_added(user)


def task_remove_user(login, p_name):
    project = get_project_by_name(p_name)
    user = get_user_record(login)
    if project not in user.project:
        raise ValueError("Failed to find project %s among %s projects" % (
            p_name, login))
    user.project.remove(project)
    if not user.project:
        user.active = False
    return ProjectLog(project).user_deleted(user)


def task_assign_resp(login, p_name):
    project = get_project_by_name(p_name)
    user = get_user_record(login)
    user.acl.is_responsible = True
    project.responsible = user
    return ProjectLog(project).responsible_added(user)


def task_assign_user(login, p_name):
    project = get_project_by_name(p_name)
    user = get_user_record(login)
    user.project.append(project)
    return ProjectLog(project).user_assigned(user)


def process_task(tid):
    task = Task(tid)
    act, entity, login, project, description = task.action().split("|")
    if act not in ["create", "assign", "update", "remove", "change"]:
        raise ValueError("The action '%s' is not supported" % act)

    if act == "create" and entity == "user":
        log = task_create_user(project, description)
    elif act == "create" and entity == "resp":
        log = task_create_user(project, act, True)
    elif act == "create" and entity == "proj":
        #  After project creation, automatically create a task to create
        #  a responsible and users
        pass
    elif act == "update" and entity == "user":
        log = task_update_user(login, description)
    elif act == "update" and entity == "proj":
        pass
    elif act == "assign" and entity == "user":
        log = task_assign_user(login, project)
    elif act == "assign" and entity == "resp":
        log = task_assign_resp(login, project)
    elif act == "remove" and entity == "user":
        log = task_remove_user(login, project)
    elif act == "remove" and entity == "proj":
        pass

    return task.done()
    #  TODO: return log.event


def task_action(action):
    if action not in ["accept", "reject", "ignore"]:
        raise ValueError("Action %s is unknown" % action)

    task = get_task()
    if action == "reject":
        task_mail("reject", task)
        return task.reject()
    elif action == "ignore":
        return task.ignore()

    task_mail("accept", task)
    task.accept()

    return task


def get_task():
    data = request.get_json()
    if not data:
        raise ValueError("Expecting application/json requests")
    tid = check_int(data["task"])

    task = Task(tid)
    if not task:
        raise ValueError("No task with id %s found" % tid)
    if task.is_processed():
        raise ValueError("Task with id %s has been already processed" % tid)
    return task


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
