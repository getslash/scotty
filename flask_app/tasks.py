from __future__ import absolute_import

import contextlib
import functools
import os
import smtplib
import stat
import subprocess
import sys
from collections import defaultdict
from datetime import timedelta
from email.mime.text import MIMEText
from io import StringIO
from pathlib import PureWindowsPath
from typing import Any, Optional
from uuid import uuid4

import flux
import logbook
import paramiko
import psutil
from celery import Celery
from celery.schedules import crontab
from celery.signals import after_setup_logger, after_setup_task_logger
from celery.signals import worker_init
from flask import current_app
from jinja2 import Template
from paramiko import SSHClient, SFTPClient
from paramiko.client import AutoAddPolicy
from paramiko.rsakey import RSAKey
from raven.contrib.celery import register_signal
from sqlalchemy import func, extract, case, or_
from sqlalchemy.orm import joinedload

from . import issue_trackers
from .app import create_app, needs_app_context
from .models import Beam, db, Pin, File, Tracker, Issue, beam_issues, BeamType
from .paths import get_combadge_path

logger = logbook.Logger(__name__)
_COMBADGE_UUID_PART_LENGTH = 10

queue = Celery('tasks', broker=os.environ.get('SCOTTY_CELERY_BROKER_URL', 'amqp://guest:guest@localhost'))
queue.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
    CELERY_RESULT_SERIALIZER='json',
    CELERY_ENABLE_UTC=True,
    CELERYBEAT_SCHEDULE={
        'nightly': {
            'task': 'flask_app.tasks.nightly',
            'schedule': crontab(hour=0, minute=0),
        },
        'free-space': {
            'task': 'flask_app.tasks.check_free_space',
            'schedule': crontab(hour=10, minute=0),
        },
        'remind': {
            'task': 'flask_app.tasks.remind_pinned',
            'schedule': crontab(hour=13, minute=0, day_of_week='sunday'),
        },
        'mark-timeout': {
            'task': 'flask_app.tasks.mark_timeout',
            'schedule': timedelta(minutes=15),
        },
    },
    CELERY_TIMEZONE='UTC'
)
def setup_log(**args: Any) -> None:
    logbook.StreamHandler(sys.stdout, bubble=True).push_application()


