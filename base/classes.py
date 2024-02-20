from flask import g
from flask_login import current_user
from base import db
from base.pages import TaskQueue
from base.functions import create_visa, calculate_ttl
from base.email import Mail, UserMailingList, ResponsibleMailingList
from base.database.schema import (LogDB, User, ACLDB, Extend, Register, Project,
                                  Resources, ArticleDB, Tasks)
from logging import debug
from operator import attrgetter
from datetime import datetime as dt
from pathlib import Path


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class Log:

    def __init__(self, project=None, register=None, user=None):
        self.log = LogDB(
            event="",
            author=current_user,
            project=project,
            register=register,
            user=user)
        self.query = LogDB().query
        self.send = True

    def before(self, date):
        self.query = self.query.filter_by(LogDB.created < date)
        return self.list()

    def after(self, date):
        self.query = self.query.filter_by(LogDB.created >= date)
        return self.list()

    def list(self):
        query = self.query
        if self.log.project:
            query = query.filter_by(project=self.log.project)
        if self.log.register:
            query = query.filter_by(register=self.log.register)
        if self.log.user:
            query = query.filter_by(user=self.log.user)
        return query.all()

    def commit(self, mail=None):
        db.session.add(self.log)
        db.session.commit()
        Mail().log(self.log).start()
        try:
            if mail and self.send:
                mail.start()
        finally:
            return self.log.event


class ProjectLog(Log):

    def __init__(self, project):
        super().__init__(project=project)
        self.project = project
        self.send = True

    def send_message(self, send=True):
        if send:
            self.send = True
        else:
            self.send = False
        return self

    def created(self):
        rid = self.project.ref.project_id()
        self.log.event = "Project created out of request %s" % rid
        return self.commit(Mail().project_new(self.project))

    def user(self, user):
        self.log.user = user
        return self

    def responsible_assign(self, task):
        self.log.event = "Made a request to assign new responsible %s" \
                         % task.user.full()
        return self.user(task.user).commit(Mail().responsible_assign(task))

    def responsible_assigned(self, task):
        self.log.event = "Assigned a new project responsible %s" \
                         % task.user.full()
        return self.user(task.user).commit(Mail().responsible_assigned(task))

    def responsible_attached(self, task):
        self.log.event = "Attached responsible %s" % task.user.full()
        return self.user(task.user).commit(Mail().responsible_attached(task))

    def user_new(self, task):
        user = task.user
        self.log.event = "User %s has been created" % user.full()
        return self.commit(Mail().user_new(user))

    def user_create(self, task):
        user = TmpUser().from_task(Task(task))
        user.task = task
        self.log.event = "Made a request to create a user %s" % user.full()
        return self.commit(Mail().user_create(user))

    def user_created(self, task):
        user = TmpUser().from_task(Task(task))
        user.task = task
        self.log.event = "User %s has been created" % user.full()
        return self.commit(Mail().user_created(user))

    def user_activate(self, task):
        self.log.event = "Made a request to activate a user %s" % task.user.full()
        return self.user(task.user).commit(Mail().user_activate(task))

    def user_activated(self, task):
        self.log.event = "User %s has been activated" % task.user.full()
        return self.user(task.user).commit(Mail().user_activated(task))

    def user_assign(self, task):
        self.log.event = "Made a request to assign a user %s" % task.user.full()
        return self.user(task.user).commit(Mail().user_assign(task))

    def user_assigned(self, task):
        self.log.event = "User %s has been assigned" % task.user.full()
        return self.user(task.user).commit(Mail().user_assigned(task))

    def user_attached(self, task):
        self.log.event = "User %s has been assigned" % task.user.full()
        return self.user(task.user).commit(Mail().user_attached(task))

    def user_delete(self, task):
        self.log.event = "Made a request to delete user %s" % task.user.full()
        return self.user(task.user).commit(Mail().user_delete(task))

    def user_deleted(self, task):
        self.log.event = "User %s has been deleted" % task.user.full()
        return self.user(task.user).commit(Mail().user_deleted(task))

    def renew(self, extension):
        article = "an exceptional" if extension.exception else "a"
        self.log.event = "Made %s request to renew project for %s hour(s)" \
                         % (article, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().project_renew(extension))

    def renewed(self, extension):
        self.log.event = "Renewal request for %s hour(s) has been processed" \
                         % extension.hours
        self.log.extension = extension
        return self.commit(Mail().project_renewed(extension))

    def extend(self, extension):
        article = "an exceptional" if extension.exception else "a"
        self.log.event = "Made %s request to extend project for %s hour(s)" \
                         % (article, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().project_extend(extension))

    def extended(self, extension):
        self.log.event = "Extension request for %s hour(s) has been processed" \
                         % extension.hours
        self.log.extension = extension
        return self.commit(Mail().project_extended(extension))

    def transform(self, extension):
        self.log.event = "Transformation request has been registered"
        self.log.extension = extension
        return self.commit(Mail().project_transform(extension))

    def transformed(self, extension):
        self.log.event = "Transformation to type %s finished successfully" \
                         % extension.transform
        self.log.extension = extension
        return self.commit(Mail().project_transformed(extension))

    def activate(self, extension):
        self.log.event = "Activation request has been registered"
        self.log.extension = extension
        return self.commit(Mail().project_activate(extension))

    def activated(self, extension):
        self.log.event = "Activation request has been processed"
        self.log.extension = extension
        return self.commit(Mail().project_activated(extension))

    def accept(self, extension):
        prefix = self._prefix(extension)
        self.log.event = "%s request for %s hours is accepted" \
                         % (prefix, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_accepted(extension, prefix))

    def ignore(self, extension):
        prefix = self._prefix(extension)
        self.log.event = "%s request for %s hours is ignored" \
                         % (prefix, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_ignored(extension, prefix))

    def reject(self, extension):
        prefix = self._prefix(extension)
        self.log.event = "%s request for %s hours is rejected" \
                         % (prefix, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_rejected(extension, prefix))

    def activity_report(self, file_rec):
        file_name = file_rec.path
        self.log.event = "Activity report saved on the server in the file %s" \
                         % file_name
        mail = Mail().report_uploaded(file_rec).attach_file(file_name)
        return self.commit(mail)

    def expired(self):
        self.log.event = "Project is expired and deactivated. Notification sent"
        return self.commit(Mail().project_expired(self.project))

    def expire_warning(self):
        self.log.event = "Expiring message sent"
        return self.commit(Mail().project_expiring(self.project))

    def event(self, message):
        self.log.event = message.lower()
        return self.commit()

    def _prefix(self, rec):
        if rec.extend:
            if rec.transform.strip():
                return "transformation"
            else:
                return "extension"
        elif rec.activate:
            return "activation"
        else:
            return "renewal"


