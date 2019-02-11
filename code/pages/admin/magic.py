from flask import current_app
from code.pages import check_int
from logging import error


def remote_project_creation_magic(name, users):
    task_file = current_app.config["TASKS_FILE"]
    task = {"project": name, "users": users}
    with open(task_file, "w") as fd:
        fd.write(task)
    return True


def get_responsible(data):
    from code.database.schema import User

    if not data.responsible_id:
        raise ValueError("Responsible's ID is missing")
    rid = check_int(data["responsible_id"])

    resp = User.query.filter_by(User.id == rid).first()
    if not resp:
        raise ValueError("No responsible's record in DB with id: %s" % rid)
    return resp


def get_users(data):
    from code.database.schema import User

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
