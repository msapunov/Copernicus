from flask_login import UserMixin
from base import db
from datetime import datetime as dt


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class ACLDB(db.Model):
    __tablename__ = "acl"

    id = db.Column(db.Integer, primary_key=True)
    is_user = db.Column(db.Boolean, default=True)
    is_responsible = db.Column(db.Boolean, default=False)
    is_manager = db.Column(db.Boolean, default=False)
    is_tech = db.Column(db.Boolean, default=False)
    is_committee = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    modified = db.Column(db.DateTime(True))
    created = db.Column(db.DateTime(True))

    def to_dict(self):
        start = self.created.strftime("%Y-%m-%d %X %Z") if self.created else ""
        mod = self.modified.strftime("%Y-%m-%d %X %Z") if self.modified else ""
        return {
            "id": self.id,
            "user": self.is_user,
            "responsible": self.is_responsible,
            "manager": self.is_manager,
            "tech": self.is_tech,
            "committee": self.is_committee,
            "admin": self.is_admin,
            "created": start,
            "modified": mod,
        }


class MethodDB(db.Model):
    __tablename__ = "methods"

    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(512), unique=True)
    acl_id = db.Column(db.Integer, db.ForeignKey("acl.id"))
    acl = db.relationship("ACLDB", uselist=False, backref="methods")
    comment = db.Column(db.Text)
    modified = db.Column(db.DateTime(True))
    created = db.Column(db.DateTime(True))
    author = db.Column(db.String(64))


class UserProjectLink(db.Model):
    __tablename__ = "user_project"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"),
                           primary_key=True)


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256))
    description = db.Column(db.String)
    scientific_fields = db.Column(db.String(256))
    genci_committee = db.Column(db.String(256))
    numerical_methods = db.Column(db.String)
    computing_resources = db.Column(db.String)
    project_management = db.Column(db.String)
    project_motivation = db.Column(db.String)
    active = db.Column(db.Boolean, default=False)
    modified = db.Column(db.DateTime(True))
    created = db.Column(db.DateTime(True))
    comment = db.Column(db.Text)
    gid = db.Column(db.Integer)
    privileged = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(128))
    type = db.Column(db.String(1))

    responsible_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    responsible = db.relationship("User", backref="responsible",
                                  uselist=False, foreign_keys=responsible_id)

    files = db.relationship("File", back_populates="project")
    articles = db.relationship("ArticleDB", back_populates="project")
    users = db.relationship("User", secondary="user_project")

    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approve = db.relationship("User", foreign_keys=approve_id)

    resources_id = db.Column(db.Integer, db.ForeignKey("project_resources.id"))
    resources = db.relationship("Resources", foreign_keys=resources_id)

    ref_id = db.Column(db.Integer, db.ForeignKey("register.id"))
    ref = db.relationship("Register", foreign_keys=ref_id)

    def __repr__(self):
        return '<Project {}>'.format(self.get_name())

    def get_responsible(self):
        return self.responsible

    def get_name(self):
        if self.name:
            return self.name
        pid = self.id
        genre = self.type
        return "%s%s" % (genre, str(pid).zfill(3))

    def api_resources(self):
        return {
            "cpu": self.resources.cpu,
            "finish": self.resources.ttl.strftime("%Y-%m-%d %X"),
            "start": self.resources.created.strftime("%Y-%m-%d %X"),
            "notify": self.responsible.email,
            "name": self.responsible.full_name(),
            "id": self.id,
            "project": self.get_name()
        }

    def pretty_dict(self):
        rec = self.to_dict()
        rec["approve"] = rec["approve"]["fullname"]
        rec["responsible"] = rec["responsible"]["fullname"]
        rec["resources"] = rec["resources"]["cpu"]
        tmp = []
        for user in rec["users"]:
            tmp.append("%s <%s>" % (user["fullname"], user["email"]))
        rec["users"] = tmp
        return rec

    def to_dict(self):
        if self.created:
            created = self.created.strftime("%Y-%m-%d %X %Z")
        else:
            created = ""
        if self.modified:
            modified = self.modified.strftime("%Y-%m-%d %X %Z")
        else:
            modified = ""

        if self.resources.created:
            start = self.resources.created.strftime("%Y-%m-%d %X %Z")
        else:
            start = ""
        if self.resources.ttl:
            end = self.resources.ttl.strftime("%Y-%m-%d %X %Z")
        else:
            end = ""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "scientific_fields": self.scientific_fields,
            "genci_committee": self.genci_committee,
            "numerical_methods": self.numerical_methods,
            "computing_resources": self.computing_resources,
            "project_management": self.project_management,
            "project_motivation": self.project_motivation,
            "active": self.active,
            "modified": modified,
            "created": created,
            "comment": self.comment,
            "gid": self.gid,
            "privileged": self.privileged,
            "name": self.get_name(),
            "type": self.type,
            "responsible": self.responsible.to_dict(),
            "responsible_login": self.responsible.login,
            "files": list(map(lambda x: x.path, self.files)),
            "articles": list(map(lambda x: x.info, self.articles)),
            "users": list(map(lambda x: x.to_dict(), self.users)),
            "approve": self.approve.to_dict(),
            "resources": self.resources.to_dict(),
            "allocation_start": start,
            "allocation_end": end,
            "ref": self.ref.id
        }


