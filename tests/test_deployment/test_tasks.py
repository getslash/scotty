from flask_app.tasks import queue, _get_os_type, _get_connected_ssh_client, _remove_combadge, _upload_combadge, get_remote_combadge_path, _get_combadge_command, beam_up
from flask_app.blueprints.beams import create as create_beam
from flask_app.models import Beam, User, db
from paramiko import SSHClient, SFTPClient
from scottypy import Scotty
from flux import current_timeline
from flask_app.blueprints.auth import get_or_create_user
from flask_sqlalchemy import SQLAlchemy
import flask_migrate



from pathlib import PureWindowsPath
from uuid import uuid4


import os
import pytest

OS_TYPES = ['linux', 'windows']


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


@pytest.fixture()
def get_ssh_client(get_host_name_by_os_type):
    def _get_ssh_client(os_type):
        pkey = get_pkey()
        host = get_host_name_by_os_type(os_type)
        ssh_client = _get_connected_ssh_client(host=host, username='root', auth_method='stored_key', pkey=pkey)
        return ssh_client
    return _get_ssh_client


@pytest.fixture()
def get_sftp_client(get_ssh_client):
    def _get_sftp_client(os_type):
        ssh_client = get_ssh_client(os_type)
        return SFTPClient.from_transport(ssh_client.get_transport())
    return _get_sftp_client


@pytest.fixture()
def get_host_name_by_os_type():
    def _get_host_name_by_os_type(os_type):
        return {
            'windows': 'gdc-qa-io-350.lab.gdc.il.infinidat.com',
            'linux': 'gdc-qa-io-017.lab.gdc.il.infinidat.com'
            }[os_type]
    return _get_host_name_by_os_type


@pytest.fixture(scope="module")
def remote_combadge_name():
    random_string = str(uuid4())[:10]
    return f"combadge_{random_string}"


@pytest.fixture(scope="module")
def get_remote_combadge_path(remote_combadge_name):
    def _get_remote_combadge_path(os_type):
        if os_type == 'windows':
            remote_path = str(PureWindowsPath(os.path.join('C:', 'Users', 'root', 'AppData', 'Local', 'Temp', remote_combadge_name)))
        elif os_type in ['linux', 'darwin']:
            remote_path = str(os.path.join('/tmp', remote_combadge_name))
        return remote_path
    return _get_remote_combadge_path


@pytest.fixture(scope="module")
def get_local_combadge_path():
    def _get_local_combadge_path(os_type):
        [local_dir, local_name] = {
            'windows': ['combadge_windows', 'combadge.exe'],
            'linux': ['combadge_linux', 'combadge'],
            'darwin': ['combadge_darwin', 'combadge'],
        }[os_type]
        local_path = os.path.realpath(os.path.join('combadge_assets', local_dir, local_name))
        return local_path
    return _get_local_combadge_path


@pytest.fixture()
def get_remote_file_to_beam(get_host_name_by_os_type):
    def _get_remote_file_to_beam(os_type):
        host_name = get_host_name_by_os_type(os_type)
        file_path = {
            'windows': str(PureWindowsPath(os.path.join('C:', 'Users', 'root', 'AppData', 'Local', 'Temp', 'scotty_test.txt'))),
            'linux': 'AutoInstall',
        }[os_type]
        return [host_name, file_path]
    return _get_remote_file_to_beam

def get_pkey():
    with open(os.path.expanduser('~/.ssh/infradev-id_rsa'), 'r') as f:
        return f.read()


@pytest.mark.parametrize("os_type", OS_TYPES)
def test_get_os_type(os_type, get_ssh_client):
    assert os_type == _get_os_type(get_ssh_client(os_type))


@pytest.mark.parametrize("os_type", OS_TYPES)
def test_get_connected_ssh_client(os_type, get_ssh_client, get_host_name_by_os_type):
    ssh_client = get_ssh_client(os_type)
    _, stdout, stderr = ssh_client.exec_command("hostname")
    host_name = get_host_name_by_os_type(os_type)
    assert stdout.read().decode().strip() == host_name


@pytest.mark.parametrize("os_type", OS_TYPES)
def test_upload_new_combadge(os_type, get_ssh_client):
    ssh_client = get_ssh_client(os_type)
    remote_combadge_path = _upload_combadge(ssh_client=ssh_client, combadge_version='v2')
    remote_combadge_dir = os.path.dirname(remote_combadge_path)
    _, stdout, stderr = ssh_client.exec_command(f"{remote_combadge_path} --help")
    assert stdout.channel.recv_exit_status() == 0


def test_upload_old_combadge(get_ssh_client):
    ssh_client = get_ssh_client('linux')
    remote_combadge_path = _upload_combadge(ssh_client=ssh_client, combadge_version='v1')
    remote_combadge_dir = os.path.dirname(remote_combadge_path)
    remote_combadge_name = remote_combadge_path.replace('/tmp/', '')
    _, stdout, stderr = ssh_client.exec_command(f"ls {remote_combadge_dir}")
    combadge_dir_content = stdout.read().decode("utf-8").strip().lower()
    assert remote_combadge_name in combadge_dir_content


@pytest.mark.parametrize("os_type", OS_TYPES)
def test_put_combadge_on_remote_host(os_type, get_sftp_client, get_remote_combadge_path, get_local_combadge_path):
    remote_combadge_path = get_remote_combadge_path(os_type)
    local_combadge_path = get_local_combadge_path(os_type)
    with get_sftp_client(os_type) as sftp_client:
        sftp_client.put(local_combadge_path, remote_combadge_path)
        sftp_client.stat(remote_combadge_path)
        sftp_client.remove(remote_combadge_path)
        with pytest.raises(FileNotFoundError):
            sftp_client.stat(remote_combadge_path)


@pytest.mark.parametrize("combadge_version,os_type", [("v1", "linux"), ("v2", "linux"), ("v2", "windows")])
def test_beam_up(combadge_version, get_host_name_by_os_type, os_type, get_remote_file_to_beam, eager_celery, webapp_context, db):
    user = get_or_create_user(email="damram@infinidat.com", name="damram")
    directory = get_remote_file_to_beam(os_type)[1]
    pkey = get_pkey()
    host_name = get_host_name_by_os_type(os_type)

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