def testing_method(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        assert current_app is not None
        assert current_app.config.get('DEBUG', False)
        return f(*args, **kwargs)

    return wrapper


def create_key(s: str) -> str:
    f = StringIO()
    f.write(s)
    f.seek(0)
    return RSAKey.from_private_key(file_obj=f, password=None)



_REMINDER = """Hello Captain,<br/><br/>
This is a reminder that the following beams are pinned by you:
<ul>
{% for beam in beams %}
<li><a href="{{base_url}}/#/beam/{{beam}}">{{beam}}</a></li>
{% endfor %}
</ul>
<br/>
If you still need these beams then please ignore this message. However, if these beams are not required anymore, please un-pin them to allow them to be garbage collected.<br/>
<br/>
Sincerely yours,<br/>
Montgomery Scott
"""


class RemoteHost:
    _TEMPDIR_COMMAND = "python -c 'import tempfile; print(tempfile.gettempdir())'"

    def __init__(self, *, host, username, auth_method, pkey=None, password=None):
        self.host = host
        self._username = username
        self._auth_method = auth_method
        self._pkey = pkey
        self._password = password
        self._ssh_client = None

    @functools.lru_cache(maxsize=None)
    def get_os_type(self) -> str:
        uname = self.exec_ssh_command("uname", raise_on_failure=False)
        if uname is None:
            return 'windows'
        return uname.lower()

    def get_temp_dir(self) -> str:
        return self.exec_ssh_command(self._TEMPDIR_COMMAND)

    def exec_ssh_command(self, command, raise_on_failure=True):
        _, stdout, stderr = self.raw_exec_ssh_command(command)
        retcode = stdout.channel.recv_exit_status()
        if retcode == 0:
            return stdout.read().decode().strip()
        if raise_on_failure:
            raise Exception(f"Failed to execute command {command}: {stderr.read().decode('utf-8')}")

    def raw_exec_ssh_command(self, command):
        logger.info(f"executing on host {self.host} command {command}")
        return self._ssh_client.exec_command(command)

    def get_sftp_client(self):
        return SFTPClient.from_transport(self._ssh_client.get_transport())

    def close(self):
        if self._ssh_client is not None:
            self._ssh_client.close()

    def __enter__(self):
        self._ssh_client = ssh_client = SSHClient()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())

        kwargs = {'username': self._username, 'look_for_keys': False}
        if self._auth_method in ('rsa', 'stored_key'):
            kwargs['pkey'] = create_key(self._pkey)
        elif self._auth_method == 'password':
            kwargs['password'] = self._password
        else:
            raise Exception('Invalid auth method')

        self._ssh_client.connect(self.host, **kwargs)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class RemoteCombadge:
    def __init__(self, *, remote_host: RemoteHost, combadge_version: str):
        self._combadge_version = combadge_version
        self._remote_host = remote_host
        self._remote_combadge_path = None

    def _generate_random_combadge_name(self, string_length: int) -> str:
        random_string = str(uuid4().hex)[:string_length]
        return f"combadge_{random_string}"

    def _get_remote_combadge_path(self):
        combadge_name = self._generate_random_combadge_name(string_length=_COMBADGE_UUID_PART_LENGTH)
        remote_combadge_dir = self._remote_host.get_temp_dir()
        if self._remote_host.get_os_type() == "windows":
            combadge_name = f'{combadge_name}.exe'
            remote_combadge_path = str(PureWindowsPath(os.path.join(remote_combadge_dir, combadge_name)))
        else:
            remote_combadge_path = os.path.join(remote_combadge_dir, combadge_name)
        logger.debug(f"combadge path: {remote_combadge_path}")
        return remote_combadge_path

    def _upload_combadge(self):
        os_type = self._remote_host.get_os_type()

        local_combadge_path = get_combadge_path(self._combadge_version, os_type=os_type)
        assert os.path.exists(local_combadge_path), f"Combadge at {local_combadge_path} does not exist"
        remote_combadge_path = self._get_remote_combadge_path()

        logger.info(f"uploading combadge {self._combadge_version} for {os_type} to {remote_combadge_path}")
        self._sftp = self._remote_host.get_sftp_client()
        self._sftp.put(local_combadge_path, remote_combadge_path)
        if os_type != 'windows':
            combadge_st = os.stat(local_combadge_path)
            self._sftp.chmod(remote_combadge_path, combadge_st.st_mode | stat.S_IEXEC)
        self._remote_combadge_path = remote_combadge_path

    def _remove_combadge(self):
        if self._remote_combadge_path is not None and self._sftp is not None:
            try:
                self._sftp.remove(self._remote_combadge_path)
            except FileNotFoundError:
                logger.warn(f"Combadge {self._remote_combadge_path} not found when trying to remove it")

    def __enter__(self):
        self._upload_combadge()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_combadge()
        if self._sftp is not None:
            self._sftp.close()

    def run(self, *, beam_id: int, directory: str, transporter: str):
        combadge_commands = {
            'v1': f'{self._remote_combadge_path} {beam_id} "{directory}" "{transporter}"',
            'v2': f'{self._remote_combadge_path} -b {beam_id} -p {directory} -t {transporter}'
        }
        combadge_command = combadge_commands[self._combadge_version]
        self._remote_host.exec_ssh_command(combadge_command)

    def ping(self):
        _, stdout, stderr = self._remote_host.raw_exec_ssh_command(self._remote_combadge_path)
        return 'usage' in (stdout.read().decode() + stderr.read().decode()).lower()


def _get_active_beams():
    active_beams = (db.session.query(Beam)
                    .filter(~Beam.pending_deletion,
                            ~Beam.deleted)
                    .options(joinedload(Beam.files)))
    return active_beams


@queue.task
@needs_app_context
def beam_up(beam_id: int, host: str, directory: str, username: str, auth_method: str, pkey: str, password: str, combadge_version: Optional[str] = None) -> None:

    beam = db.session.query(Beam).filter_by(id=beam_id).one()
    if combadge_version is None:
        combadge_version = 'v2'
    try:
        delay = flux.current_timeline.datetime.utcnow() - beam.start
        if delay.total_seconds() > 10:
            current_app.raven.captureMessage(
                "Beam took too long to start", extra={'beam_id': beam.id, 'delay': str(delay)}, level="info")

        transporter = current_app.config.get('TRANSPORTER_HOST', 'scotty')
        logger.info(f'Beaming up {username}@{host}:{directory} ({beam_id}) to transporter {transporter}. Auth method: {auth_method}')
        logger.info(f'{beam_id}: Connected to {host}. Uploading combadge version: {combadge_version}')

        with RemoteHost(host=host, username=username, auth_method=auth_method, pkey=pkey, password=password) as remote_host:
            with RemoteCombadge(remote_host=remote_host, combadge_version=combadge_version) as remote_combadge:
                remote_combadge.run(beam_id=beam_id, directory=directory, transporter=transporter)

        logger.info(f'{beam_id}: Detached from combadge')
    except Exception as e:
        logger.exception("Failed to beam up")
        beam.error = str(e)
        beam.completed = True
        db.session.commit()

        if not isinstance(e, paramiko.ssh_exception.AuthenticationException):
            raise


