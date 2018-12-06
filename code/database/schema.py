from flask_login import UserMixin
from code import db, login


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
#    projects = db.relationship("ProjectDB", secondary="user_project")
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

    def to_dict(self):
        return {
            "id": self.id,
            "login": self.login,
            "name": self.name,
            "surname": self.surname,
            "email": self.email,
            "phone": self.phone,
            "lab": self.lab,
            "position": self.position,
            "active": self.active,
            "comment": self.comment,
#            "last_seen": self.last_seen.isoformat() + 'Z'
            "modified": self.modified,
            "created": self.created
        }