class RequestLog(Log):

    def __init__(self, project):
        super().__init__(register=project)
        self.pending = project

    def visa_received(self):
        self.log.event = "Visa received"
        return self.commit(Mail().visa_received(self.pending))

    def visa_resent(self):
        self.log.event = "Visa re-sent to %s" % self.pending.responsible_email
        return self.commit(Mail().visa_resent(self))

    def visa_sent(self):
        self.log.event = "Visa sent to %s" % self.pending.responsible_email
        return self.commit(Mail().visa_sent(self))

    def visa_skip(self):
        self.log.event = "Visa sending step has been skipped"
        return self.commit(Mail().visa_skip(self))

    def create(self, project=None):
        meso = self.pending.project_id()
        if project:
            name = project.get_name()
            self.log.project = project
            self.log.event = "Create project %s from request %s" % (name, meso)
        else:
            self.log.event = "Create project from request %s" % meso
        return self.commit()

    def user_del(self, user):
        self.log.event = "Remove user %s" % user
        return self.commit()

    def user_add(self, user):
        self.log.event = "Add user %s" % user
        return self.commit()

    def user_change(self, info):
        self.log.event = "Change user info: %s" % info
        return self.commit()

    def request_change(self, info):
        self.log.event = "Change request info: %s" % info
        return self.commit()

    def approve(self):
        self.log.event = "Project software requirements approved"
        return self.commit(Mail().pending_approve(self))

    def reset(self):
        self.log.event = "Project creation process has been reset"
        return self.commit(Mail().pending_reset(self))

    def reject(self, message):
        self.log.event = "Project creation request rejected"
        return self.commit(Mail().pending_reject(self, message))

    def ignore(self):
        self.log.event = "Project creation request ignored"
        return self.commit(Mail().pending_ignore(self))


