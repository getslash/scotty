import json
from datetime import datetime, time
from typing import TYPE_CHECKING, Any

import flux
from flask_login import UserMixin
from flask_security import RoleMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship as sqlalchemy_relationship

db = SQLAlchemy()

if TYPE_CHECKING:

    class BaseModel:
        query: Any

        def __init__(self, *args: Any, **kwargs: Any):
            pass


else:
    BaseModel = db.Model


### Add models here

roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id", ondelete="CASCADE")),
    db.Column("role_id", db.Integer(), db.ForeignKey("role.id", ondelete="CASCADE")),
)


class Pin(BaseModel):
    __table_args__ = (db.UniqueConstraint("beam_id", "user_id", name="uix_pin"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    beam_id = db.Column(db.Integer, db.ForeignKey("beam.id"), index=True)


class Role(BaseModel, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(BaseModel, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True)
    name = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )
    pins = db.relationship("Pin", backref="user")

    @property
    def is_anonymous_user(self):
        return self.email == "anonymous@getslash.github.io"


class Tracker(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True, unique=True)
    type = db.Column(db.String, nullable=False)
    config = db.Column(db.String)
    url = db.Column(db.String, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "url": self.url,
            "config": json.loads(self.config),
        }

    def issue_url(self, issue_id):
        if self.type == "jira":
            return "{}/browse/{}".format(self.url, issue_id)
        else:
            return ""


class Issue(BaseModel):
    __table_args__ = (
        db.UniqueConstraint("tracker_id", "id_in_tracker", name="uix_unique_issue"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tracker_id = db.Column(
        db.Integer, db.ForeignKey("tracker.id", ondelete="CASCADE"), index=True
    )
    tracker = db.relationship("Tracker")
    id_in_tracker = db.Column(db.String, nullable=False, index=True)
    open = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        url = self.tracker.issue_url(self.id_in_tracker)
        return {
            "id": self.id,
            "tracker_id": self.tracker_id,
            "id_in_tracker": self.id_in_tracker,
            "open": self.open,
            "url": url,
        }


beam_issues = db.Table(
    "beam_issues",
    db.Column(
        "beam_id",
        db.Integer(),
        db.ForeignKey("beam.id", ondelete="CASCADE"),
        index=True,
    ),
    db.Column("issue_id", db.Integer(), db.ForeignKey("issue.id", ondelete="CASCADE")),
)


class Beam(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime, index=True)
    end = db.Column(db.DateTime, index=True, nullable=True)
    size = db.Column(db.BigInteger)
    host = db.Column(db.String)
    comment = db.Column(db.String)
    directory = db.Column(db.String)
    type_id = db.Column(
        db.Integer, db.ForeignKey("beam_type.id", name="beam_type_fkey"), nullable=True
    )
    type = db.relationship("BeamType")
    pending_deletion = db.Column(db.Boolean, index=True)
    error = db.Column(db.String)
    deleted = db.Column(db.Boolean, index=True)
    completed = db.Column(db.Boolean, index=True)
    combadge_contacted = db.Column(db.Boolean, nullable=False, server_default="true")
    initiator = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    files = db.relationship("File", backref=backref("beam", lazy="joined"))
    pins = db.relationship("Pin", backref="beam")
    issues = db.relationship("Issue", secondary=beam_issues)
    tags: sqlalchemy_relationship

    def get_purge_time(self, default_threshold):
        if not self.completed:
            return None

        if self.size == 0:
            return 0

        if self.pins:
            return None

        if any(i.open for i in self.issues):
            return None

        threshold = (
            self.type.vacuum_threshold if self.type is not None else default_threshold
        )
        days = (
            threshold
            - (
                flux.current_timeline.datetime.utcnow()
                - datetime.combine(self.start, time(0, 0))
            ).days
        )
        return max(days, 0)

    def set_completed(self, completed):
        if self.completed == completed:
            return
        self.completed = completed
        if completed:
            if self.end is None:
                self.end = flux.current_timeline.datetime.utcnow()
        else:
            self.end = None

    def to_dict(self, default_threshold):
        return {
            "id": self.id,
            "host": self.host,
            "completed": self.completed,
            "start": self.start.isoformat() + "Z",
            "end": self.end.isoformat() + "Z" if self.end else None,
            "size": self.size,
            "comment": self.comment,
            "initiator": self.initiator,
            "purge_time": self.get_purge_time(default_threshold),
            "type": None if not self.type else self.type.name,
            "error": self.error,
            "directory": self.directory,
            "deleted": self.pending_deletion or self.deleted,
            "pins": [u.user_id for u in self.pins],
            "tags": [t.tag for t in self.tags],  # pylint: disable=E1101
            "associated_issues": [i.id for i in self.issues],
        }

    def __repr__(self):
        return "<Beam(id='%s')>" % (self.id,)


class BeamType(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True, unique=True, nullable=False)
    vacuum_threshold = db.Column(db.Integer, nullable=False)


class Tag(BaseModel):
    __table_args__ = (db.UniqueConstraint("beam_id", "tag", name="uix_beam_tag"),)

    def __init__(self, *, tag, **kwargs):
        tag = tag.strip().lower()
        super().__init__(tag=tag, **kwargs)

    id = db.Column(db.Integer, primary_key=True)
    beam_id = db.Column(db.Integer, db.ForeignKey("beam.id"), index=True)
    beam = db.relationship("Beam", backref="tags")
    tag = db.Column(db.String, index=True)


class File(BaseModel):
    __table_args__ = (db.UniqueConstraint("beam_id", "file_name", name="uix_1"),)

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String)
    beam_id = db.Column(db.Integer, db.ForeignKey("beam.id"), index=True)
    status = db.Column(db.String(25))
    size = db.Column(db.BigInteger)
    checksum = db.Column(db.String)
    mtime = db.Column(db.DateTime)
    last_validated = db.Column(db.DateTime, index=True)
    storage_name = db.Column(db.String)

    def __repr__(self):
        return "<File(id='%s', name='%s', beam='%s')>" % (
            self.id,
            self.file_name,
            self.beam_id,
        )


class Key(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String, nullable=False, unique=True)
    key = db.Column(db.String, nullable=False)

    def to_dict(self):
        return {"id": self.id, "description": self.description}
