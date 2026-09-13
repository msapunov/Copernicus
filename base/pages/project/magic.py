"""Business logic for project management: suspension, expiry, user management,
activity reports, renewals, extensions, and transformations.
"""

from datetime import datetime as dt
from datetime import timezone
from logging import debug, error
from pathlib import Path

from flask import current_app, g, render_template, request
from flask_login import current_user
from webdav3.client import Client
from werkzeug.utils import secure_filename

from base import db
from base.classes import ProjectLog, Task, TaskQueue, TmpUser, UserLog
from base.database.schema import Extend, File, Project, Tasks, User
from base.functions import (
    calculate_ttl,
    form_error_string,
    get_field_value,
    parse_moment,
    ssh_check,
    ssh_wrapper,
    upload_to_cloud,
    write_pdf,
)
from base.pages import generate_login
from base.pages.board.magic import create_resource
from base.pages.user.magic import user_by_id


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


def suspend_expired_projects(projects):
    """Deactivate projects whose resources have expired.

    Compares each project's TTL against the current time and deactivates
    expired projects.

    Args:
        projects: List of Project instances to check.
    """
    now = dt.now().replace(tzinfo=timezone.utc)
    for project in projects:
        finish = project.resources.ttl
        if finish > now:
            continue
        project.active = False
        debug("%s: suspended due to resource expiration %s" %
              (project.name, finish.isoformat()))
        ProjectLog(project).expired()
    if db.session.new or db.session.dirty or db.session.deleted:
        db.session.commit()


def warn_expired_projects(projects, config):
    """Send expiration warnings for projects nearing their end date.

    Checks each project's TTL against the ``finish_notice_dt`` configured
    for its type and sends a warning if within the notice period and if
    no warning has been sent yet.

    Args:
        projects: List of Project instances to check.
        config: Project configuration dictionary.
    """
    now = dt.now().replace(tzinfo=timezone.utc)
    for project in projects:
        finish = project.resources.ttl
        ptype = project.type
        if ptype not in config:
            continue
        warn = config[ptype].get("finish_notice_dt", "")
        if not warn:
            debug("No warning date has been defined, skipping notification")
            continue
        if warn <= now < finish:
            debug("Expiring %s, %s" % (project.name, finish.isoformat()))
            debug("Checking if warning has been send already")
            log = ProjectLog(project)
            logs = log.after(warn).list()
            debug("List of log events found: %s" % logs)
            was_sent = list(filter(lambda x: "Expiring" in x.event, logs))
            debug("Events with word Expiring found: %s" % was_sent)
            if not was_sent:
                debug("Sending warning cause no previous warning events found")
                log.expire_warning()
    db.session.commit()


def suspend_overconsumed_projects(projects):
    """Placeholder: suspend projects that have over-consumed resources."""


def warn_overconsumed_projects(projects):
    """Placeholder: warn about projects that have over-consumed resources."""


def consumption_check(projects):
    """Placeholder: check consumption across all projects."""


def active_users_check(projects):
    """Find projects with inactive users.

    Args:
        projects: List of Project instances.

    Returns:
        Dictionary mapping projects to lists of inactive user logins.
    """
    result = {}
    for project in projects:
        for user in project.users:
            if not user.active:
                if project not in result:
                    result[project] = []
                result[project].append(user.login)
    return result


def sanity_check():
    """Run a health check across all active projects.

    Checks active user status, suspends expired projects, and checks
    for overconsumption.

    Returns:
        Summary string listing any inactive users found, or
        ``"Sanity check done"``.
    """
    cfg = g.project_config
    projects = (
        Project.query
        .filter(Project.active.is_(True))
        .with_for_update()
        .all()
    )
    users = active_users_check(projects)
    suspend_expired_projects(projects)
#    warn_expired_projects(projects, cfg)
    suspend_overconsumed_projects(projects)
#    warn_overconsumed_projects(projects)
    consumption_check(projects)
    if users:
        return ", ".join(f"{k}: {' '.join(map(str, v))}" for k, v in users.items())
    return "Sanity check done"