class UserLog(Log):

    def __init__(self, user):
        super().__init__(user=user)
        self.user = user

    def goodbye(self):
        self.log.event = "Sending goodbye notification"
        return self.commit(Mail().user_goodbye(self.user))

    def acl(self, acl):
        result = []
        for name, value in acl.items():
            result.append("%s to %s" % (name, value))
        self.log.event = "Set ACL permissions: %s" % "; ".join(result)
        return self.commit()

    def key_upload(self, key):
        self.log.event = "Upload SSH key %s" % key
        return self.commit()

    def key_uploaded(self, key):
        self.log.event = "Uploaded SSH key %s" % key
        return self.commit(Mail().user_publickey(self, key))

    def password_changed(self):
        self.log.event = "Password has been changed"
        return self.commit()

    def password_reset(self, passwd):
        self.log.event = "Password has been reset"
        return self.commit(Mail().user_password(self, passwd))

    def user_update(self, info):
        changes = []
        for name, value in info.items():
            old = getattr(self.user, name)
            prop = name.capitalize()
            changes.append("%s change: %s -> %s" % (prop, old, value))
        self.log.event = "; ".join(changes)
        return self.commit(Mail().user_update(self))

    def user_updated(self, task):
        full = task.user.full()
        self.log.event = "Modifications for user %s has been applied" % full
        return self.commit(Mail().user_updated(self))

    def info_update(self, info=None, acl=None, projects=None, active=None):
        changes = []
        if info is not None:
            for name, value in info.items():
                old = getattr(self.user, name)
                prop = name.capitalize()
                changes.append("%s change: %s -> %s" % (prop, old, value))
        if acl is not None:
            for name, value in acl.items():
                old = getattr(self.user.acl, name)
                changes.append("ACL %s change %s -> %s" % (name, old, value))
        if active is not None:
            old = self.user.active
            changes.append("Set active status from %s to '%s'" % (old, active))
        if projects is not None:
            old = self.user.project_names()
            for name in projects:
                if name in old:
                    changes.append("Add to project %s" % name)
                else:
                    changes.append("Remove from project %s" % name)
        result = "; ".join(changes)
        self.log.event = "User information changes requested: %s" % result
        return self.commit(Mail().user_update(self))


class Extensions:
    def __init__(self, eid=None):
        if eid:
            self.id = eid
        else:
            self.id = False
        self.queue = Extend().query
        self.cpu = None
        self.extend = None
        self.rec = None
        self.ext = Extend

    def history(self, reverse=True):
        records = self.records()
        return sorted(records, key=attrgetter("created"), reverse=reverse)

    def unprocessed(self):
        return self.queue.filter_by(processed=False).all()

    def pending(self):
        recs = self.queue.filter_by(processed=True).filter_by(accepted=True) \
            .filter_by(done=False).all()
        return list(map(lambda x: x.api(), recs))

    def records(self):
        if self.id:
            return self.record()
        return self.queue.all()

    def record(self):
        if not self.id:
            return self.records()
        return self.queue.filter_by(id=self.id).one()

    @staticmethod
    def _process(record):
        record.processed = True
        record.approve = current_user
        db.session.commit()
        return record

    def ignore(self):
        record = self.record()
        if record.processed:
            raise ValueError("This request has been already processed")
        record.accepted = False
        record.decision = "Extension request has been ignored"
        return self._process(record)

    def reject(self, note):
        record = self.record()
        if record.processed:
            raise ValueError("This request has been already processed")
        record.accepted = False
        record.decision = note
        return self._process(record)

    def transform(self, note):
        self.rec = self.record()
        if self.rec.processed:
            raise ValueError("This request has been already processed")
        self.rec.decision = note
        if not self.rec.transform:
            raise ValueError("This request is not transformation one")
        self.rec.accepted = True
        return self._process(self.rec)

    def accept(self, note):
        self.rec = self.record()
        if self.rec.processed:
            raise ValueError("This request has been already processed")
        self.rec.decision = note

        if (self.extend is True or self.extend is False) and \
                self.rec.extend is not self.extend:
            self.rec.extend = self.extend
            self.rec.decision += "\nExtension option was manually set to %s" \
                                 % self.extend
        if self.cpu and (self.rec.hours != self.cpu):
            self.rec.hours = self.cpu
            self.rec.decision += "\nCPU value was manually set to %s" % self.cpu

        self.rec.accepted = True
        return self._process(self.rec)


