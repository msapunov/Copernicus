from flask_login import UserMixin
from code import db
from datetime import datetime as dt


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
    allocation_end = db.Column(db.DateTime(True))
    comment = db.Column(db.Text)
    gid = db.Column(db.Integer)
    privileged = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(128))
    type = db.Column(db.String(1),
                     db.CheckConstraint("type IN ('a', 'b', 'c', 'h')"))

    responsible_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    responsible = db.relationship("User", backref="responsible",
                                  uselist=False, foreign_keys=responsible_id)

    files = db.relationship("FileDB", back_populates="project")
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

    def to_dict(self):
        if self.created:
            created = self.created.strftime("%Y-%m-%d %X %Z")
        else:
            created = ""
        if self.modified:
            modified = self.modified.strftime("%Y-%m-%d %X %Z")
        else:
            modified = ""
        if self.allocation_end:
            allocation = self.allocation_end.strftime("%Y-%m-%d %X %Z")
        else:
            allocation = ""
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
            "files": self.files,
            "articles": self.articles,
            "users": list(map(lambda x: x.to_dict(), self.users)),
            "approve": self.approve.to_dict(),
            "resources": self.resources.to_dict(),
            "allocation_end": allocation,
            "ref": self.ref.id
        }


class Extend(db.Model):
    __tablename__ = "project_extension"

    id = db.Column(db.Integer, primary_key=True)
    reason = db.Column(db.Text)
    hours = db.Column(db.Integer, db.CheckConstraint("cpu>=0"))
    created = db.Column(db.DateTime(True))
    modified = db.Column(db.DateTime(True))
    accepted = db.Column(db.Boolean)
    processed = db.Column(db.Boolean, default=False)
    decision = db.Column(db.Text)
    allocation = db.Column(db.Boolean, default=False)
    present_use = db.Column(db.Integer)
    present_total = db.Column(db.Integer)
    usage_percent = db.Column(db.String(4))
    activate = db.Column(db.Boolean, default=False)
    transform = db.Column(db.Boolean, default=False)

    doc_id = db.Column(db.Integer, db.ForeignKey("project_files.id"))
    doc = db.relationship("FileDB", foreign_keys=[doc_id])

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    project = db.relationship("Project", foreign_keys=project_id)

    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approve = db.relationship("User", foreign_keys=approve_id)

    def __repr__(self):
        return "<Extension for project {}>".format(self.project.get_name())

    def to_dict(self):
        return {
            "id": self.id,
            "reason": self.reason,
            "hours": self.hours,
            "created": self.created.timestamp(),
            "modified": self.modified,
            "accepted": self.accepted,
            "processed": self.processed,
            "decision": self.decision,
            "allocation": self.allocation,
            "present_use": self.present_use,
            "present_total": self.present_total,
            "activate": self.activate,
            "transform": self.transform,
            "project": self.project.id,
            "total": self.present_total,
            "use": self.present_use,
            "usage": self.usage_percent,
            "project_name": self.project.get_name(),
            #            "approve": self.approve.full_name(),
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


class FileDB(db.Model):
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

    valid = db.Column(db.Boolean, default=False)
    cpu = db.Column(db.Integer, db.CheckConstraint("cpu>=0"))
    type = db.Column(db.String(1),
                     db.CheckConstraint("type IN ('a', 'b', 'c', 'h')"))
    comment = db.Column(db.Text)
    created = db.Column(db.DateTime(True))
    modified = db.Column(db.DateTime(True))

    def to_dict(self):
        return {
            "id": self.id,
            "approve": self.approve.to_dict(),
            "valid": self.valid,
            "cpu": self.cpu,
            "type": self.type,
            "comment": self.comment,
            "created": self.created,
            "modified": self.modified
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

    def __repr__(self):
        return '<User {}>'.format(self.login)

    def full_name(self):
        return "%s %s" % (self.name.capitalize(), self.surname.capitalize())

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

    def project_ids(self):
        projects = list(self.project)
        ids = map(lambda x: x.id, projects)
        return list(ids)

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
    type_a = db.Column(db.Boolean, default=True)
    type_b = db.Column(db.Boolean, default=False)
    type_c = db.Column(db.Boolean, default=False)
    type_h = db.Column(db.Boolean, default=False)
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
    comment = db.Column(db.String)
    created = db.Column(db.Boolean)
    created_ts = db.Column(db.DateTime(True))

    def __repr__(self):
        return "<Registration request {}>".format(self.id)

    def project_type(self):
        if self.type_a:
            return "A"
        if self.type_b:
            return "B"
        if self.type_c:
            return "C"
        if self.type_h:
            return "H"

    def project_id(self):
        year = dt.now().year
        return "meso-%s-%s-%s" % (year, self.id, self.project_type())

    def get_users(self):
        users = self.users.split("\n")
        result = []
        for user in users:
            tmp = {}
            info = user.split(";")
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
            "type_a": self.type_a,
            "type_b": self.type_b,
            "type_c": self.type_c,
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
            "meso_id": self.project_id()
        }


class LogDB(db.Model):
    __tablename__ = "project_logs"

    id = db.Column(db.Integer, primary_key=True)

    created = db.Column(db.DateTime(True), default=dt.utcnow)
    event = db.Column(db.Text, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", foreign_keys=author_id)

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"),
                           nullable=False)
    project = db.relationship("Project", foreign_keys=project_id)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", foreign_keys=user_id)

    articles_id = db.Column(db.Integer, db.ForeignKey("project_articles.id"))
    articles = db.relationship("ArticleDB", foreign_keys=articles_id)

    extension_id = db.Column(db.Integer, db.ForeignKey("project_extension.id"))
    extension = db.relationship("Extend", foreign_keys=extension_id)

    files_id = db.Column(db.Integer, db.ForeignKey("project_files.id"))
    files = db.relationship("FileDB", foreign_keys=files_id)

    resources_id = db.Column(db.Integer, db.ForeignKey("project_resources.id"))
    resources = db.relationship("Resources", foreign_keys=resources_id)

    def __repr__(self):
        return "<Log event for project {}>".format(self.project.get_name())

    def to_dict(self):
        event = self.event[0].upper() + self.event[1:]
        creator = self.author.full_name()
        if self.user_id:
            msg = "%s %s <%s> by %s" % (event, self.user.full_name(),
                                        self.user.email, creator)
        elif self.resources_id:
            cpu = self.resources.cpu
            msg = "%s: %s hours by %s" % (event, cpu, creator)
        elif self.extension_id:
            if self.extension.activate:
                msg = "%s for activation by %s" % (event, creator)
            elif self.extension.transform:
                msg = "%s for transformation by %s" % (event, creator)
            else:
                cpu = self.extension.hours
                msg = "%s for %s hours by %s" % (event, cpu, creator)
        else:
            msg = "%s by %s" % (event, creator)
        return {
            "date": self.created.strftime("%Y-%m-%d %X %Z"),
            "message": msg
        }


class Tasks(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(6),
                       db.CheckConstraint("action IN ('create', 'update',"
                                          " 'delete')"), nullable=False)
    status = db.Column(db.String(11), db.CheckConstraint(
        "status IN ('pending', 'done', 'in progress')"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", foreign_keys=author_id)

    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"),
                           nullable=False)
    approve = db.relationship("User", foreign_keys=approve_id)

    decision = db.Column(db.String(6),
                         db.CheckConstraint("decision IN ('accept', 'reject',"
                                            " 'ignore')"))
    processed = db.Column(db.Boolean)

    created = db.Column(db.DateTime(True), default=dt.utcnow)
    modified = db.Column(db.DateTime(True))

    limbo_uid = db.Column(db.Integer, db.ForeignKey("limbo_users.id"))
    limbo_user = db.relationship("LimboUser", foreign_keys=limbo_uid)

    limbo_pid = db.Column(db.Integer, db.ForeignKey("limbo_projects.id"))
    limbo_project = db.relationship("LimboProject", foreign_keys=limbo_pid)

    def __repr__(self):
        return "<Task queue record {}>".format(self.id)

    def to_dict(self):
        if self.modified:
            modified = self.modified.strftime("%Y-%m-%d %X %Z")
        else:
            modified = ""
        if self.limbo_user and self.limbo_project:
            human = "%s %s in %s" % (self.action, self.limbo_user.login,
                                     self.limbo_project.get_name())
        elif self.limbo_user:
            human = "%s %s" % (self.action, self.limbo_user.login)
        elif self.limbo_project:
            human = "%s %s" % (self.action, self.limbo_project.title)
        return {
            "id": self.id,
            "action": self.action,
            "status": self.status,
            "author": self.author.login,
            "approve": self.approve.full_name() if self.approve else "",
            "decision": self.decision,
            "processed": self.processed,
            "created": self.created.strftime("%Y-%m-%d %X %Z"),
            "modified": modified,
            "human": human
        }


class LimboProject(db.Model):
    __tablename__ = "limbo_projects"

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
    allocation_end = db.Column(db.DateTime(True))
    comment = db.Column(db.Text)
    gid = db.Column(db.Integer)
    privileged = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(128))
    type = db.Column(db.String(1),
                     db.CheckConstraint("type IN ('a', 'b', 'c', 'h')"))
    ref_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    reference = db.relationship("Project", foreign_keys=ref_id)

    def __repr__(self):
        return '<Limbo Project {}>'.format(self.get_name())

    def get_name(self):
        if self.name:
            return self.name
        pid = self.id
        genre = self.type
        return "%s%s" % (genre, str(pid).zfill(3))

    def to_dict(self):
        if self.created:
            created = self.created.strftime("%Y-%m-%d %X %Z")
        else:
            created = ""
        if self.modified:
            modified = self.modified.strftime("%Y-%m-%d %X %Z")
        else:
            modified = ""
        if self.allocation_end:
            allocation = self.allocation_end.strftime("%Y-%m-%d %X %Z")
        else:
            allocation = ""
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
            "files": self.files,
            "articles": self.articles,
            "users": list(map(lambda x: x.to_dict(), self.users)),
            "approve": self.approve.to_dict(),
            "resources": self.resources.to_dict(),
            "allocation_end": allocation,
            "ref": self.ref.id
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

    def __repr__(self):
        return '<Limbo User {}>'.format(self.login)
