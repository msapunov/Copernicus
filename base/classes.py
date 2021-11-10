from flask import g
from flask_login import current_user
from base import db
from base.functions import project_config, create_visa
from base.email import Mail, UserMailingList, ResponsibleMailingList
from base.database.schema import LogDB, User, ACLDB, Extend, Register

from logging import warning, debug
from operator import attrgetter
from datetime import datetime as dt
from pathlib import Path

__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class Log:

    def __init__(self, project=None, register=None, user=None):
        self.log = LogDB(
            author=current_user,
            project=project,
            register=register,
            user=user)
        self.send = True

    def list(self):
        query = LogDB().query
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
            if mail and self.send: mail.start()
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

    def created(self, date):
        self.log.event = "Project created"
        if date:
            self.log.created = date
        return self.commit()

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

    def user_assign(self, task):
        self.log.event = "Made a request to assign a user %s" % task.user.full()
        return self.user(task.user).commit(Mail().user_assign(task))

    def user_assigned(self, task):
        self.log.event = "User %s has been assigned" % task.user.full()
        return self.user(task.user).commit(Mail().user_assigned(task))

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

    def accept(self, extension):
        ext_or_new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is accepted" \
                         % (ext_or_new, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_accepted(extension, ext_or_new))

    def ignore(self, extension):
        new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is ignored" \
                         % (new, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_ignored(extension, new))

    def reject(self, extension):
        ext_or_new = "Extension" if extension.extend else "Renewal"
        self.log.event = "%s request for %s hours is rejected" \
                         % (ext_or_new, extension.hours)
        self.log.extension = extension
        return self.commit(Mail().allocation_rejected(extension, ext_or_new))

    def activity_report(self, file_rec):
        file_name = file_rec.path
        self.log.event = "Activity report saved on the server in the file %s" \
                         % file_name
        mail = Mail().report_uploaded(file_rec).attach_file(file_name)
        return self.commit(mail)

    def event(self, message):
        self.log.event = message.lower()
        return self.commit()


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

    def create(self):
        self.log.event = "Project created out of this request"
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

    def acl(self, acl):
        result = []
        for name, value in acl.items():
            result.append("%s to %s" % (name, value))
        self.log.event = "Set ACL permissions: %s" % "; ".join(result)
        return self.commit()

    def user_update(self, info):
        changes = []
        for name, value in info.items():
            old = getattr(self.user, name)
            prop = name.capitalize()
            changes.append("%s change: %s -> %s" % (prop, old, value))
        self.log.event = "; ".join(changes)
        return self.commit(Mail().user_update(self))

    def user_updated(self, info):
        changes = []
        for name, value in info.items():
            old = getattr(self.user, name)
            prop = name.capitalize()
            changes.append("%s change: %s -> %s" % (prop, old, value))
        self.log.event = "; ".join(changes)
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