class TmpUser(User):
    """
    Class representing a user which has to be added to the system and doesn't
    exist yet
    """

    def __init__(self):
        """
        Init takes no argument
        """
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
        self.password = None

    def __repr__(self):
        return '<TmpUser {}>'.format(self.login)

    def from_task(self, task):
        """
        Takes a task's action string and fill up the properties of TmpUser
        object
        :param task: Object. Instance of Task object
        :return: Object. Instance of TmpUser class
        """
        description = task.get_description()
        if "WITH ACL" not in description:
            description += " WITH ACL user: True"
        if " WITH STATUS " not in description:
            description += " WITH STATUS True"

        user_part, service_part = description.split(" WITH ACL ")
        for i in user_part.split(" and "):
            if "login" in i:
                self.login = i.replace("login: ", "").strip()
            elif "surname" in i:
                self.surname = i.replace("surname: ", "").strip()
            elif "name" in i:
                self.name = i.replace("name: ", "").strip()
            elif "email" in i:
                self.email = i.replace("email: ", "").strip()

        acl_part, active_part = service_part.split(" WITH STATUS ")
        roles = ["user", "responsible", "manager", "tech", "committee", "admin"]
        for acl in acl_part.split(", "):
            for role in roles:
                if role not in acl:
                    continue
                condition = "%s: True" % role
                tmp = True if condition in acl.strip() else False
                self.__setattr__("is_%s" % role, tmp)

        self.active = True if active_part.strip() == "True" else False
        return self


