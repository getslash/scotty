from typing import Any, Type

from flask import Flask
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Interval,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.session import Session
from flask_sqlalchemy.SQLAlchemy import relationship as flask_sqlalchemy_relationship


class SQLAlchemy:
    def __init__(self):
        ...

    def init_app(self, app: Flask) -> None:
        pass

    Model: Any
    engine: Any

    Column = Column
    Integer = Integer
    ForeignKey = ForeignKey
    Index = Index
    String = String
    Boolean = Boolean
    DateTime = DateTime
    Table = Table
    Interval = Interval
    BigInteger = BigInteger
    relationship = relationship
    backref = backref
    UniqueConstraint = UniqueConstraint
    flask_sqlalchemy_relationship = flask_sqlalchemy_relationship

    session: Session
