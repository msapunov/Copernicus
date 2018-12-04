from flask_login import UserMixin
from code import db, login


class User(UserMixin, db.Model):

    __tablename__ = "users"
    __bind_key__ = "management"

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
    projects = db.relationship("ProjectDB", secondary="user_project")
    active = db.Column(db.Boolean, default=False)
    comment = db.Column(db.Text)
    modified = db.Column(db.DateTime(True))
    created = db.Column(db.DateTime(True))

    def __repr__(self):
        return '<User {}>'.format(self.login)


@login.user_loader
def load_user(userid):
    return User.query.filter(User.id == userid).first()