class Pending:
    """
    Representation of RegisterDB record
    Performs operations on pending projects, i.e. registration records which
    haven't been processed yet
    """

    def __init__(self, rid=None):
        """
        self.pending is always a list.
        If rid is provided set self.pending to the unprocessed record with
        provided id. Otherwise it returns all unprocessed records.
        :param rid: String. ID of registration record. Optional
        """
        self.pending = Register.query.filter_by(id=rid).first()
        self.action = None
        self.result = None

    def verify(self):
        """
        Verify if record exists and user or user's role has proper access
        rights.
        :return: Object. Register record
        """
        if not self.pending:
            raise ValueError("Register project record is not set!")
        if "admin" in g.permissions:
            return self.pending
        if self.pending.type not in g.project_config:
            debug("Type %s absent in project configuration" % self.pending.type)
            acl = []
        else:
            acl = g.project_config[self.pending.type].get("acl", [])
        user_allowed = current_user.login in acl
        role_allowed = set(acl).intersection(set(g.permissions))
        if (not user_allowed) and (not role_allowed):
            raise ValueError("Processing of new project record is not allowed")
        if self.pending.status in ["created", "ignored", "rejected"]:
            raise ValueError("Request %s is in final state: %s" %
                             (self.pending.project_id(), self.pending.status))
        return self.pending

    def create(self, users):
        """
        Check if all requirements are satisfied and creates a project in the DB
        and corresponding task for remote execution.
        :return: Object. Pending object
        """
        record = self.verify()
        if record.status not in ["received", "skipped"]:
            raise ValueError("Visa haven't been received yet!")
        if Project.query.filter(Project.title.ilike(record.title)).first():
            raise ValueError("Project '%s' already exist" % record.title)
        total = Project.query.count()
        name = "%s%s" % (record.type, total + 1)
        responsible = list(filter(lambda x: x.resp, users))[0]
        titles = [getattr(record, f"article_{i}") for i in range(1, 6) if
                  getattr(record, f"article_{i}", "") is not ""]
        articles = map(lambda x: ArticleDB(info=x, user=responsible), titles)
        proj = Project(
            title=record.title,
            description=record.description,
            scientific_fields=record.scientific_fields,
            genci_committee=record.genci_committee,
            numerical_methods=record.numerical_methods,
            computing_resources=record.computing_resources,
            project_management=record.project_management,
            project_motivation=record.project_motivation,
            active=False,
            comment="Project created using Copernicus",
            ref=record,
            privileged=False,
            type=record.type,
            created=dt.now(),
            approve=current_user,
            name=name,
            responsible=responsible,
            users=users,
            articles=list(articles),
            resources=Resources(
                approve=current_user,
                valid=True,
                cpu=record.cpu,
                type=record.type,
                project=name,
                ttl=calculate_ttl(record),
                treated=False
            )
        )
        TaskQueue().project(proj).project_create().task.accept()
        for user in users:
            if user.action == "assign" and user.resp:
                TaskQueue().project(proj).responsible_assign(user).task.accept()
            elif user.action == "assign" and not user.resp:
                TaskQueue().project(proj).user_assign(user).task.accept()
            elif user.action == "create" and user.resp:
                TaskQueue().project(proj).responsible_create(user).task.accept()
            elif user.action == "create" and not user.resp:
                TaskQueue().project(proj).user_create(user).task.accept()
        db.session.add(proj)
        self.result = RequestLog(record).create(proj)
        record.status = "created"
        record.processed = True
        record.processed_ts = dt.now()
        return self.commit()

    def visa_create(self, resend=False):
        """
        Creates visa files and attaches them to a mail for responsible person.
        Afterwards delete files from disk and set proper status for register
        record.
        :return: Object. Pending object
        """
        record = self.verify()
        name = record.project_id()
        if not resend and record.status != "approved":
            raise ValueError("Project %s has to be approved first!" % name)
        if resend and record.status not in ["sent", "resent"]:
            raise ValueError("Wrong status for visa resend: %s" % record.status)
        mail = Mail()
        u_list = mail.cfg.get("DEFAULT", "USER_LIST", fallback=None)
        r_list = mail.cfg.get("DEFAULT", "RESPONSIBLE_LIST", fallback=None)
        record.user_list = "(%s)" % u_list if u_list else ""
        record.resp_list = "(%s)" % r_list if r_list else ""
        path = create_visa(record)
        if not path:
            raise ValueError("Failed to generate visa document")
        mail.registration(record).visa_attach(path).start()
        map(lambda x: Path(x).unlink(), path)
        debug("Temporary file(s) %s was deleted" % ",".join(path))
        if resend:
            record.status = "resent"
            self.result = RequestLog(record).visa_resent()
        else:
            record.status = "sent"
            self.result = RequestLog(record).visa_sent()
        return self.commit()

    def visa_skip(self):
        """
        Set correct value to status field in case if visa is not required.
        :return: Object. Pending object
        """
        record = self.verify()
        if record.status != "approved":
            raise ValueError("Cant skip not approved record: %s" % record.status)
        record.status = "skipped"
        self.result = RequestLog(record).visa_skip()
        return self.commit()

    def visa_received(self):
        """
        Set correct value to status field if visa has been received.
        :return: Object. Pending object
        """
        record = self.verify()
        record.status = "visa received"
        self.result = RequestLog(record).visa_received()
        return self.commit()

    def approve(self):
        """
        Set approved value to status field. First step to project creation.
        :return: Object. Pending object
        """
        record = self.verify()
        record.status = "approved"
        record.approve = True
        record.approve_ts = dt.now()
        self.result = RequestLog(record).approve()
        return self.commit()

    def reset(self):
        """
        Set status field of register record to empty string and processed field
        to False thus resetting project creation process
        :return: Object. Pending object
        """
        record = self.verify()
        record.processed = False
        record.status = ""
        self.result = RequestLog(record).reset()
        return self.commit()

    def ignore(self):
        """
        Set self.action to ignore and process the records
        :return: Result of self.process_records() method
        """
        self.action = "ignore"
        return self.process_record()

    def reject(self, message):
        """
        Set self.action to reject and process the records
        :return: Result of self.process_records() method
        """
        self.action = "reject"
        return self.process_record(message)

    def process_record(self, message=None):
        """
        Set processed field of the task record to True, so the task will be
        moved to the task ready to be executed. Based on action property set
        the accepted property and comment value and execute correspondent
        RequestLog method. Commit changes via self.commit()
        :return: Object. Pending object
        """
        record = self.verify()
        record.processed = True
        record.processed_ts = dt.now()
        record.accepted_ts = dt.now()
        record.accepted = False
        record.author = current_user.full_name()
        debug("Action performed on project creation request: %s" % self.action)
        if self.action is "ignore":
            record.status = "ignore"
            self.result = RequestLog(record).ignore()
        elif self.action is "reject":
            record.status = "reject"
            self.result = RequestLog(record).reject(message)
        else:
            raise ValueError("Action %s is not supported" % self.action)
        if message:
            self.pending.comment = message
        return self.commit()

    def commit(self):
        """
        Commit changes to the database
        :return: Object. Pending object
        """
        db.session.commit()
        return self