class TmpUser:
    """
    Class representing a user which has to be added to the system and doesn't
    exists yet
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

    def full(self):
        return "%s %s" % (self.name, self.surname)

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
                self.login = i.replace("login: ", "")
            elif "surname" in i:
                self.surname = i.replace("surname: ", "")
            elif "name" in i:
                self.name = i.replace("name: ", "")
            elif "email" in i:
                self.email = i.replace("email: ", "")

        acl_part, active_part = service_part.split(" WITH STATUS ")
        roles = ["user", "responsible", "manager", "tech", "committee", "admin"]
        for acl in acl_part.split(", "):
            for role in roles:
                if role not in acl:
                    continue
                condition = "%s: True" % role
                tmp = True if condition in acl.strip() else False
                self.__setattr__("is_%s" % role, tmp)

        if "PASSWORD" in active_part:
            active_part, password = active_part.split("AND PASSWORD")
            self.password = password.strip()
        self.active = True if active_part.strip() == "True" else False
        return self

    def ready_task(self):
        """
        Creates task's description out of instance of TmpUser
        :return: String. Task's description
        """
        u_part = "login: %s and name: %s and surname: %s and email: %s" % (
            self.login, self.name, self.surname, self.email)
        a_part = "user: %s, responsible: %s, manager: %s, tech: %s, " \
                 "committee: %s, admin: %s" % (self.is_user,
                                               self.is_responsible,
                                               self.is_manager, self.is_tech,
                                               self.is_committee, self.is_admin)
        if self.password:
            return "%s WITH ACL %s WITH STATUS %s AND PASSWORD %s" % \
                   (u_part, a_part, self.active, self.password)
        return "%s WITH ACL %s WITH STATUS %s" % (u_part, a_part, self.active)


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
        query = Register.query.filter_by(processed=False)
        self.pending = query.filter_by(id=rid).first()
        self.action = None
        self.result = None

    def verify(self):
        """
        Verify if record is exists and user or user's role has proper access
        rights.
        :return: Object. Register record
        """
        if not self.pending:
            raise ValueError("Register project record is not set!")
        if "admin" in g.permissions:
            return self.pending
        config = project_config()
        acl = config[self.pending.type].get("acl", [])
        user_allowed = current_user.login in acl
        role_allowed = set(acl).intersection(set(g.permissions))
        if (not user_allowed) and (not role_allowed):
            raise ValueError("Processing of new project record is not allowed")
        return self.pending

    def create(self):
        """
        Check if all requirements are satisfied and creates a project in the DB
        and corresponding task for remote execution.
        :return: Object. Pending object
        """
        record = self.verify()
        name = record.project_id()
        status = record.status.upper()
        if "VISA RECEIVED" not in status and "VISA SKIPPED" not in status:
            raise ValueError("Visa for '%s' haven't been received yet!" % name)
        record.status = "project created"
        self.result = RequestLog(record).create()
        record.processed = True
        return self.commit()

    def visa_skip(self):
        """
        Set correct value to status field in case if visa is not required.
        :return: Object. Pending object
        """
        record = self.verify()
        name = record.project_id()
        status = record.status.upper()
        if ("APPROVED" not in status) and ("VISA SENT" not in status):
            raise ValueError("Project %s has to be approved first!" % name)
        record.status = "visa skipped"
        self.result = RequestLog(record).visa_skip()
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
        status = record.status.upper()
        if ("APPROVED" not in status) and ("VISA SENT" not in status):
            raise ValueError("Project %s has to be approved first!" % name)
        if ("VISA SENT" in status) and not resend:
            raise ValueError("Visa for project %s has been already sent" % name)
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
        record.status = "visa sent"
        if resend:
            self.result = RequestLog(record).visa_resent()
        else:
            self.result = RequestLog(record).visa_sent()
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

    def done(self):
        """
        Set field done of the task record to True and commit changes
        :return: Object. Result of self.commit method  - task object
        """
        self.task.done = True
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
        if act not in ["create", "assign", "update", "remove", "change"]:
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

    def user_create(self):
        """
        Re-create TmpUser object user out of task description, create DB entry
        for User record and ACL record and append ne user to project associated
        with the task.
        :return: String. The log event associated with this action
        """
        project = self.task.project
        tmp_user = TmpUser().from_task(self)
        acl = ACLDB(is_user=tmp_user.is_user,
                    is_responsible=tmp_user.is_responsible,
                    is_tech=tmp_user.is_tech,
                    is_manager=tmp_user.is_manager,
                    is_committee=tmp_user.is_committee,
                    is_admin=tmp_user.is_admin)
        user = User(login=tmp_user.login,
                    name=tmp_user.name,
                    surname=tmp_user.surname,
                    email=tmp_user.email,
                    active=tmp_user.active,
                    acl=acl,
                    project=[project],
                    created=dt.now())
        db.session.add(acl)
        db.session.add(user)
        project.users.append(user)
        Mail().user_new(tmp_user)
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
            UserMailingList().change(old_email, user.email, user.full_name())
            if user.acl.is_responsible:
                ResponsibleMailingList().change(old_email,
                                                user.email,
                                                user.full_name())
        return UserLog(user).user_updated()

    def user_assign(self):
        """
        Appending task associated user to a task associated project
        :return: String. The log event associated with this action
        """
        project = self.task.project
        user = self.task.user
        project.users.append(user)
        return ProjectLog(project).user_assigned(self.task)

    def user_delete(self):
        """
        Remove task associated user from task associated project and if there
        is no project associate with the user, the user set as inactive
        :return: String. The log event associated with this action
        """
        project = self.task.project
        user = self.task.user
        project.users.remove(user)
        if not user.project:
            user.active = False
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
        ResponsibleMailingList.subscribe(user.email, user.full_name())
        resp = list(map(lambda x: x.get_responsible(), old_responsible.project))
        if not resp:
            old_responsible.acl.is_responsible = False
            ResponsibleMailingList.unsubscribe(old_responsible.email)
        return ProjectLog(project).responsible_assigned(self.task)
