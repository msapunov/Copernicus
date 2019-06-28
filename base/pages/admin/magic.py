from flask import current_app, request
from flask_login import current_user
from base.pages import check_int, ssh_wrapper, send_message, check_str, Task
from base.pages import ProjectLog
from base.pages.project.magic import get_project_by_name
from base.pages.user.magic import get_user_record, user_by_id
from logging import error, debug
from operator import attrgetter
from datetime import datetime as dt
from base import db

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def task_mail(action, task):
    description = task.description()
    tid = task.id
    to = current_app.config["EMAIL_TECH"]
    title = "Task id '%s' has been %sed" % (tid, action)
    msg = "Task '%s' with id '%s' has been %s" % (description, tid, action)
    return message(to, msg, title)


#  Project registration logic below


def remote_project_creation_magic(name, users):
    task_file = current_app.config["TASKS_FILE"]
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
    by_who = current_app.config["EMAIL_PROJECT"]
    cc = current_app.config["EMAIL_PROJECT"]
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


def reg_ignore(pid):
    full_name = current_user.full_name()
    rec = get_registration_record(pid)
    rec.processed = True
    rec.accepted = False
    rec.comment = "Project creation request ignored by %s" % full_name
    rec.accepted_ts = dt.now()
    rec.processed_ts = dt.now()
    return True


def get_registration_record(pid):
    from base.database.schema import Register

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


def get_pid_notes(data):
    pid = check_int(data["pid"])
    note = check_str(data["note"])
    debug("Got pid: %s and note: %s" % (pid, note))
    return pid, note


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
    from base.database.schema import LimboUser

    user = LimboUser()
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

    from base import db
    db.session.commit()

    return user.to_dict_with_acl()


def group_users():
    result = {}

    from base.database.schema import User
    users_obj = User.query.all()
    users_obj = sorted(users_obj, key=attrgetter("login"))
    users = map(lambda x: {"id": x.id, "login": x.login, "name": x.name,
                           "surname": x.surname, "status": x.active,
                           "user": x.acl.is_user, "manager": x.acl.is_manager,
                           "tech": x.acl.is_tech, "admin": x.acl.is_admin,
                           "responsible": x.acl.is_responsible,
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
    for key, value in info.items():
        if hasattr(user, key):
            setattr(user, key, value)


def task_create_user(p_name, user_data, responsible=False):
    project = get_project_by_name(p_name)

    data = user_data.split(" and ")
    login = surname = name = email = ""
    for i in data:
        if "login" in i:
            login = i.replace("login: ", "")
        elif "surname" in i:
            surname = i.replace("surname: ", "")
        elif "name" in i:
            name = i.replace("name: ", "")
        elif "email" in i:
            email = i.replace("email: ", "")
    for i in [login, surname, name, email]:
        if not i:
            raise ValueError("Empty!")

    from base.database.schema import User
    from base.database.schema import ACLDB
    from base import db

    if responsible:
        acl = ACLDB(is_user=True, is_responsible=True, is_manager=False,
                    is_tech=False, is_committee=False, is_admin=False)
    else:
        acl = ACLDB(is_user=True, is_responsible=False, is_manager=False,
                    is_tech=False, is_committee=False, is_admin=False)

    user = User(login=login, name=name, surname=surname, email=email, acl=acl,
                active=True, project=[project], created=dt.now())

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


def task_assign_user(login, p_name):
    project = get_project_by_name(p_name)
    user = get_user_record(login)
    user.project.append(project)
    return ProjectLog(project).user_deleted(user)


def process_task(tid):
    task = Task(tid)
    act, entity, login, project, description = task.action().split("|")
    if act not in ["create", "assign", "update", "remove"]:
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
        pass
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


def get_uptime(server):
    tmp = {}
    result, err = ssh_wrapper("uptime", host=server)
    if not result:
        error("Error getting 'uptime' information: %s" % err)
        return tmp

    for up in result:
        output = up.split(",")
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


def get_mem(server):
    tmp = {}
    result, err = ssh_wrapper("free -m", host=server)
    if not result:
        error("Error getting 'free' information: %s" % err)
        return tmp

    for mem in result:
        output = mem.split(",")
        for i in output:
            if "total" in i:
                continue
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