def active_check():
    """Compare project active status in the database against SLURM data.

    Expects raw POST data with ``project_name|state`` lines.

    Returns:
        String describing any inconsistencies found.
    """
    result = []
    projects = db.session.query(Project).all()
    raw_data = request.get_data()
    if not raw_data:
        return "No data received"
    cook_data = raw_data.decode("utf-8", errors="replace").split("\n")
    data = dict(map(lambda x: x.split("|"), cook_data))
    for project in projects:
        name = project.name
        if name not in data:
            if project.active:
                result.append("Project %s have no QOS but it's active" % name)
            continue
        if data[name] == 0 and project.active:
            result.append("Project %s banned in SLURM but active in DB" % name)
            continue
        if not data[name] and not project.active:
            result.append("Project %s active in SLURM but banned in DB" % name)
            continue
    if result:
        return "\n".join(result)
    return "Project status check done"


def project_attach_user(project, form):
    """Attach an existing user to a project.

    Creates a task queue entry for assigning or activating the user,
    and auto-processes it if the current user is an admin.

    Args:
        project: Project instance.
        form: UserForm with a ``login`` field containing the user ID.

    Returns:
        The event string from the project log.
    """
    uid = form.login.data
    user = User.query.filter(User.id == uid).first()
    if not user:
        raise ValueError("Failed to find user with ID '%s' in database" % uid)
    if user in project.users:
        raise ValueError("User %s has been already attached to project %s"
                         % (user.full(), project.get_name()))
    if user.active:
        task = TaskQueue().project(project).user_assign(user).task
    else:
        task = TaskQueue().project(project).user_activate(user).task
    if "admin" in current_user.permissions():
        Task(task).accept()
    if user.active:
        return ProjectLog(project).user_assign(task)
    return ProjectLog(project).user_activate(task)


def project_create_user(project, form):
    """Create a new user from form data and queue the creation task.

    Validates input, checks for duplicate emails, generates a login,
    and optionally uploads an SSH public key.

    Args:
        project: Project instance.
        form: UserForm with name/surname/email/key data.

    Returns:
        The event string from the project log.
    """
    ssh_upload = get_project_option(project, "ssh_upload")
    add_users = get_project_option(project, "add_users")
    tmp_users = get_project_option(project, "tmp_users")
    prenom = get_field_value(form, "prenom").lower()
    surname = get_field_value(form, "surname").lower()
    email = get_field_value(form, "email").lower()
    if not all((prenom, surname, email)):
        raise ValueError("Name, Surname and Email are required")
    key = get_field_value(form, "key")
    if ssh_upload and key:
        ssh_check(key)
    if User.query.filter(User.email == email).first():
        raise ValueError("User with e-mail %s has been registered already"
                         % email)
    user = TmpUser()
    user.login = generate_login(prenom, surname)
    user.name = prenom
    user.surname = surname
    user.email = email
    if tmp_users:
        user.comment = "TEMPORARY USER"
    task = TaskQueue().project(project).user_create(user).task
    if current_user.login and "admin" in current_user.permissions() or add_users:
        task.accept()
    if ssh_upload and key:
        ssh_task = TaskQueue()
        ssh_task.u_name = user.login
        ssh_task.key_upload(key)
        ssh_task.task.user = current_user
        ssh_task.task.accept()
        UserLog(current_user).key_upload(key)
    return ProjectLog(project).user_create(task)


def check_responsible(name):
    """Verify that the current user is the responsible person for a project.

    Args:
        name: Project name.

    Returns:
        The Project instance.

    Raises:
        ValueError: If the current user is not the project responsible.
    """
    project = get_project_by_name(name)
    if current_user != project.responsible:
        raise ValueError("User %s is not register as the responsible person "
                         "for the project %s" % (current_user.login, name))
    return project


def assign_responsible(name, form):
    """Assign a new responsible person to a project.

    Admins can assign any user; non-admins can only assign existing
    project users.

    Args:
        name: Project name.
        form: ResponsibleForm with the new responsible user ID.

    Returns:
        The event string from the project log.
    """
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    uid = form.login.data
    send = form.send.data
    user = user_by_id(uid)
    if "admin" in current_user.permissions():
        project = get_project_by_name(name)
    else:
        project = check_responsible(name)
    if user == project.responsible:
        raise ValueError("User %s is already responsible for the project %s" %
                         (user.full_name(), project.get_name()))
    if "admin" in current_user.permissions():
        task = TaskQueue().project(project).responsible_assign(user).task
        Task(task).accept()
        return ProjectLog(project).send_message(send).responsible_assign(task)
    if user not in project.users:
        raise ValueError("New responsible has to be one of the project users")
    task = TaskQueue().project(project).responsible_assign(user).task
    return ProjectLog(project).responsible_assign(task)


