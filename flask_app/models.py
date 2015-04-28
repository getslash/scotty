from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import UserMixin, RoleMixin

db = SQLAlchemy()

### Add models here

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Pin(db.Model):
    __table_args__ = (db.UniqueConstraint('beam_id', 'user_id', name='uix_pin'), ) # Index

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


class Beam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime, index=True)
    size = db.Column(db.BigInteger)
    host = db.Column(db.String)
    directory = db.Column(db.String)
    pending_deletion = db.Column(db.Boolean, index=True)
    error = db.Column(db.String)
    deleted = db.Column(db.Boolean, index=True)
    completed = db.Column(db.Boolean)
    initiator = db.Column(db.Integer, db.ForeignKey('user.id'))
    files = db.relationship("File", backref="beam")
    pins = db.relationship("Pin", backref="beam")

    def __repr__(self):
        return "<Beam(id='%s')>" % (self.id, )


class File(db.Model):
    __table_args__ = (db.UniqueConstraint('beam_id', 'file_name', name='uix_1'), ) # Index

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String)
    beam_id = db.Column(db.Integer, db.ForeignKey('beam.id'))
    status = db.Column(db.String(25))
    size = db.Column(db.BigInteger)
    storage_name = db.Column(db.String)

    def __repr__(self):
        return "<File(id='%s', name='%s', beam='%s')>" % (self.id, self.file_name, self.beam_id)
