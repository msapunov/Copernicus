from flask_login import UserMixin, current_user
from base import db
from base.functions import generate_password, process_register_user
from datetime import datetime as dt
from textwrap import shorten
from logging import error
from pathlib import PurePath
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from re import split as re_split


__author__ = "Matvey Sapunov"
__copyright__ = "Aix Marseille University"


class Accounting(db.Model):
    __tablename__ = "accounting"
    id = db.Column(db.Integer, primary_key=True)
    resources_id = db.Column(db.Integer, db.ForeignKey("project_resources.id"))
    resources = db.relationship("Resources", foreign_keys=resources_id)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    project = db.relationship("Project", foreign_keys=project_id)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", foreign_keys=user_id)
    date = db.Column(db.DateTime(True))
    cpu = db.Column(db.Integer, db.CheckConstraint("cpu>=0"))

    def __repr__(self):
        return '<Account ID {}>'.format(self.id)


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
    users = db.relationship("User", secondary="user_project",
                            back_populates="project")

    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approve = db.relationship("User", foreign_keys=approve_id)

    resources_id = db.Column(db.Integer, db.ForeignKey("project_resources.id"))
    resources = db.relationship("Resources", foreign_keys=resources_id)

    ref_id = db.Column(db.Integer, db.ForeignKey("register.id"))
    ref = db.relationship("Register", foreign_keys=ref_id)

    def __repr__(self):
        return '<Project {}>'.format(self.get_name())

    def account_by_user(self, user=None):
        result = self.resources.group_by_user()
        if not result:
            return {}
        return {key: value for key, value in result}

    def user_account(self, user=current_user):
        result = self.resources.user_consumption(user)
        return result if result else 0

    def account_group(self, daily=None):
        query = (Accounting.query.join(User, Accounting.user_id == User.id)
                 .filter(Accounting.resources_id == self.resources_id))
        if daily:
            result = query.group_by(
                User.login, Accounting.date
            ).with_entities(
                User.login, Accounting.date, func.sum(Accounting.cpu)
            ).all()
            return {i[1].strftime("%Y-%m-%d"): {i[0]: i[2]} for i in result}
        else:
            result = query.group_by(
                User.login
            ).with_entities(
                User.login, func.sum(Accounting.cpu)
            ).all()
            return {i[0]: i[1] for i in result }

    def account(self):
        result = self.resources.consumption()
        return result if result else 0

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
        rec["approve"] = self.approve.full_name()
        rec["lab"] = self.responsible.lab
        rec["responsible"] = self.responsible.full_name()
        rec["resources"] = self.resources.cpu
        tmp = ["%s <%s>" % (u.full_name(), u.email) for u in self.users]
        rec["users"] = tmp
        return rec

    def consumed(self):
        return self.resources.usage()

    def consumed_use(self):
        usage = self.resources.usage()  # with percents
        return float(usage.replace("%", "")) if usage else 0

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
        if self.responsible:
            responsible = self.responsible.to_dict()
            responsible_login = self.responsible.login
        else:
            responsible = ""
            responsible_login = ""
        if self.ref:
            ref = self.ref.project_id()
        else:
            ref = ""
        usage = self.resources.usage()  # with percents
        use = float(usage.replace("%", "")) if usage else 0
        result = {
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
            "responsible": responsible,
            "responsible_login": responsible_login,
            "files": list(map(lambda x: x.path, self.files)),
            "articles": list(map(lambda x: x.info, self.articles)),
            "users": list(map(lambda x: x.to_dict(), self.users)),
            "approve": self.approve.to_dict(),
            "resources": self.resources.to_dict(),
            "allocation_start": start,
            "allocation_end": end,
            "ref": ref,
            "total": self.resources.cpu if self.resources else 0,
            "consumed": self.account(),
            "consumed_use": use,
            "consumed_usage": usage
        }
        return result


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

    def about(self):
        result = ""
        if self.exception:
            result += "exceptional "
        if self.transform != " ":
            result += "transformation"
        elif self.activate:
            result += "activation"
        else:
            if self.extend:
                result += "extension"
            else:
                result += "renewal"
        return result

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
        usage = self.project.resources.usage().replace("%", "")  # No percents
        use = self.project.resources.consumption()
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
            "present_use": use,  # Should be inverse with use
            "present_usage": usage,
            "name": self.project.get_name(),
            "approve": approve,
            "responsible": self.project.responsible.full_name(),
            "responsible_login": self.project.responsible.login,
            "about": self.about()
        }