def get_activity_files(name):
    """Find activity-related temporary files for a project.

    Args:
        name: Project name.

    Returns:
        List of Path objects matching the project name pattern.
    """
    temp_dir = current_app.get_tmpdir()
    debug("Using temporary directory to store files: %s" % temp_dir)
    pattern = "*%s*" % name
    debug("Pattern %s to get associated files for %s" % (pattern, name))
    already = list(Path(temp_dir).glob(pattern))
    debug("List of existing files: %s" % already)
    return already


def save_activity(req):
    """Save an uploaded activity file to the temporary directory.

    Enforces a configurable upload limit per project.

    Args:
        req: The incoming Flask request.

    Returns:
        Dictionary with ``saved_name`` and ``incoming_name`` keys.
    """
    limit = current_app.config.get("ACTIVITY_REPORT_LIMIT", 3)
    project = req.form.get("project", None)
    if not project:
        raise ValueError("No project name provided!")
    check_responsible(project)
    files = get_activity_files(project)
    if len(files) >= limit:
        raise ValueError("You have already uploaded %s or more files" % limit)
    if "file" not in req.files:
        raise ValueError("Missing 'file' in uploaded data.")
    file = req.files["file"]
    if not file.filename:
        raise ValueError("Uploaded file has no name.")
    original = secure_filename(file.filename)
    stamp = dt.now().strftime("%Y-%m-%d")
    new_name = f"{project}-{stamp}.{original}"
    debug(f"New name for the file: {new_name}")
    path = Path(current_app.get_tmpdir())
    path.mkdir(parents=True, exist_ok=True)
    save_path = path / new_name
    debug(f"Saving file to: {save_path}")
    file.save(save_path)
    return {"saved_name": new_name, "incoming_name": file.filename}


def save_report(project):
    """Generate and save a PDF activity report for a project.

    Optionally uploads the report (and images) to a cloud storage.

    Args:
        project: Project instance.

    Returns:
        The File record for the saved report.
    """
    project_name = project.get_name()
    html = render_template("report.html", data=project)
    stamp = int(dt.now().timestamp())
    path = write_pdf(html, f"{project_name}-activity-report-{stamp}.pdf")
    if current_app.config.get("ACTIVITY_UPLOAD", False):
        debug("Uploading report to a cloud storage")
        remote_directory = current_app.config.get("ACTIVITY_DIR", "/")
        if current_app.config.get("ACTIVITY_UPLOAD_IMG", False):
            for i in ["image_1", "image_2", "image_3"]:
                tmp = getattr(project, i, None)
                upload_to_cloud(remote_directory, tmp) if tmp else False
        upload_to_cloud(remote_directory, path)
    report = File(
        path=str(path),
        size=Path(path).stat().st_size,
        comment="Activity report",
        user=current_user,
        project=project,
        created=dt.now(timezone.utc),
    )
    db.session.add(report)
    project.resources.file = report
    db.session.commit()
    debug("Activity report saved to the file %s" % report.path)
    return report


def report_activity(name, form):
    """Process an activity report submission.

    Args:
        name: Project name.
        form: ActivityForm with report data.

    Returns:
        The File record for the saved report.
    """
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    project = check_responsible(name)
    project.report = form.report.data
    project.doi = form.doi.data
    project.training = form.training.data
    project.hiring = form.hiring.data
    project.generated = dt.strftime(dt.now(timezone.utc), "%c")
    tmp = current_app.get_tmpdir()
    for i in ["image_1", "image_2", "image_3"]:
        path = Path(tmp, form[i].data)
        if path.exists() and path.is_file():
            setattr(project, i, str(path.resolve()))
        else:
            error("Path for image doesn't exists: %s" % path.resolve())
    debug(project)
    return save_report(project)


