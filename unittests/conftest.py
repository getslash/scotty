# pylint: disable=redefined-outer-name
import datetime
import io
import os
import pathlib
import shutil
import sys
from unittest import mock
from uuid import UUID

import flask_migrate
import logbook
import munch
import pytest
from flask import current_app

from flask_app import paths
from flask_app.app import get_or_create_app
from flask_app.blueprints import user_datastore
from flask_app.models import Beam, File, Issue, Tracker, db
from flask_app.tasks import queue, setup_log
from flask_app.utils import remote_combadge, remote_host
from flask_app.utils.remote_host import RemoteHost

_TEMPDIR_COMMAND = RemoteHost._TEMPDIR_COMMAND


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
            "TESTING": True,
            "DEBUG": True,
        }
    )
    app_context = app.app_context()
    monkeypatch.setattr(app, "app_context", lambda: app_context)
    with app_context:
        flask_migrate.Migrate(app, db)
        flask_migrate.upgrade()
        logs = logbook.StreamHandler(sys.stdout, bubble=True)
        logs.push_application()
        yield app
        logs.pop_application()


@pytest.fixture
def client(app_context):
    return app_context.test_client()


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
        user = user_datastore.create_user(email=email, name=name)
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
            start=start,
            size=0,
            host=host,
            comment="",
            directory=directory,
            initiator=user.id,
            error=None,
            combadge_contacted=False,
            pending_deletion=False,
            completed=completed,
            deleted=False,
        )
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
    tracker = Tracker(config="{}", name="JIRA", type="jira", url="https://mock-jira",)
    db_session.add(tracker)
    db_session.commit()
    return tracker


@pytest.fixture
def issue(db_session, tracker):
    issue = Issue(tracker_id=tracker.id, id_in_tracker="mock-ticket-1", open=True)
    db_session.add(issue)
    db_session.commit()
    return issue


class MockSSHClient:
    instances = []

    def __init__(self):
        self.instances.append(self)
        self.policy = None
        self.connect_args = None
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
        self.exit_status = 0
        self.stdout.channel = munch.Munch(recv_exit_status=lambda: self.exit_status)
        self.stderr = io.BytesIO()
        self.commands = []
        self.os_type = None

    def exec_command(self, command):
        self.commands.append(command)
        self.exit_status = 0
        self.stdout.truncate(0)
        self.stdout.seek(0)
        if command == "uname":
            if self.os_type == "linux":
                self.stdout.write(b"Linux")
            else:
                self.stderr.write(
                    (
                        b"uname : The term 'uname' is not recognized as the name of a cmdlet, function, script file, "
                        b"or operable program. Check the spelling of the name, or if a path was included, "
                        b"verify that the path is correct and try again."
                    )
                )
                self.exit_status = 1
        elif command == _TEMPDIR_COMMAND:
            if self.os_type == "linux":
                self.stdout.write(b"/tmp")
            else:
                user = self.connect_args["username"]
                self.stdout.write(fr"C:\Users\{user}\AppData\Local\Temp".encode())
        self.stdout.seek(0)
        self.stdin.seek(0)
        self.stderr.seek(0)
        return self.stdin, self.stdout, self.stderr

    def connect(self, host, **kwargs):
        self.connect_args = dict(host=host, **kwargs)
        self.os_type = "linux" if host == "mock-host" else "windows"

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def get_transport(self):
        return "mock-transport"

    def close(self):
        pass

    @classmethod
    def clear(cls):
        cls.instances = []


@pytest.fixture
def mock_ssh_client(monkeypatch):
    monkeypatch.setattr(remote_host, "SSHClient", MockSSHClient)
    MockSSHClient.clear()
    yield MockSSHClient
    MockSSHClient.clear()


class MockSFTPClient:
    instances = []
    files = {}
    trash = []

    def __init__(self):
        self.instances.append(self)
        self.calls = []

    @classmethod
    def from_transport(cls, transport):
        assert transport == "mock-transport"
        return cls()

    def put(self, local, remote):
        self.files[remote] = dict(local=local)
        self.calls.append(dict(action="put", args=dict(local=local, remote=remote)))

    def remove(self, remote):
        self.trash.append(remote)
        self.files.pop(remote)
        self.calls.append(dict(action="remove", args=dict(remote=remote)))

    def chmod(self, remote, mode):
        self.files[remote]["mode"] = mode
        self.calls.append(dict(action="chmod", args=dict(remote=remote, mode=mode)))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass

    @classmethod
    def clear(cls):
        cls.instances = []
        cls.files = {}
        cls.trash = []

    @classmethod
    def get_one_instance_or_raise(cls):
        assert len(cls.instances) == 1, f"Expected one instance, got: {cls.instances}"
        return cls.instances[0]

    def assert_calls_equal_to(self, expected_calls):
        assert len(self.calls) == len(expected_calls)
        for actual_call, expected_call in zip(self.calls, expected_calls):
            if expected_call["action"] == "chmod":
                assert actual_call["args"]["remote"] == expected_call["args"]["remote"]
                assert (
                    actual_call["args"]["mode"] & expected_call["args"]["mode"]
                    == expected_call["args"]["mode"]
                )
            else:
                assert actual_call == expected_call


@pytest.fixture
def mock_sftp_client(monkeypatch):
    monkeypatch.setattr(remote_host, "SFTPClient", MockSFTPClient)
    MockSFTPClient.clear()
    yield MockSFTPClient
    MockSFTPClient.clear()


@pytest.fixture
def mock_rsa_key(monkeypatch):
    RSAKey = mock.MagicMock()
    monkeypatch.setattr(remote_host, "RSAKey", RSAKey)
    return RSAKey


@pytest.fixture
def uuid4(monkeypatch):
    uuid = UUID("f1e8962b-00c9-4799-aacf-5d616163e03d")
    monkeypatch.setattr(remote_combadge, "uuid4", lambda: uuid)
    return uuid


@pytest.fixture
def combadge_assets_dir(tmpdir, monkeypatch):
    tmpdir = pathlib.Path(tmpdir)
    for os, ext in [("linux", ""), ("windows", ".exe")]:
        directory = tmpdir / "v2" / f"combadge_{os}"
        directory.mkdir(parents=True)
        with (directory / f"combadge{ext}").open("w") as f:
            f.write("")
    monkeypatch.setattr(paths, "COMBADGE_ASSETS_DIR", str(tmpdir))
    return str(tmpdir)


@pytest.fixture
def beam_with_real_file(db_session):
    directory = "test-directory"
    file_name = "test-file"
    storage_path = current_app.config["STORAGE_PATH"]
    full_directory = os.path.join(storage_path, directory)
    if os.path.exists(full_directory):
        shutil.rmtree(full_directory)
    os.mkdir(full_directory)
    full_file_location = os.path.join(storage_path, directory, file_name)
    with open(full_file_location, "w") as f:
        f.write("test-content")
    file = File(file_name=file_name, storage_name=os.path.join(directory, file_name))
    beam = Beam(
        start=datetime.datetime.now(),
        directory=directory,
        completed=True,
        files=[file],
    )
    db_session.add(file)
    db_session.add(beam)
    db_session.commit()
    return beam
