import os

import flask_login
import pytest
from flux import current_timeline

from flask_app.blueprints.auth import get_or_create_user
from flask_app.models import Beam
from flask_app.tasks import beam_up, queue
from flask_app.utils.remote_combadge import RemoteCombadge
from flask_app.utils.remote_host import RemoteHost

OS_TYPES = ['linux', 'windows']
HOST_NAME_BY_OS_TYPE = {
    'windows': os.environ.get("WINDOWS_HOST"),
    'linux': os.environ.get("LINUX_HOST"),
}
COMBADGE_VERSIONS = ['v1', 'v2']
UNSUPPORTED_OS_TYPES_PER_COMBADGE_VERSION = {
    'v1': ['windows'],
    'v2': [],
}


def pytest_generate_tests(metafunc):
    if "os_type" in metafunc.fixturenames and "combadge_version" in metafunc.fixturenames:
        metafunc.parametrize("os_type,combadge_version", [
            (os_type, combadge_version)
            for os_type in OS_TYPES
            for combadge_version in COMBADGE_VERSIONS
            if os_type not in UNSUPPORTED_OS_TYPES_PER_COMBADGE_VERSION[combadge_version]
        ])


@pytest.fixture
def webapp_context(webapp, monkeypatch):
    app_context = webapp.app_context()
    monkeypatch.setattr(webapp, "app_context", lambda: app_context)
    with app_context:
        yield


@pytest.fixture
def eager_celery():
    queue.conf.update(CELERY_ALWAYS_EAGER=True)
    yield
    queue.conf.update(CELERY_ALWAYS_EAGER=False)


@pytest.fixture
def client(monkeypatch, get_user, app_context):
    app_context.config["TESTING"] = True
    app_context.config["DEBUG"] = True
    app_context.secret_key = "test_secret_key"
    monkeypatch.setattr(flask_login.utils, "_get_user", get_user)
    app_context.login_manager._login_disabled = True
    with app_context.test_client() as client:
        yield client


def get_remote_host(os_type):
    pkey = get_pkey()
    host = HOST_NAME_BY_OS_TYPE[os_type]
    return RemoteHost(host=host, username='root', auth_method='stored_key', pkey=pkey)


def get_pkey():
    with open(os.path.expanduser('~/.ssh/infradev-id_rsa'), 'r') as f:
        return f.read()


@pytest.mark.parametrize("os_type", OS_TYPES)
def test_get_os_type(os_type):
    with get_remote_host(os_type) as remote_host:
        assert remote_host.get_os_type() == os_type


def standardize_hostname(hostname):
    return hostname.strip().split('.', 1)[0]


@pytest.mark.parametrize("os_type", OS_TYPES)
def test_exec_ssh_command(os_type):
    with get_remote_host(os_type) as remote_host:
        assert standardize_hostname(remote_host.exec_ssh_command("hostname")) == standardize_hostname(remote_host._host)


def test_remote_combadge(os_type, combadge_version):
    with get_remote_host(os_type) as remote_host:
        with RemoteCombadge(remote_host=remote_host, combadge_version=combadge_version) as remote_combadge:
            assert remote_combadge.ping()


def test_beam_up(combadge_version, os_type, eager_celery, webapp_context, db, tmpdir):
    user = get_or_create_user(email="damram@infinidat.com", name="damram")
    directory = str(tmpdir)
    pkey = get_pkey()
    host_name = HOST_NAME_BY_OS_TYPE[os_type]

    beam = Beam(
        start=current_timeline.datetime.utcnow(),
        size=0,
        host=host_name,
        comment='',
        directory=directory,
        initiator=user.id,
        error=None,
        combadge_contacted=False,
        pending_deletion=False,
        completed=False,
        deleted=False)

    db.session.add(beam)
    db.session.commit()

    beam_up.delay(
        beam_id=beam.id,
        host=beam.host,
        directory=beam.directory,
        username='root',
        auth_method='stored_key',
        pkey=pkey,
        password=None,
        combadge_version=combadge_version)

    res_beam = db.session.query(Beam).filter_by(id=beam.id).one()
    assert res_beam.error is None