class Extend(db.Model):
    __tablename__ = "project_extension"

    id = db.Column(db.Integer, primary_key=True)
    extend = db.Column(db.Boolean)
    exception = db.Column(db.Boolean)
    reason = db.Column(db.Text)
    hours = db.Column(db.Integer, db.CheckConstraint("cpu>=0"))
    created = db.Column(db.DateTime(True))
    modified = db.Column(db.DateTime(True))
    accepted = db.Column(db.Boolean)
    processed = db.Column(db.Boolean, default=False)
    decision = db.Column(db.Text)
    done = db.Column(db.Boolean, default=False)
    present_use = db.Column(db.Integer)
    present_total = db.Column(db.Integer)
    usage_percent = db.Column(db.String(10))
    activate = db.Column(db.Boolean, default=False)
    transform = db.Column(db.String(1), default="")

    doc_id = db.Column(db.Integer, db.ForeignKey("project_files.id"))
    doc = db.relationship("File", foreign_keys=[doc_id])

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    project = db.relationship("Project", foreign_keys=project_id)

    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approve = db.relationship("User", foreign_keys=approve_id)

    def __repr__(self):
        return "<Extension for project {}>".format(self.project.get_name())

    def api(self):
        return {
            "cpu": self.hours,
            "finish": self.project.resources.ttl.strftime("%Y-%m-%d %X"),
            "start": self.project.resources.created.strftime("%Y-%m-%d %X"),
            "notify": self.project.responsible.email,
            "name": self.project.responsible.full_name(),
            "id": self.id,
            "add_hours": self.extend,
            "project": self.project.get_name(),
            "transform": self.transform
        }

    def to_dict(self):
        start = self.created.strftime("%Y-%m-%d %X %Z") if self.created else ""
        mod = self.modified.strftime("%Y-%m-%d %X %Z") if self.modified else ""
        approve = self.approve.full_name() if self.approve else ""
        if hasattr(self.project, "consumed"):
            conso = self.project.consumed
        else:
            conso = ""
        if hasattr(self.project, "consumed_use"):
            use = self.project.consumed_use
        else:
            use = ""
        return {
            "id": self.id,
            "extension": self.extend,
            "exception": self.exception,
            "reason": self.reason,
            "hours": self.hours,
            "created": start,
            "modified": mod,
            "accepted": self.accepted,
            "processed": self.processed,
            "decision": self.decision,
            "done": self.done,
            "activate": self.activate,
            "transform": self.transform,
            "project": self.project.id,
            "total": self.present_total,
            "initial_use": self.present_use,
            "initial_usage": self.usage_percent,
            "present_use": conso,
            "present_usage": use,
            "project_name": self.project.get_name(),
            "approve": approve,
            "responsible": self.project.responsible.full_name(),
            "responsible_login": self.project.responsible.login
        }


class ArticleDB(db.Model):
    __tablename__ = "project_articles"

    id = db.Column(db.Integer, primary_key=True)
    info = db.Column(db.Text)
    created = db.Column(db.DateTime(True), default=dt.utcnow)

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    project = db.relationship("Project", back_populates="articles")
    user = db.relationship("User", foreign_keys=user_id)


class File(db.Model):
    __tablename__ = "project_files"

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.Text)
    size = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created = db.Column(db.DateTime(True), default=dt.utcnow)

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    project = db.relationship("Project", back_populates="files")
    user = db.relationship("User", foreign_keys=user_id)