class ArticleDB(db.Model):
    __tablename__ = "project_articles"

    id = db.Column(db.Integer, primary_key=True)
    info = db.Column(db.Text)
    created = db.Column(db.DateTime(True), default=dt.utcnow())

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
    created = db.Column(db.DateTime(True), default=dt.utcnow())

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    project = db.relationship("Project", back_populates="files")
    user = db.relationship("User", foreign_keys=user_id)

    def name(self):
        return PurePath(self.path).name


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
    created = db.Column(db.DateTime(True), default=dt.utcnow())
    ttl = db.Column(db.DateTime(True))
    project = db.Column(db.String)
    treated = db.Column(db.Boolean, default=False)

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

    def user_consumption(self, user=current_user):
        return Accounting.query.filter_by(
            resources=self, user=user
        ).with_entities(func.sum(Accounting.cpu)).scalar()

    def consumption(self):
        return Accounting.query.filter_by(
            resources=self, user=None
        ).with_entities(func.sum(Accounting.cpu)).scalar()

    def usage(self):
        conso = self.consumption()
        total = self.cpu
        if not conso:
            return "0%"
        try:
            return "{0:.1%}".format(float(conso) / float(total))
        except TypeError as err:
            error("Failed to calculate project usage: %s" % err)
            return "0%"


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
    project = db.relationship("Project", secondary="user_project",
                              back_populates="users")
    active = db.Column(db.Boolean, default=False)
    comment = db.Column(db.Text)
    modified = db.Column(db.DateTime(True))
    created = db.Column(db.DateTime(True))
    uid = db.Column(db.Integer)
    hash = db.Column(db.String(128))
    first_login = db.Column(db.Boolean, default=True)
    seen = db.Column(db.DateTime(True))

    def __repr__(self):
        return '<User {}>'.format(self.login)

    def task_description(self):
        """
        Creates task's description out of instance of TmpUser
        :return: String. Task's description
        """
        u_part = "login: %s and name: %s and surname: %s and email: %s" % (
            self.login, self.name, self.surname, self.email)
        if getattr(self, "acl", False):
            self = self.acl
        is_user = getattr(self, "is_user", False)
        is_resp = getattr(self, "is_responsible", False)
        is_mngr = getattr(self, "is_manager", False)
        is_tech = getattr(self, "is_tech", False)
        is_comm = getattr(self, "is_committee", False)
        is_admin = getattr(self, "is_admin", False)
        a_part = "user: %s, responsible: %s, manager: %s, tech: %s, " \
                 "committee: %s, admin: %s" % (is_user, is_resp, is_mngr,
                                               is_tech, is_comm, is_admin)
        return "%s WITH ACL %s" % (u_part, a_part)

    def reset_password(self):
        password = generate_password()
        self.hash = generate_password_hash(password)
        self.first_login = True
        db.session.commit()
        return password

    def set_password(self, password):
        self.hash = generate_password_hash(password)
        self.first_login = False
        db.session.commit()
        return password

    def check_password(self, password):
        return check_password_hash(self.hash, password)

    def full(self):
        return "%s <%s> [%s]" % (self.full_name(), self.email, self.login)

    def full_name(self):
        result = []
        for name in [self.name, self.surname]:
            if not name:
                continue
            name_parts = re_split('[\/.,\'\s-]', name)
            for part in name_parts:
                cap = part.capitalize()
                name = name.replace(part, cap)
            result.append(name)
        return " ".join(result)

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
        if self.acl.created:
            start = self.acl.created.strftime("%Y-%m-%d %X %Z")
        else:
            start = ""
        if self.acl.modified:
            mod = self.acl.modified.strftime("%Y-%m-%d %X %Z")
        else:
            mod = ""
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
            "seen": self.seen.strftime("%Y-%m-%d %X %Z") if self.seen else "",
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
            "brief": self.full(),
            "projects": self.project_names(),
            "password": True if self.hash else False,
            "first": self.first_login
        }

    def info_acl(self):
        return {
            "active": self.active,
            "user": self.acl.is_user,
            "responsible": self.acl.is_responsible,
            "manager": self.acl.is_manager,
            "tech": self.acl.is_tech,
            "committee": self.acl.is_committee,
            "admin": self.acl.is_admin,
            "login": self.login,
            "name": self.name,
            "surname": self.surname,
            "seen": self.seen.strftime("%Y-%m-%d %X %Z") if self.seen else "",
            "email": self.email
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
            "seen": self.seen.strftime("%Y-%m-%d %X %Z") if self.seen else "",
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
    cloud_image = db.Column(db.String)
    status = db.Column(db.String)

    def __repr__(self):
        return "<Registration request {}>".format(self.id)

    def project_type(self):
        return self.type.upper()

    def project_id(self):
        year = dt.now().year
        return "meso-%s-%s-%s" % (year, self.id, self.project_type())

    def responsible_full_name(self):
        first = self.responsible_first_name
        last = self.responsible_last_name
        if first and last:
            return "%s %s" % (first.capitalize(), last.capitalize())
        if first:
            return first.capitalize()
        if last:
            return last.capitalize()

    def get_users(self):
        users = self.users.split("\n")
        return [{"name": name if name else "",
                 "last": surname if surname else "",
                 "mail": email if email else "",
                 "login": login if login else ""}
                for x in users
                for name, surname, email, login in [process_register_user(x)]]

    def cloud(self):
        return [
            "registration id: %s" % self.id,
            "title: %s" % self.title,
            "type: %s" % self.project_type(),
            "cloud image: %s" % self.cloud_image,
            "responsible full name: %s" % self.responsible_full_name(),
            "users: %s" % self.get_users(),
            "description: %s" % self.description,
            "created: %s" % self.created,
            "status: %s" % self.status,
            "mesocentre id: %s" % self.project_id()
        ]

    def logs(self, obj=False):
        logs = LogDB.query.filter_by(register=self).all()
        if obj:
            return logs
        return list(map(lambda x: x.to_dict(), logs))

    def to_dict(self):
        return {
            "id": self.id,
            "ts": self.ts.strftime("%Y-%m-%d %X %Z"),
            "ts_full": self.ts.strftime("%c"),
            "title": self.title,
            "cloud_image": self.cloud_image,
            "responsible_full_name": self.responsible_full_name(),
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
            "status": self.status,
            "type": self.project_type(),
            "meso_id": self.project_id()
        }


class LogDB(db.Model):
    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True)

    created = db.Column(db.DateTime(True), default=dt.utcnow())
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

    register_id = db.Column(db.Integer, db.ForeignKey("register.id"))
    register = db.relationship("Register", foreign_keys=register_id)

    def __repr__(self):
        return "<Log event for project {}>".format(self.project.get_name())

    def brief(self):
        event = self.event.capitalize()
        creator = self.author.full_name() if self.author else "Unknown author"
        return {"created": self.created, "event": "%s by %s" % (event, creator)}

    def to_web(self):
        event = self.event.capitalize()
        if "ssh" in event:
            event = event[:50] + "..." + event[-50:]
        creator = self.author.full_name() if self.author else "Unknown author"
        msg = "%s by %s" % (event, creator)
        if self.project:
            item = self.project.name
            category = "project"
        elif self.register:
            item = self.register.project_id()
            category = "registration"
        elif self.user:
            item = self.user.full_name()
            category = "user"
        else:
            item = ""
            category = "unknown"
        return {
            "project": self.project.name if self.project else "",
            "item": item,
            "category": category,
            "date": self.created.strftime("%Y-%m-%d %X %Z"),
            "date_full": self.created.strftime("%c"),
            "message": msg
        }

    def to_dict(self):
        event = self.event[0].upper() + self.event[1:]
        creator = self.author.full_name() if self.author else "Unknown author"
        msg = "%s by %s" % (event, creator)
        short = shorten(msg, width=50, placeholder="...")
        return {
            "date": self.created.strftime("%Y-%m-%d %X %Z"),
            "date_full": self.created.strftime("%c"),
            "message": short,
            "message_full": msg
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
    result = db.Column(db.Text, default=None)
    comment = db.Column(db.String, default=None)

    created = db.Column(db.DateTime(True), default=dt.utcnow())
    modified = db.Column(db.DateTime(True))

    uid = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", foreign_keys=uid)

    pid = db.Column(db.Integer, db.ForeignKey("projects.id"))
    project = db.relationship("Project", foreign_keys=pid)

    def __repr__(self):
        return "<Task queue record {}>".format(self.id)

    def waiting(self):
        return self.query.filter_by(processed=True,
                                    done=False,
                                    decision="accept").all()

    def accept(self):
        self.decision = "accept"
        self.processed = True
        self.approve = current_user
        db.session.commit()
        return self

    def brief(self):
        act, entity, login, project, task = self.action.split("|")
        if act in ["create", "add", "assign", "delete", "remove", "activate"]:
            if entity == "user":
                act += " a user "
            else:
                act += " a project "
        elif act in ["ssh"]:
            act = "upload SSH key "
        elif act in ["update"]:
            act += " user's info "
        act = act[0].upper() + act[1:].lower()
        if self.author:
            act += "by %s" % self.author.full_name()
        else:
            act += "by Automatic Service"
        return act

    def description(self):
        act, entity, login, project, task = self.action.split("|")
        if act in ["create", "activate"]:
            if "new project" in task:
                return task
            act += " a user with %s for the project %s" % (task, project)
        if act in ["assign", "remove"]:
            return task
        elif act in ["update"]:
            act += " user info for %s with following data: %s" % (login, task)
        elif act in ["ssh"]:
            short = "%s ... %s" % (task[:20], task[-20:])
            act = "upload SSH public key: %s" % short
        act = act[0].upper() + act[1:]
        if self.comment:
            act = act + " " + self.comment
        return act

    def notify(self):
        if "update" in self.action and self.project:
            return self.author.email
        elif ("change" in self.action) and ("password" in self.action):
            return self.user.email
        elif self.author and self.project:
            if self.project.responsible and self.project.responsible.email:
                return self.project.responsible.email
            else:
                return ""
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
            "result": self.result,
            "comment": self.comment,
            "modified": mod
        }
