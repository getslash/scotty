# pylint: disable=redefined-outer-name
import os
import datetime

import flask_migrate
import pytest

from flask_app.blueprints import user_datastore
from flask_app.models import db
from flask_app.tasks import queue
from flask_app.app import get_or_create_app
from flask_app.models import Beam, Issue, Tracker, File


@pytest.fixture
def storage_path(tmpdir):
    with open(str(tmpdir / ".test"), "w") as f:
        f.write("")
    return str(tmpdir)


@pytest.fixture
def vacuum_threshold():
    return 60


@pytest.fixture
def app_context(monkeypatch, storage_path, vacuum_threshold):
    app = get_or_create_app(
        config={
            "SQLALCHEMY_DATABASE_URI": os.environ.get(
                "SCOTTY_DATABASE_URI", "postgresql://localhost/scotty_test"
            ),
            "STORAGE_PATH": storage_path,
            "VACUUM_THRESHOLD": vacuum_threshold,
            "TRANSPORTER_HOST": "scotty",
        }
    )
    app_context = app.app_context()
    monkeypatch.setattr(app, "app_context", lambda: app_context)
    with app_context:
        flask_migrate.Migrate(app, db)
        flask_migrate.upgrade()
        yield app


@pytest.fixture
def _db(app_context):
    return db


@pytest.fixture
def eager_celery():
    queue.conf.update(CELERY_ALWAYS_EAGER=True)
    yield
    queue.conf.update(CELERY_ALWAYS_EAGER=False)


@pytest.fixture
def user():
    name = "scotty_testing"
    email = "scotty@testing.infinidat.com"
    user = user_datastore.get_user(email)
    if not user:
        user = user_datastore.create_user(
            email=email,
            name=name)
        user_datastore.db.session.commit()
    return user


@pytest.fixture
def host():
    return "mock-host"


@pytest.fixture
def directory(tmpdir):
    return str(tmpdir)


@pytest.fixture
def file(db_session):
    file = File(file_name="mock-file")
    db_session.add(file)
    db_session.commit()
    return file


@pytest.fixture
def create_beam(db_session, host, user, directory, file):
    def _create(*, start, completed, add_file=True):
        beam = Beam(
            start=start, size=0,
            host=host,
            comment='',
            directory=directory,
            initiator=user.id,
            error=None,
            combadge_contacted=False,
            pending_deletion=False, completed=completed, deleted=False)
        if add_file:
            beam.files.append(file)
        db_session.add(beam)
        db_session.commit()
        return beam

    return _create


@pytest.fixture
def now():
    return datetime.datetime.utcnow()


@pytest.fixture
def expired_beam_date(now, vacuum_threshold):
    return now - datetime.timedelta(days=vacuum_threshold + 1)


@pytest.fixture
def tracker(db_session):
    tracker = Tracker(
        config='{}',
        name="JIRA",
        type="jira",
        url="https://mock-jira",
    )
    db_session.add(tracker)
    db_session.commit()
    return tracker


@pytest.fixture
def issue(db_session, tracker):
    issue = Issue(tracker_id=tracker.id, id_in_tracker="mock-ticket-1", open=True)
    db_session.add(issue)
    db_session.commit()
    return issue