# noinspection PyArgumentList
class Task:
    """
    Methods of this class is used for processing task status and to perform
    actions associated with a task
    """

    def __init__(self, task):
        """
        Init takes one argument which is task record
        :param task: Object. Task record.
        """
        self.task = task
        self.id = task.id

    def is_processed(self):
        """
        Return processed field value from the task record
        :return: Boolean
        """
        return self.task.processed

    def done(self, result=None):
        """
        Set field done of the task record to True and commit changes
        :return: Object. Result of self.commit method  - task object
        """
        self.task.done = True
        if result:
            self.task.result = result
        return self.commit()

    def accept(self):
        """
        Marking the task for execution in case of positive decision.
        Sending mail with technical details to tech stuff by default
        :return: Object. Task record
        """
        self.task.decision = "accept"
        Mail().task_accepted(self.task).send()
        return self.process()

    def ignore(self):
        """
        Marking the task as ignored in case of negative decision.
        Sending mail with technical details to tech stuff by default
        Task is marked as done and shouldn't be in the task queue for execution
        :return: Object. Task record
        """
        self.task.decision = "ignore"
        self.process()
        return self.done()

    def reject(self):
        """
        Marking the task as rejected in case of negative decision.
        Sending mail with technical details to tech stuff by default
        Task is marked as done and shouldn't be in the task queue for execution
        :return: Object. Task record
        """
        self.task.decision = "reject"
        Mail().task_rejected(self.task).send()
        self.process()
        return self.done()

    def get_action(self):
        """
        Split the action field of task record using "|" as delimiter and return
        the first part of it which represent a task action which should be done
        on task target
        :return: String. Should be one of the following: "create", "assign",
                 "update", "remove" and "change"
        """
        act = self.task.action.split("|")[0]
        if act not in ["activate", "create", "assign", "update", "remove",
                       "change", "ssh"]:
            raise ValueError("The action '%s' is not supported" % act)
        return act

    def get_entity(self):
        """
        Split the action field of task record using "|" as delimiter and return
        the second part of it which represent a task target
        :return: String. Could be user or resp
        """
        return self.task.action.split("|")[1]

    def get_description(self):
        """
        Split the action field of task record and return the last part of it
        which should be a task description, for example:
        "Remove user LOGIN from project PROJECT"
        :return: String
        """
        return self.task.action.split("|")[-1]  # Or index is 4 not -1

    def process(self):
        """
        Set processed field of the task record to True, so the task will be
        moved to the task ready to be executed.
        Set approve field to current user and commit changes via self.commit()
        :return: Object. Task record
        """
        self.task.processed = True
        self.task.approve = current_user
        return self.commit()

    def commit(self):
        """
        Commit changes to the database
        :return: Object. Task record
        """
        db.session.commit()
        return self.task

    def user_new(self):
        """
        Re-create TmpUser object user out of task description, create DB entry
        for User record and ACL record and append ne user to project associated
        with the task.
        :return: String. The log event associated with this action
        """
        project = self.task.project
        self.task.user.passwd = self.task.user.reset_password()
        self.task.user.active = True
        UserMailingList().add(self.task.user.email, self.task.user.full_name())
        if self.task.user.acl.is_responsible:
            ResponsibleMailingList().add(self.task.user.email, self.task.user.full_name())
        return ProjectLog(project).user_new(self.task)

    def user_create(self):
        """
        Execute user_new method but send warning to project's responsible.
        :return: String. The log event associated with this action
        """
        if not self.task.author_id:
            return self.user_new()
        project = self.task.project
        tmp_user = TmpUser().from_task(self)
        user = User.query.filter_by(login=tmp_user.login).first()
        if not user:
            user = User(login=tmp_user.login,
                        name=tmp_user.name,
                        surname=tmp_user.surname,
                        email=tmp_user.email,
                        active=tmp_user.active,
                        project=[project],
                        created=dt.now(),
                        acl=ACLDB(is_user=tmp_user.is_user,
                                  is_responsible=tmp_user.is_responsible,
                                  is_tech=tmp_user.is_tech,
                                  is_manager=tmp_user.is_manager,
                                  is_committee=tmp_user.is_committee,
                                  is_admin=tmp_user.is_admin))
            db.session.add(user)
        if user not in project.users:
            project.users.append(user)
        if not getattr(user, "passwd", None):
            user.passwd = user.reset_password()
        Mail().user_new(user).start()
        UserMailingList().add(user.email, user.full_name())
        if user.acl.is_responsible:
            project.responsible = user
            ResponsibleMailingList().add(user.email, user.full_name())
        return ProjectLog(project).user_created(self.task)

    def user_update(self):
        """

        :return: String. The log event associated with this action
        """
        description = self.get_description()
        user = self.task.user
        old_email = user.email if "email" in description else None

        for i in description.split(" and "):
            if "surname" in i and hasattr(user, "surname"):
                setattr(user, "surname", i.replace("surname: ", "").strip())
            elif "name" in i and hasattr(user, "name"):
                setattr(user, "name", i.replace("name: ", "").strip())
            elif "email" in i and hasattr(user, "email"):
                setattr(user, "email", i.replace("email: ", "").strip())

        if old_email:
            UserMailingList().unsubscribe(old_email)
            UserMailingList().add(user.email, user.full_name())
            if user.acl.is_responsible:
                ResponsibleMailingList().unsubscribe(old_email)
                ResponsibleMailingList().add(user.email, user.full_name())
        return UserLog(user).user_updated(self.task)

    def user_activate(self):
        """
        Appending task associated user to task associated project and set active
        property to True
        :return: String. The log event associated with this action
        """
        project = self.task.project
        user = self.task.user
        if user not in project.users:
            project.users.append(user)
        if not user.active:
            user.active = True
            UserMailingList().add(user.email, user.full_name())
            if user.acl.is_responsible:
                ResponsibleMailingList.add(user.email, user.full_name())
        return ProjectLog(project).user_activated(self.task)

    def user_assign(self):
        """
        Appending task associated user to a task associated project
        :return: String. The log event associated with this action
        """
        project = self.task.project
        user = self.task.user
        if user not in project.users:
            project.users.append(user)
        if not self.task.author_id:
            return ProjectLog(project).user_attached(self.task)
        return ProjectLog(project).user_assigned(self.task)

    def user_delete(self):
        """
        Remove task associated user from task associated project and if there
        is no project associate with the user, the user set as inactive
        :return: String. The log event associated with this action
        """
        project = self.task.project
        user = self.task.user
        if user in project.users:
            project.users.remove(user)
        if not user.project:
            user.active = False
            # UserLog(user).goodbye()
        return ProjectLog(project).user_deleted(self.task)

    def responsible_assign(self):
        """
        Assign new responsible to a task associated project. Set ACL property
        is_responsible to True, save old_responsible, assign the task associated
        user to project responsible and assign it to the mailing list. Check if
        old_responsible has other projects as responsible and if not, remove
        responsible property from his ACL and unsubscribe from responsible
        mailing list.
        :return: String. The log event associated with this action
        """
        project = self.task.project
        user = self.task.user
        if not user.acl.is_responsible:
            user.acl.is_responsible = True
        old_responsible = project.responsible
        project.responsible = user
        ResponsibleMailingList().subscribe(user.email, user.full_name())
        resp = list(map(lambda x: x.get_responsible(), old_responsible.project))
        if not resp:
            old_responsible.acl.is_responsible = False
            ResponsibleMailingList().unsubscribe(old_responsible.email)
        if not self.task.author_id:
            return ProjectLog(project).responsible_attached(self.task)
        return ProjectLog(project).responsible_assigned(self.task)

    def user_publickey(self):
        """
        Send message after public key has been uploaded on the server
        Return: Object. Mail object
        """
        user = self.task.user
        key = self.get_description()
        return UserLog(user).key_uploaded(key)

    def project_create(self):
        """
        Send message when project has been created on the server
        Return: Object. Mail object
        """
        project = self.task.project
        project.active = True
        return ProjectLog(project).created()