def remove_activity(name, file_name):
    """Remove an uploaded activity file.

    Args:
        name: Project name.
        file_name: Name of the file to remove.

    Returns:
        True if the file was removed or did not exist.
    """
    check_responsible(name)
    temp_dir = current_app.get_tmpdir()
    path = Path(temp_dir) / file_name
    if not path.exists():
        debug("Path doesn't exists: %s" % str(path))
        return True
    if path.is_file():
        path.unlink()
        debug("File deleted: %s" % file_name)
        return True
    if path.is_dir():
        error("Path %s is a directory and can't be removed" % str(path))
        return False


def clean_activity(name):
    """Remove all uploaded activity files for a project.

    Args:
        name: Project name.

    Returns:
        True if cleaned successfully.
    """
    debug("Cleaning activity files for project %s" % name)
    check_responsible(name)
    files = get_activity_files(name)
    if len(files) < 1:
        return True
    for x in files:
        x.unlink()
        debug("File deleted: %s" % str(x))
    return True


def renew_project(pid, ext, date):
    """Process a project renewal: create new resources.

    Args:
        pid: Extension ID (unused, for logging).
        ext: Extend record.
        date: Date string for the comment.

    Returns:
        The event string from the project log.
    """
    ext.project.resources.valid = False
    if ext.hours == 0:
        new_hours = ext.project.resources.cpu
    else:
        new_hours = ext.hours
    ext.project.resources = create_resource(ext.project, new_hours)
    msg = "Created based on renewal request ID %s on %s" % (pid, date)
    ext.project.resources.comment = msg
    ext.project.active = True
    return ProjectLog(ext.project).renewed(ext)


def extend_project(pid, ext, date):
    """Process a project extension: add CPU hours and extend TTL.

    Args:
        pid: Extension ID.
        ext: Extend record.
        date: Date string for the comment.

    Returns:
        The event string from the project log.
    """
    ext.project.resources.ttl = calculate_ttl(ext.project.type)
    ext.project.resources.cpu += ext.hours
    ext.project.resources.valid = True
    msg = "CPU value has been extended to %s hours on %s based upon "\
          "extension request ID %s" % (ext.hours, date, pid)
    old_comment = ext.project.resources.comment
    comment = old_comment.split("\n") if old_comment else []
    comment.append(msg)
    ext.project.resources.comment = "\n".join(comment)
    ext.project.active = True
    return ProjectLog(ext.project).extended(ext)


def transform_project(ext, date):
    """Process a project transformation: change type and create new resources.

    Args:
        ext: Extend record.
        date: Date string for the comment.

    Returns:
        The event string from the project log.
    """
    ext.project.type = ext.transform
    ext.project.name = "%s%s" % (ext.transform, str(ext.project.id).zfill(3))
    ext.project.resources.valid = False
    ext.project.resources = create_resource(ext.project, ext.hours)
    msg = "Created based on transformation request ID %s on %s" % (ext.id, date)
    ext.project.resources.comment = msg
    ext.project.active = True
    return ProjectLog(ext.project).transformed(ext)


def activate_project(eid, ext, date):
    """Process a project activation.

    Args:
        eid: Extension ID.
        ext: Extend record.
        date: Date string for the comment.

    Returns:
        The event string from the project log.
    """
    ext.project.resources.valid = False
    ext.project.resources = create_resource(ext.project, ext.hours)
    msg = "Created based on activation request ID %s on %s" % (eid, date)
    ext.project.resources.comment = msg
    ext.project.users = [ext.project.responsible]
    ext.project.active = True
    return ProjectLog(ext.project).activated(ext)


def process_extension(eid):
    """Process an extension/renewal/transformation request based on its type.

    Examines the Extend record and dispatches to the appropriate handler.

    Args:
        eid: Extension ID.

    Returns:
        The event string from the project log.
    """
    ext = Extend.query.filter_by(id=eid).first()
    if not ext:
        raise ValueError("Failed to find extension record with id '%s'" % eid)
    ext.done = True
    date = dt.now().replace(microsecond=0).isoformat(" ")
    never_extend = current_app.config.get("NO_EXTENSION_TYPE", [])
    never_renew = current_app.config.get("NO_RENEWAL_TYPE", [])
    if ext.transform.strip() != "":
        return transform_project(ext, date)
    if ext.project.type in never_extend:
        return renew_project(eid, ext, date)
    if ext.project.type in never_renew:
        return extend_project(eid, ext, date)
    if ext.activate:
        return activate_project(eid, ext, date)
    if not ext.extend:
        return renew_project(eid, ext, date)
    return extend_project(eid, ext, date)