def vacuum_beam(beam: Beam, storage_path: str) -> None:
    logger.info("Vacuuming {}".format(beam.id))
    for f in beam.files:
        if not f.storage_name:
            continue

        path = os.path.join(storage_path, f.storage_name)
        if os.path.exists(path):
            logger.info("Deleting {}".format(path))
            os.unlink(path)

    logger.info("Vacuumed {} successfully".format(beam.id))
    beam.deleted = True
    db.session.commit()


@queue.task
@needs_app_context
def mark_timeout() -> None:
    timeout = timedelta(seconds=current_app.config['COMBADGE_CONTACT_TIMEOUT'])
    timed_out = flux.current_timeline.datetime.utcnow() - timeout
    dead_beams = (
        db.session.query(Beam).filter_by(completed=False)
        .filter(Beam.combadge_contacted == False, Beam.start < timed_out))
    for beam in dead_beams:
        logger.info("Combadge of {} did not contact for more than {}".format(beam.id, timeout))
        beam.completed = True
        beam.error = "Combadge didn't contact the transporter"

    db.session.commit()


_THRESHOLD_VALUES = ['SMTP', 'SMTP_FROM', 'BASE_URL']
@queue.task
@needs_app_context
def remind_pinned() -> None:
    if current_app.config.get('PIN_REMIND_THRESHOLD') is None:
        logger.info("Sending email reminders is disabled for this instance")
        return

    for value in _THRESHOLD_VALUES:
        if value not in current_app.config:
            logger.error("{} must be specified in the configuration together with PIN_REMIND_THRESHOLD".format(
                value))
            return

    remind_time = flux.current_timeline.datetime.utcnow() - timedelta(days=current_app.config['PIN_REMIND_THRESHOLD'])
    emails: defaultdict = defaultdict(list)
    pins = (db.session.query(Pin)
            .join(Pin.beam_id)
            .options(joinedload(Pin.user_id), joinedload(Pin.beam_id))
            .filter(Beam.start <= remind_time))
    for pin in pins:
        emails[pin.user.email].append(pin.beam_id)

    template = Template(_REMINDER)
    s = smtplib.SMTP(current_app.config['SMTP'])
    for email, beams in emails.items():
        body = template.render(beams=beams, base_url=current_app.config['BASE_URL'])
        msg = MIMEText(body, 'html')
        msg['Subject'] = 'Pinned beams reminder'
        msg['From'] = current_app.config['SMTP_FROM']
        msg['To'] = email

        s.send_message(msg)

    s.quit()


@needs_app_context
def get_pending_query():
    now = flux.current_timeline.datetime.utcnow()
    days_factor = 60 * 60 * 24
    beam_age_in_days = func.trunc(extract('epoch', now) - extract('epoch', Beam.start)) / days_factor
    vacuum_threshold = case([(Beam.type_id == None, current_app.config['VACUUM_THRESHOLD']),], else_ = BeamType.vacuum_threshold)

    existing_open_issues = (db.session.query(beam_issues.c.beam_id)
                                     .join(Issue, Issue.id == beam_issues.c.issue_id)
                                     .filter(beam_issues.c.beam_id == Beam.id,
                                             Issue.open)
                                     .exists())

    pending_query = (db.session.query(Beam.id)
                              .outerjoin(Pin, Pin.beam_id == Beam.id)
                              .outerjoin(BeamType, BeamType.id == Beam.type_id)
                              .outerjoin(File, File.beam_id == Beam.id)
                              .filter(~Beam.pending_deletion,
                                      ~Beam.deleted,
                                      Beam.completed,
                                      Pin.id == None,
                                      ~existing_open_issues,
                                      or_(
                                          File.beam_id == None,
                                          beam_age_in_days >= vacuum_threshold
                                      )))
    return pending_query



@queue.task
@needs_app_context
def vacuum() -> None:
    logger.info("Vacuum intiated")

    # Make sure that the storage folder is accessable. Whenever deploying scotty to somewhere, one
    # must create this empty file in the storage directory
    os.stat(os.path.join(current_app.config['STORAGE_PATH'], ".test"))
    pending_query = get_pending_query()
    db.session.query(Beam).filter(Beam.id.in_(pending_query)).update(dict(pending_deletion=True), synchronize_session='fetch')
    db.session.commit()
    logger.info("Finished marking vacuum candidates")

    to_delete = db.session.query(Beam).filter(Beam.pending_deletion == True, Beam.deleted == False)
    for beam in to_delete:
        vacuum_beam(beam, current_app.config['STORAGE_PATH'])
    logger.info("Vacuum done")