class Resources(db.Model):
    __tablename__ = "project_resources"

    id = db.Column(db.Integer, primary_key=True)
    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approve = db.relationship("User", foreign_keys=approve_id)

    file_id = db.Column(db.Integer, db.ForeignKey("project_files.id"))
    file = db.relationship("File", foreign_keys=file_id)

    valid = db.Column(db.Boolean, default=False)
    cpu = db.Column(db.Integer, db.CheckConstraint("cpu>=0"))
    type = db.Column(db.String(1))
    comment = db.Column(db.Text)
    modified = db.Column(db.DateTime(True))
    created = db.Column(db.DateTime(True))
    ttl = db.Column(db.DateTime(True))
    project = db.Column(db.String)
    treated = db.Column(db.Boolean, default=False)
    consumption_ts = db.Column(db.DateTime(True))
    consumption = db.Column(db.Integer, db.CheckConstraint("consumption>=0"))

    def to_dict(self):
        start = self.created.strftime("%Y-%m-%d %X %Z") if self.created else ""
        mod = self.modified.strftime("%Y-%m-%d %X %Z") if self.modified else ""
        ttl = self.ttl.strftime("%Y-%m-%d %X %Z") if self.ttl else ""
        return {
            "id": self.id,
            "approve": self.approve.to_dict(),
            "report": self.file.path if self.file else False,
            "valid": self.valid,
            "cpu": self.cpu,
            "type": self.type,
            "comment": self.comment,
            "created": start,
            "modified": mod,
            "finish": ttl
        }


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    surname = db.Column(db.String(128))
    email = db.Column(db.String(128))
    phone = db.Column(db.String(10))
    lab = db.Column(db.String(128))
    position = db.Column(db.String(128))
    login = db.Column(db.String(128), unique=True)
    acl_id = db.Column(db.Integer, db.ForeignKey("acl.id"))
    acl = db.relationship("ACLDB", uselist=False, backref="users")
    project = db.relationship("Project", secondary="user_project")
    active = db.Column(db.Boolean, default=False)
    comment = db.Column(db.Text)
    modified = db.Column(db.DateTime(True))
    created = db.Column(db.DateTime(True))
    uid = db.Column(db.Integer)

    def __repr__(self):
        return '<User {}>'.format(self.login)

    def full_name(self):
        if self.name and self.surname:
            return "%s %s" % (self.name.capitalize(), self.surname.capitalize())
        return "%s %s" % (self.name, self.surname)

    def permissions(self):
        perm = []
        if self.acl.is_user:
            perm.append("user")
        if self.acl.is_responsible:
            perm.append("responsible")
        if self.acl.is_manager:
            perm.append("manager")
        if self.acl.is_tech:
            perm.append("tech")
        if self.acl.is_committee:
            perm.append("committee")
        if self.acl.is_admin:
            perm.append("admin")
        return perm

    def project_names(self):
        projects = list(self.project)
        names = map(lambda x: x.get_name(), projects)
        return list(names)

    def project_ids(self):
        projects = list(self.project)
        ids = map(lambda x: x.id, projects)
        return list(ids)

    def details(self):
        start = self.acl.created.strftime("%Y-%m-%d %X %Z") if self.acl.created else ""
        mod = self.acl.modified.strftime("%Y-%m-%d %X %Z") if self.acl.modified else ""
        return {
            "id": self.id,
            "login": self.login,
            "name": self.name,
            "fullname": self.full_name(),
            "surname": self.surname,
            "email": self.email,
            "phone": self.phone,
            "lab": self.lab,
            "position": self.position,
            "active": self.active,
            "comment": self.comment,
            #            "last_seen": self.last_seen.isoformat() + 'Z',
            "modified": self.modified,
            "created": self.created,
            "acl_id": self.acl.id,
            "user": self.acl.is_user,
            "responsible": self.acl.is_responsible,
            "manager": self.acl.is_manager,
            "tech": self.acl.is_tech,
            "committee": self.acl.is_committee,
            "admin": self.acl.is_admin,
            "acl_created": start,
            "acl_modified": mod,
            "uid": self.uid,
            "projects": self.project_names()
        }

    def to_dict(self):
        return {
            "id": self.id,
            "login": self.login,
            "name": self.name,
            "fullname": self.full_name(),
            "surname": self.surname,
            "email": self.email,
            "phone": self.phone,
            "lab": self.lab,
            "position": self.position,
            "active": self.active,
            "comment": self.comment,
            #            "last_seen": self.last_seen.isoformat() + 'Z',
            "modified": self.modified,
            "uid": self.uid,
            "created": self.created
        }