def get_users(project=None):
    """Return the list of users belonging to a project, or all users.

    Args:
        project: Optional Project instance. If provided, returns users
            of that project including future (queued) users.

    Returns:
        List of User objects.
    """
    if project:
        get_future_users([project])
        return project.users
    else:
        return User.query.all()


def get_future_users(projects):
    """Augment project user lists with users pending creation from tasks.

    For each project, finds pending ``create|user`` tasks and adds them
    as ``trans_users`` attribute on the project.

    Args:
        projects: List of Project instances.
    """
    for project in projects:
        recs = Tasks.query.filter_by(processed=False, project=project).all()
        if not recs:
            continue
        tasks = list(filter(lambda x: "create|user" in x.action, recs))
        f_users = [TmpUser().from_description(task.action) for task in tasks]
        for user in project.users:
            f_users = [x for x in f_users if x.login != user.login]

        if f_users:
            project.trans_users = f_users
    return projects


def get_project_by_name(name):
    """Find a project by its name.

    Args:
        name: Project name.

    Returns:
        The Project instance.

    Raises:
        ValueError: If no project with the given name is found.
    """
    projects = Project.query.all()
    for project in projects:
        if project.get_name() != name:
            continue
        return project
    raise ValueError("Failed to find a project with name '%s'" % name)


def get_project_record(pid):
    """Find a project by its database ID.

    Args:
        pid: Project ID.

    Returns:
        The Project instance.

    Raises:
        ValueError: If no project with the given ID is found.
    """
    project = Project.query.filter_by(id=pid).first()
    if not project:
        raise ValueError("Failed to find project with id '%s'" % pid)
    return project


def project_transform(name, form):
    """Initiate a project transformation request.

    Args:
        name: Project name.
        form: TransForm with new type, CPU, and note.

    Returns:
        The created Extend record.
    """
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    new = form.new.data
    cpu = form.cpu.data
    note = form.note.data
    project = check_responsible(name)
    possible_types = get_transformation_options(project.type)
    possible_types = list(map(lambda x: x[0], possible_types))
    if new not in possible_types and "admin" not in g.permissions:
        raise ValueError("Configuration forbids transformation to %s" % new)
    record = Extend(
        project=project,
        hours=cpu,
        reason=note,
        extend=True,
        present_use=project.account(),
        transform=new,
        usage_percent=project.consumed_use(),
        present_total=project.resources.cpu,
        exception=False,
    )
    db.session.add(record)
    db.session.commit()
    return record


def project_renew(project, form, active=False):
    """Initiate a project renewal request.

    Args:
        project: Project instance.
        form: RenewForm with CPU and note.
        active: If True, skip renewable check for activation.

    Returns:
        The created Extend record.
    """
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    cpu = form.cpu.data
    note = form.note.data
    if active and project.active:
        raise ValueError("Project %s already active" % project.get_name())
    project = is_project_renewable(project)
    if not active and not project.is_renewable and "admin" not in g.permissions:
        raise ValueError("Project %s is not renewable" % project.get_name())
    record = Extend(
        project=project,
        hours=cpu,
        reason=note,
        extend=False,
        present_use=project.account(),
        usage_percent=project.consumed_use(),
        present_total=project.resources.cpu,
        exception=False,
    )
    db.session.add(record)
    db.session.commit()
    return record


