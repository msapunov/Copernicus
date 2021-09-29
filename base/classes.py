from flask import g
from flask_login import current_user
from base import db
from base.functions import project_config
from base.email import Mail, UserMailingList, ResponsibleMailingList
from base.database.schema import LogDB, User, ACLDB, Extend, Register

from logging import warning, debug
from operator import attrgetter
from datetime import datetime as dt

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

    def visa_sent(self):
        self.log.event = "Visa sent to %s" % self.pending.responsible_email
        return self.commit()

    def visa_skip(self):
        self.log.event = "Visa sending step has been skipped"
        return self.commit()

    def approve(self):
        self.log.event = "Project software requirements approved"
        return self.commit()

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

    def accept(self):
        self.log.event = "Project creation request accepted"
        return self.commit()

    def reject(self):
        self.log.event = "Project creation request rejected"
        return self.commit()

    def ignore(self):
        self.log.event = "Project creation request ignored"
        return self.commit()


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
        return "%s WITH ACL %s WITH STATUS %s" % (u_part, a_part, self.active)


class Pending:
    """
    Operations on pending projects, i.e. registration records which haven't been
    processed yet
    """
    def __init__(self, rid=None):
        """
        self.pending is always a list.
        If rid is provided set self.pending to the unprocessed record with
        provided id. Otherwise it returns all unprocessed records.
        :param rid: String. ID of registration record. Optional
        """
        query = Register.query.filter_by(processed=False)
        if rid:
            self.pending = [query.filter_by(id=id).first()]
        else:
            self.pending = query.all()
        self.action = None

    @staticmethod
    def acl_filter(reg):
        """
        Reads project configuration file and check if the type of project in
        register record should be shown to current_user based on roles in
        g.permissions and acl option value from config
        If user has admin role always return True
        :param reg: Object. Registration value
        :return: Boolean
        """
        if "admin" in g.permissions:
            return True
        config = project_config()
        project_type = reg.type.lower()
        if project_type not in config.keys():
            warning("Type %s is not found in config" % project_type)
            return False
        acl = config[project_type].get("acl", [])
        debug("ACL %s for register project type %s" % (acl, project_type))
        if current_user.login in acl:
            debug("Login %s is in register ACL: %s" % (current_user.login, acl))
            return True
        role = set(acl).intersection(set(g.permissions))
        debug("Intersection of register ACL and user permissions: %s" % role)
        if role:
            return True
        return False

    def unprocessed(self):
        """
        Filter unprocessed records based on value of acl option from project
        configuration file
        :return: List. List of unprocessed register project records
        """
        return list(filter(lambda x: self.acl_filter(x), self.pending))

    def ignore(self):
        """
        Set self.action to ignore and process the records
        :return: List. Result of self.process_records() method
        """
        self.action = "ignore"
        return self.process_records()

    def reject(self):
        """
        Set self.action to reject and process the records
        :return: List. Result of self.process_records() method
        """
        self.action = "reject"
        return self.process_records()

    def accept(self):
        """
        Set self.action to accept and process the records
        :return: List. Result of self.process_records() method
        """
        self.action = "accept"
        return self.process_records()

    def process_records(self):
        """
        Execute process_record method on each unprocessed record in self.pending
        and commit the changes.
        :return: List. List of processed register records
        """
        result = map(lambda x: self.process_record(x), self.pending)
        self.commit()
        return list(result)

    def process_record(self, record):
        """
        Set processed field of the task record to True, so the task will be
        moved to the task ready to be executed. Based on action property set
        the accepted property and comment value and execute correspondent
        RequestLog method
        Set approve field to current user and commit changes via self.commit()
        :return: Object. Register record
        """
        if not self.acl_filter(record):
            raise ValueError("")
        record.processed = True
        record.approve = current_user
        record.processed_ts = dt.now()
        record.accepted_ts = dt.now()

        full = current_user.full_name()
        debug("Action performed on project creation request: %s" % self.action)
        if self.action is "ignore":
            record.accepted = False
            record.comment = "Project creation request ignored by %s" % full
            RequestLog(record).ignore()
        elif self.action is "reject":
            record.accepted = False
            record.comment = "Project creation request rejected by %s" % full
            RequestLog(record).reject()
        elif self.action is "accept":
            record.accepted = True
            record.comment = "Project creation request accepted by %s" % full
            RequestLog(record).accept()
        else:
            raise ValueError("Action %s is not supported" % self.action)
        return self

    def commit(self):
        """
        Commit changes to the database
        :return: Object. Task record
        """
        db.session.commit()
        return self.pending


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
        tmp_user = TmpUser().from_task(self.task)
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
        return ProjectLog(project).user_assigned(self.task)

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
        return ProjectLog(project).user_deleted(user)

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
