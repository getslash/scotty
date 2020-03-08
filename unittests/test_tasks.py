import datetime
import io
import pathlib
from unittest import mock
from uuid import UUID

import munch
import pytest

from flask_app import tasks, paths
from flask_app.models import Beam, Pin, BeamType
from flask_app.tasks import vacuum, beam_up


def is_vacuumed(db_session, beam):
    beam = db_session.query(Beam).filter_by(id=beam.id).one_or_none()
    if beam is None:
        raise RuntimeError(f"Beam {beam.id} not found")
    return beam.deleted


def test_completed_beam_past_date_should_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date):
    beam = create_beam(start=expired_beam_date, completed=True)
    vacuum.delay()
    assert is_vacuumed(db_session, beam)


def test_beam_before_date_should_not_be_vacuumed(eager_celery, db_session, create_beam, now):
    beam = create_beam(start=now, completed=True)
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_not_completed_beam_should_not_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date):
    beam = create_beam(start=expired_beam_date, completed=False)
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_beam_with_open_issues_should_not_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date, issue):
    beam = create_beam(start=expired_beam_date, completed=True)
    beam.issues.append(issue)
    db_session.commit()
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_pinned_beam_should_not_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date, user):
    beam = create_beam(start=expired_beam_date, completed=True)
    pin = Pin(user_id=user.id, beam_id=beam.id)
    db_session.add(pin)
    db_session.commit()
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_beam_without_file_should_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date):
    beam = create_beam(start=expired_beam_date, completed=True, add_file=False)
    db_session.commit()
    vacuum.delay()
    assert is_vacuumed(db_session, beam)


def test_beam_with_beam_type_greater_threshold_is_not_vacuumed(eager_celery, db_session, create_beam, expired_beam_date, vacuum_threshold):
    # threshold       default threshold                 now
    #   |    10 days        |            60 days         |
    # -----------------------------------------------------> date
    #         |
    #        beam
    #
    # beam is before the default threshold (60 days) so it should usually be vacuumed
    # but here we increase the threshold by 10 more days (vacuum_threshold=vacuum_threshold + 10)
    # and therefore the beam is *within* the threshold and will *not* be vacuumed
    beam = create_beam(start=expired_beam_date, completed=True)
    beam_type = BeamType(name="beam_type_1", vacuum_threshold=vacuum_threshold + 10)
    db_session.add(beam_type)
    beam.type = beam_type
    db_session.commit()
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_beam_with_beam_type_smaller_threshold_is_vacuumed(eager_celery, db_session, create_beam, now):
    # default threshold                threshold      now
    # |  59 days                        |   1 day      |
    # --------------------------------------------------> date
    #                           |
    #                         beam
    #
    # beam is within the default threshold (60 days) so it should usually *not* be vacuumed
    # but here we make the threshold 1 day (vacuum_threshold=1)
    # and therefore the beam is outside the threshold and *should* be vacuumed
    vacuum_threshold = 1
    beam = create_beam(start=now - datetime.timedelta(days=2), completed=True)
    beam_type = BeamType(name="beam_type_1", vacuum_threshold=vacuum_threshold)
    db_session.add(beam_type)
    beam.type = beam_type
    db_session.commit()
    vacuum.delay()
    assert is_vacuumed(db_session, beam)


class MockSSHClient:
    instances = []

    def __init__(self):
        self.instances.append(self)
        self.policy = None
        self.connect_args = None
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
        self.recv_exit_status = 0
        self.stdout.channel = munch.Munch(recv_exit_status=lambda: self.recv_exit_status)
        self.stderr = io.BytesIO()
        self.commands = []
        self.os_type = None

    def exec_command(self, command):
        self.commands.append(command)
        self.recv_exit_status = 0
        self.stdout.truncate(0)
        self.stdout.seek(0)
        if command == "uname":
            if self.os_type == "linux":
                self.stdout.write(b"linux")
            else:
                self.stderr.write((
                    b"uname : The term 'uname' is not recognized as the name of a cmdlet, function, script file, "
                    b"or operable program. Check the spelling of the name, or if a path was included, "
                    b"verify that the path is correct and try again."
                ))
                self.recv_exit_status = 1
        elif command == "python -c 'import tempfile; print(tempfile.gettempdir())'":
            if self.os_type == "linux":
                self.stdout.write(b"/tmp")
            else:
                user = self.connect_args['username']
                self.stdout.write(b"C:\\Users\\" + user.encode() + b"\\AppData\\Local\\Temp")
        self.stdout.seek(0)
        self.stdin.seek(0)
        self.stderr.seek(0)
        return self.stdin, self.stdout, self.stderr

    def connect(self, host, **kwargs):
        self.connect_args = dict(host=host, **kwargs)
        if host == "mock-host":
            self.os_type = "linux"
        else:
            self.os_type = "windows"

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def get_transport(self):
        return "mock-transport"

    @classmethod
    def clear(cls):
        cls.instances = []


@pytest.fixture
def mock_ssh_client(monkeypatch):
    monkeypatch.setattr(tasks, "SSHClient", MockSSHClient)
    MockSSHClient.clear()
    yield MockSSHClient
    MockSSHClient.clear()


@pytest.fixture
def mock_sftp_client(monkeypatch):
    SFTPClient = mock.MagicMock()
    monkeypatch.setattr(tasks, "SFTPClient", SFTPClient)
    return SFTPClient


@pytest.fixture
def mock_rsa_key(monkeypatch):
    RSAKey = mock.MagicMock()
    monkeypatch.setattr(tasks, "RSAKey", RSAKey)
    return RSAKey


@pytest.fixture
def uuid4(monkeypatch):
    uuid = UUID('f1e8962b-00c9-4799-aacf-5d616163e03d')
    monkeypatch.setattr(tasks, "uuid4", lambda: uuid)
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


@pytest.mark.parametrize("os_type", ["linux", "windows"])
def test_beam_up(db_session, now, create_beam, eager_celery, monkeypatch, mock_ssh_client, mock_sftp_client, mock_rsa_key, uuid4, os_type, combadge_assets_dir):
    beam = create_beam(start=now, completed=False)
    if os_type == "windows":
        beam.host = "mock-windows-host"
        db_session.commit()
    result = beam_up.delay(
        beam_id=beam.id,
        host=beam.host,
        directory=beam.directory,
        username='root',
        auth_method='stored_key',
        pkey='mock-pkey',
        password=None,
        combadge_version='v2'
    )
    assert result.successful(), result.traceback
    beam = db_session.query(Beam).filter_by(id=beam.id).one()
    assert beam.error is None
    assert len(mock_ssh_client.instances) == 1
    if os_type == "linux":
        combadge = f"/tmp/combadge_{uuid4.hex[:10]}"
    else:
        combadge = f"C:\\Users\\root\\AppData\\Local\\Temp\\combadge_{uuid4.hex[:10]}.exe"
    assert mock_ssh_client.instances[0].commands == [
        "uname",
        "python -c 'import tempfile; print(tempfile.gettempdir())'",
        f"{combadge} -b {beam.id} -p {beam.directory} -t scotty",
    ]