def project_extend(name, form):
    """Initiate a project extension request.

    Args:
        name: Project name.
        form: ExtendForm with exception, CPU, and note.

    Returns:
        The created Extend record.
    """
    if not form.validate_on_submit():
        raise ValueError(form_error_string(form.errors))
    exception = form.exception.data
    cpu = form.cpu.data
    note = form.note.data
    project = check_responsible(name)
    project = is_project_extendable(project)
    if not project.is_extendable and "admin" not in g.permissions:
        raise ValueError("Project %s is not extendable" % name)
    record = Extend(
        project=project,
        hours=cpu,
        reason=note,
        extend=True,
        present_use=project.account(),
        usage_percent=project.consumed_use(),
        present_total=project.resources.cpu,
        exception=exception,
    )
    db.session.add(record)
    db.session.commit()
    return record


def is_activity_report(project):
    """Check whether an activity report has been uploaded and is valid.

    Verifies that the report file exists within the valid time window
    and optionally checks remote cloud storage.

    Args:
        project: Project instance.

    Returns:
        True if a valid activity report exists.

    Raises:
        ValueError: If the report is outdated.
    """
    if (not project.resources) or (not project.resources.file):
        return False
    cfg = g.project_config
    finish_dt = cfg[project.type].get("finish_dt", None)
    report_dt = cfg[project.type].get("finish_report_dt", None)
    file_dt = project.resources.file.created.replace(tzinfo=timezone.utc)
    if (report_dt and finish_dt) and not (report_dt < file_dt < finish_dt):
        raise ValueError("Please upload the most recent activity report")
    name = project.resources.file.name()
    debug("Activity file name is: %s" % name)
    if not current_app.config.get("ACTIVITY_UPLOAD", False):
        return True
    url = current_app.config.get("OWN_CLOUD_URL", None)
    login = current_app.config.get("OWN_CLOUD_LOGIN", None)
    password = current_app.config.get("OWN_CLOUD_PASSWORD", None)
    options = {
        "webdav_hostname": url,
        "webdav_login": login,
        "webdav_password": password,
    }
    client = Client(options)
    remote_dir = current_app.config.get("ACTIVITY_DIR", "/")
    if not remote_dir.endswith("/"):
        remote_dir += "/"
    remote = remote_dir + name
    debug("Checking is file %s exists" % remote)
    if client.check(remote):
        debug("File exists on remote server")
        return True
    debug("File does not exist on remote server")
    return False


def list_of_projects():
    """Return a sorted list of all project names.

    Returns:
        Sorted list of project name strings.
    """
    projects = map(lambda x: x.get_name(), Project.query.all())
    return sorted(list(projects))


def set_state(pid, state):
    """Set the active state of a project.

    Args:
        pid: Project ID.
        state: Boolean active state.

    Returns:
        The project's ``to_dict()`` representation.
    """
    project = get_project_record(pid)
    if type(state) != bool:
        ValueError("Argument state is not boolean: %s" % state)
    project.active = state
    db.session.commit()
    return project.to_dict()


def is_project_extendable(project):
    """Check whether a project type allows extension.

    Looks for the ``evaluation_dt`` or ``extendable`` configuration
    options for the project's type and sets ``is_extendable`` accordingly.

    Args:
        project: Project instance.

    Returns:
        The Project instance with ``is_extendable`` set.
    """
    cfg = g.project_config
    ptype = project.type
    eva = cfg[ptype].get("evaluation_dt", None) if ptype in cfg else None
    debug(f"{project.name} - evaluation_dt option for type {ptype}: {eva}")
    ext = cfg[ptype].get("extendable", False) if ptype in cfg else None
    debug(f"{project.name} - extendable option for type {ptype}: {ext}")
    if eva or ext:
        project.is_extendable = True
    else:
        project.is_extendable = False
    debug(f"{project.name} - is project extendable: {project.is_extendable}")
    return project


def is_project_renewable(project):
    """Check whether a project is currently in its renewal window.

    Uses ``renew_start`` and ``renew_close`` configuration options to
    determine the renewal period.

    Args:
        project: Project instance.

    Returns:
        The Project instance with ``is_renewable`` set.
    """
    now = dt.now(timezone.utc)
    if not get_project_option(project, "renewable"):
        debug(
            f"{project.name} - No renewable option found in config file"
            f"for type {project.type} projects"
        )
        project.is_renewable = False
        return project
    start = get_project_option(project, "renew_start")
    close = get_project_option(project, "renew_close")
    if not any((close, start)):
        debug(
            f"{project.name} - Either renew_start or renew_close is absent"
            f"in configuration file"
        )
        project.is_renewable = False
        return project
    debug(f"{project.name} - configured renew timeframe: {start} to {close}")
    debug(f"{project.name} - converting {start} to datetime")
    begin = parse_moment(start)
    debug(f"{project.name} - converting {close} to datetime")
    end = parse_moment(close)
    if begin < now <= end:
        project.is_renewable = True
    else:
        project.is_renewable = False
    debug(f"{project.name} - is project renewable: {project.is_renewable}")
    return project