class Register(db.Model):
    __tablename__ = "register"

    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime(True))
    title = db.Column(db.String(256))
    responsible_first_name = db.Column(db.String(128))
    responsible_last_name = db.Column(db.String(128))
    responsible_position = db.Column(db.String(128))
    responsible_lab = db.Column(db.String(128))
    responsible_email = db.Column(db.String(128))
    responsible_phone = db.Column(db.String(10))
    description = db.Column(db.String)
    scientific_fields = db.Column(db.String(256))
    genci_committee = db.Column(db.String(128))
    numerical_methods = db.Column(db.String)
    computing_resources = db.Column(db.String)
    type = db.Column(db.String(1))
    cpu = db.Column(db.Integer, db.CheckConstraint("cpu_cluster>=0"))
    article_1 = db.Column(db.String)
    article_2 = db.Column(db.String)
    article_3 = db.Column(db.String)
    article_4 = db.Column(db.String)
    article_5 = db.Column(db.String)
    users = db.Column(db.String)
    project_management = db.Column(db.String)
    project_motivation = db.Column(db.String)
    processed = db.Column(db.Boolean)
    processed_ts = db.Column(db.DateTime(True))
    accepted = db.Column(db.Boolean)
    accepted_ts = db.Column(db.DateTime(True))
    accepted_skip = db.Column(db.Boolean)
    comment = db.Column(db.String)
    created = db.Column(db.Boolean)
    created_ts = db.Column(db.DateTime(True))
    approve = db.Column(db.Boolean)
    approve_ts = db.Column(db.DateTime(True))
    approve_skip = db.Column(db.Boolean)

    def __repr__(self):
        return "<Registration request {}>".format(self.id)

    def _parse_user_rec(self, record):
        tmp = {}
        info = record.split(";")
        for i in info:
            j = i.split(":")
            if "First Name" in j[0]:
                tmp["name"] = j[1].strip()
            elif "Last Name" in j[0]:
                tmp["last"] = j[1].strip()
            elif "E-mail" in j[0]:
                tmp["mail"] = j[1].strip()
            else:
                tmp["login"] = j[1].strip()
        return tmp

    def project_type(self):
        return self.type.upper()

    def project_id(self):
        year = dt.now().year
        return "meso-%s-%s-%s" % (year, self.id, self.project_type())

    def get_users(self):
        users = self.users.split("\n")
        result = []
        for user in users:
            try:
                tmp = self._parse_user_rec(user)
            except:
                continue
            result.append(tmp)
        return result

    def to_dict(self):
        return {
            "id": self.id,
            "ts": self.ts.strftime("%Y-%m-%d %X %Z"),
            "title": self.title,
            "responsible_first_name": self.responsible_first_name,
            "responsible_last_name": self.responsible_last_name,
            "responsible_position": self.responsible_position,
            "responsible_lab": self.responsible_lab,
            "responsible_email": self.responsible_email,
            "responsible_phone": self.responsible_phone,
            "description": self.description,
            "scientific_fields": self.scientific_fields,
            "genci_committee": self.genci_committee,
            "numerical_methods": self.numerical_methods,
            "computing_resources": self.computing_resources,
            "cpu": self.cpu,
            "article_1": self.article_1,
            "article_2": self.article_2,
            "article_3": self.article_3,
            "article_4": self.article_4,
            "article_5": self.article_5,
            "users": self.get_users(),
            "project_management": self.project_management,
            "project_motivation": self.project_motivation,
            "processed": self.processed,
            "processed_ts": self.processed_ts,
            "accepted": self.accepted,
            "accepted_ts": self.accepted_ts,
            "comment": self.comment,
            "created": self.created,
            "created_ts": self.created_ts,
            "approve": self.approve,
            "approve_ts": self.approve_ts,
            "type": self.project_type(),
            "meso_id": self.project_id()
        }