@queue.task
@needs_app_context
def refresh_issue_trackers() -> None:
    trackers = db.session.query(Tracker)
    active_beams_ids = db.session.query(Beam.id).filter(~Beam.pending_deletion, ~Beam.deleted)
    issues_of_active_beams = db.session.query(beam_issues.c.issue_id).filter(beam_issues.c.beam_id.in_(active_beams_ids)).distinct()
    for tracker in trackers:
        logger.info("Refreshing tracker {} - {} of type {}", tracker.id, tracker.url, tracker.type)
        try:
            issues = db.session.query(Issue).filter(Issue.id.in_(issues_of_active_beams)).filter_by(tracker_id=tracker.id)
            issue_trackers.refresh(tracker, issues)
        except Exception:
            current_app.raven.captureException()

        db.session.commit()


@queue.task
@needs_app_context
def nightly() -> None:
    try:
        refresh_issue_trackers()
    except Exception:
        current_app.raven.captureException()
    vacuum()
    validate_checksum()


@queue.task
@needs_app_context
def vacuum_check() -> None:
    storage_path = current_app.config['STORAGE_PATH']
    deleted_beams = db.session.query(Beam).filter(Beam.deleted == True)
    for beam in deleted_beams:
        for file_ in beam.files:
            full_path = os.path.join(storage_path, file_.storage_name)
            if not os.path.exists(full_path):
                continue

            logger.warning("{} still exists".format(full_path))
            os.unlink(full_path)


def _checksum(path: str) -> str:
    return subprocess.check_output([current_app.config['SHA512SUM'], path]).decode("utf-8").split(" ")[0]


@queue.task
@needs_app_context
def validate_checksum() -> None:
    storage_path = current_app.config['STORAGE_PATH']

    files = File.query.join(Beam).filter(
        Beam.pending_deletion == False, Beam.deleted == False,
        File.checksum.isnot(None), File.status == "uploaded").order_by(File.last_validated).limit(100)

    for file_ in files:
        assert not file_.beam.deleted
        assert not file_.beam.pending_deletion
        full_path = os.path.join(storage_path, file_.storage_name)
        checksum = _checksum(full_path)
        assert checksum == file_.checksum, "Expected checksum of {} is {}. Got {} instead".format(
            full_path, file_.checksum, checksum)
        logger.info("{} validated (last validated: {})".format(full_path, file_.last_validated))
        file_.last_validated = flux.current_timeline.datetime.utcnow()

    db.session.commit()


@queue.task
@needs_app_context
def scrub() -> None:
    logger.info("Scrubbing intiated")
    errors = []

    storage_path = current_app.config['STORAGE_PATH']

    expected_files = set()
    active_beams = _get_active_beams()
    for beam in active_beams:
        for beam_file in beam.files:
            if not beam_file.storage_name and not beam_file.size:
                errors.append("{} has no storage name and a size greated than 0".format(
                    beam_file.id
                ))
                beam_file.size = 0
                continue

            if not beam_file.storage_name:
                continue

            full_path = os.path.join(storage_path, beam_file.storage_name)
            expected_files.add(full_path)
            if not os.path.exists(full_path):
                errors.append("{} ({}) does not exist".format(full_path, beam_file.id))
                continue

            file_info = os.stat(full_path)
            if file_info.st_size != beam_file.size:
                errors.append("Size of {} ({}) is {} bytes on the disk but {} bytes in the database".format(
                    full_path, beam_file.id, file_info.st_size, beam_file.size
            ))
                beam_file.size = file_info.st_size

        sum_size = sum(f.size for f in beam.files if f.size is not None)
        if beam.size != sum_size:
            errors.append("Size of beam {} is {}, but the sum of its file sizes is {}".format(
                beam.id, beam.size, sum_size
            ))
            beam.size = sum_size

    for root, _, files in os.walk(storage_path):
        for file_ in files:
            full_path = os.path.join(root, file_)
            if full_path not in expected_files:
                errors.append('Unexpected files {}'.format(full_path))

    if errors:
        db.session.commit()
        raise Exception(errors)


@queue.task
@needs_app_context
def check_free_space() -> None:
    if 'FREE_SPACE_THRESHOLD' not in current_app.config:
        logger.info("Free space checking is disabled as FREE_SPACE_THRESHOLD is not defined")
        return

    percent = psutil.disk_usage(current_app.config['STORAGE_PATH']).percent
    if percent >= current_app.config['FREE_SPACE_THRESHOLD']:
        current_app.raven.captureMessage("Used space is {}%".format(percent))


@queue.task
@needs_app_context
@testing_method
def sleep(t: int) -> None:
    flux.current_timeline.set_time_factor(0)
    flux.current_timeline.sleep(t)
    nightly()


@worker_init.connect
def on_init(**_: Any) -> None:
    app = create_app()
    register_signal(app.raven.client)


after_setup_logger.connect(setup_log)
after_setup_task_logger.connect(setup_log)