def get_add_users_options(project):
    """Check if the ``add_users`` option is enabled for the project type.

    Args:
        project: Project instance.

    Returns:
        The Project instance with ``add_users`` set.
    """
    cfg = g.project_config
    ptype = project.type
    if ptype in cfg:
        project.add_users = cfg[ptype].get("add_users", False)
    return project


def get_ssh_options(project):
    """Check if the ``ssh_upload`` option is enabled for the project type.

    Args:
        project: Project instance.

    Returns:
        The Project instance with ``ssh_upload`` set.
    """
    cfg = g.project_config
    ptype = project.type
    if ptype in cfg:
        project.ssh_upload = cfg[ptype].get("ssh_upload", False)
    else:
        project.ssh_upload = False
    return project


def get_reservation_options(project):
    """Check and populate reservation options for a project.

    Args:
        project: Project instance.

    Returns:
        The Project instance with ``reservation`` set.
    """
    cfg = g.project_config
    ptype = project.type
    if cfg.get(ptype, {}).get("reservation"):
        project.reservation = get_reservation(project.name)
    else:
        project.reservation = False
    return project


def get_transformation_options(project_type=None):
    """Return available transformation targets for a project type.

    Args:
        project_type: Optional project type to filter options for.

    Returns:
        List of (type, description) tuples.
    """
    cfg = g.project_config
    options = []
    for name in cfg.keys():
        desc = cfg[name].get("description", None)
        options.append((name.lower(), desc if desc else name))

    if (not project_type) or (project_type not in cfg.keys()):
        return options

    trans = cfg[project_type].get("transform", None)
    if not trans:
        return []

    options_copy = options.copy()
    for option in options_copy:
        if option[0] not in trans:
            options.remove(option)
    return options


def is_project_transformable(project):
    """Check whether a project can be transformed to another type.

    Args:
        project: Project instance.

    Returns:
        The Project instance with ``is_transformable`` set.
    """
    trans = get_transformation_options(project.type)
    if trans:
        project.is_transformable = True
    else:
        project.is_transformable = False
    return project


def get_reservation(name):
    """Query SLURM reservations associated with a project.

    Args:
        name: Project name.

    Returns:
        List of dictionaries with reservation details, or a single
        "No reservations found" message.
    """

    def parse(text, prop):
        """Extract a property value from a SLURM scontrol output line.

        Finds all characters that match the property prefix and removes
        the prefix to get the value.

        Args:
            text: A line from scontrol output.
            prop: The property prefix (e.g. ``ReservationName=``).

        Returns:
            The extracted value string.
        """
        element = "".join([s for s in text if prop in s])
        return element.replace(prop, "")

    cmd = f"scontrol show reservation -o | grep Accounts={name}"
    result, err = ssh_wrapper(cmd)
    if not result:
        return ["No reservations found"]
    if err:
        return [err]
    output = []
    for line in result:
        el = line.split(" ")
        output.append(
            {
                "name": parse(el, "ReservationName="),
                "start": parse(el, "StartTime=").replace("T", " "),
                "end": parse(el, "EndTime=").replace("T", " "),
                "duration": parse(el, "Duration="),
                "nodes": parse(el, "NodeCnt="),
                "cores": parse(el, "CoreCnt="),
            }
        )
    return output


def get_project_option(project, option_name):
    """Retrieve an option from project configuration based on project type.

    Missing values default to False.

    Args:
        project: Project instance with a ``type`` attribute.
        option_name: Configuration key name.

    Returns:
        The option value, or False by default.
    """
    cfg = g.project_config
    return cfg.get(project.type, {}).get(option_name, False)