class LogDB(db.Model):
    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True)

    created = db.Column(db.DateTime(True), default=dt.utcnow)
    event = db.Column(db.Text, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", foreign_keys=author_id)

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    project = db.relationship("Project", foreign_keys=project_id)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", foreign_keys=user_id)

    articles_id = db.Column(db.Integer, db.ForeignKey("project_articles.id"))
    articles = db.relationship("ArticleDB", foreign_keys=articles_id)

    extension_id = db.Column(db.Integer, db.ForeignKey("project_extension.id"))
    extension = db.relationship("Extend", foreign_keys=extension_id)

    files_id = db.Column(db.Integer, db.ForeignKey("project_files.id"))
    files = db.relationship("File", foreign_keys=files_id)

    resources_id = db.Column(db.Integer, db.ForeignKey("project_resources.id"))
    resources = db.relationship("Resources", foreign_keys=resources_id)

    def __repr__(self):
        return "<Log event for project {}>".format(self.project.get_name())

    def to_web(self):
        event = self.event[0].upper() + self.event[1:]
        creator = self.author.full_name() if self.author else "Author is unknown"
        msg = "%s by %s" % (event, creator)
        return {
            "project": self.project.name if self.project else "",
            "date": self.created.strftime("%Y-%m-%d %X %Z"),
            "message": msg
        }

    def to_dict(self):
        event = self.event[0].upper() + self.event[1:]
        creator = self.author.full_name() if self.author else "Author is unknown"
        msg = "%s by %s" % (event, creator)
        return {
            "date": self.created.strftime("%Y-%m-%d %X %Z"),
            "message": msg
        }


class Tasks(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.Text, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", foreign_keys=author_id)

    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"),
                           nullable=False)
    approve = db.relationship("User", foreign_keys=approve_id)

    decision = db.Column(db.String(6),
                         db.CheckConstraint("decision IN ('accept', 'reject',"
                                            " 'ignore')"))
    processed = db.Column(db.Boolean)
    done = db.Column(db.Boolean)

    created = db.Column(db.DateTime(True), default=dt.utcnow)
    modified = db.Column(db.DateTime(True))

    uid = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", foreign_keys=uid)

    limbo_uid = db.Column(db.Integer, db.ForeignKey("limbo_users.id"))
    limbo_user = db.relationship("LimboUser", foreign_keys=limbo_uid)

    pid = db.Column(db.Integer, db.ForeignKey("projects.id"))
    project = db.relationship("Project", foreign_keys=pid)

    def __repr__(self):
        return "<Task queue record {}>".format(self.id)

    def brief(self):
        act, entity, login, project, task = self.action.split("|")
        if act in ["create", "add", "assign", "delete", "remove"]:
            act += " a user "
        elif act in ["update"]:
            act += " user's info "
        act = act[0].upper() + act[1:].lower()
        act += "by %s" % self.author.full_name()
        return act

    def description(self):
        act, entity, login, project, task = self.action.split("|")
        if act in ["create"]:
            act += " a user with %s for the project %s" % (task, entity)
        if act in ["assign", "remove"]:
            return task
        elif act in ["update"]:
            act += " %s user's info with following data: %s" % (entity, task)
        act = act[0].upper() + act[1:]
        return act

    def notify(self):
        if "update" in self.action and self.project:
            return self.author.email
        elif ("change" in self.action) and ("password" in self.action):
            return self.user.email
        elif (self.author and self.project):
            return self.project.responsible.email
        else:
            return ""

    def api(self):
        act, entity, login, project, task = self.action.split("|")
        return {
            "id": self.id,
            "notify": self.notify(),
            "pid": self.pid if self.pid else "",
            "uid": self.uid if self.uid else "",
            "action": act,
            "user": login,
            "project": project,
            "entity": entity,
            "task": task
        }

    def to_dict(self):
        if self.done:
            status = "done"
        elif self.processed:
            status = "processed"
        else:
            status = ""
        mod = self.modified.strftime("%Y-%m-%d %X %Z") if self.modified else ""
        return {
            "id": self.id,
            "description": self.description(),
            "action": self.brief(),
            "done": self.done,
            "author": self.author.full_name() if self.author else "",
            "approve": self.approve.full_name() if self.approve else "",
            "decision": self.decision,
            "processed": self.processed,
            "created": self.created.strftime("%Y-%m-%d %X %Z"),
            "status": status,
            "modified": mod
        }


class LimboUser(db.Model):
    __tablename__ = "limbo_users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    surname = db.Column(db.String(128))
    email = db.Column(db.String(128))
    phone = db.Column(db.String(10))
    lab = db.Column(db.String(128))
    position = db.Column(db.String(128))
    login = db.Column(db.String(128), unique=True)
    active = db.Column(db.Boolean, default=False)
    comment = db.Column(db.Text)
    modified = db.Column(db.DateTime(True))
    created = db.Column(db.DateTime(True))
    ref_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reference = db.relationship("User", foreign_keys=ref_id)
    acl_id = db.Column(db.Integer, db.ForeignKey("acl.id"))

    def __repr__(self):
        return '<Limbo User {}>'.format(self.login)

    def full_name(self):
        if self.name and self.surname:
            return "%s %s" % (self.name.capitalize(), self.surname.capitalize())
        return "Not available"

    def task_ready(self):
        return "login: %s and name: %s and surname: %s and email: %s" % (
            self.login, self.name, self.surname, self.email)

    def to_dict(self):
        return {
            "id": self.id,
            "login": self.login if self.login else "",
            "name": self.name if self.name else "",
            "fullname": self.full_name(),
            "surname": self.surname if self.surname else "",
            "email": self.email if self.email else "",
            "phone": self.phone if self.phone else "",
            "lab": self.lab if self.lab else "",
            "position": self.position if self.position else "",
            "active": self.active if self.active else "",
            "comment": self.comment if self.comment else "",
        }
