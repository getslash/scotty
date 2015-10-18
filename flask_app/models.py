from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import UserMixin, RoleMixin
from sqlalchemy.orm import backref

db = SQLAlchemy()

### Add models here

roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE')))


class Pin(db.Model):
    __table_args__ = (db.UniqueConstraint('beam_id', 'user_id', name='uix_pin'), )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    beam_id = db.Column(db.Integer, db.ForeignKey('beam.id'))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    pins = db.relationship("Pin", backref="user")

    @property
    def is_anonymous_user(self):
        return self.email == "anonymous@infinidat.com"


class Beam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime, index=True)
    size = db.Column(db.BigInteger)
    host = db.Column(db.String)
    directory = db.Column(db.String)
    pending_deletion = db.Column(db.Boolean, index=True)
    error = db.Column(db.String)
    deleted = db.Column(db.Boolean, index=True)
    completed = db.Column(db.Boolean, index=True)
    combadge_contacted = db.Column(db.Boolean, nullable=False, server_default="true")
    initiator = db.Column(db.Integer, db.ForeignKey('user.id'))
    files = db.relationship("File", backref=backref("beam", lazy="joined"))
    pins = db.relationship("Pin", backref="beam")

    def __repr__(self):
        return "<Beam(id='%s')>" % (self.id, )


class Tag(db.Model):
    __table_args__ = (db.UniqueConstraint('beam_id', 'tag', name='uix_beam_tag'), )

    id = db.Column(db.Integer, primary_key=True)
    beam_id = db.Column(db.Integer, db.ForeignKey('beam.id'))
    beam = db.relationship("Beam", backref="tags")
    tag = db.Column(db.String, index=True)


class File(db.Model):
    __table_args__ = (db.UniqueConstraint('beam_id', 'file_name', name='uix_1'), )

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String)
    beam_id = db.Column(db.Integer, db.ForeignKey('beam.id'))
    status = db.Column(db.String(25))
    size = db.Column(db.BigInteger)
    checksum = db.Column(db.String)
    last_validated = db.Column(db.DateTime, index=True)
    storage_name = db.Column(db.String)

    def __repr__(self):
        return "<File(id='%s', name='%s', beam='%s')>" % (self.id, self.file_name, self.beam_id)
