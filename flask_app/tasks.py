from __future__ import absolute_import
import os
import smtplib
import subprocess
import psutil
from email.mime.text import MIMEText
from datetime import timedelta, datetime
from collections import defaultdict
from io import StringIO
import functools
import sys
import logging
import logging.handlers
import logbook
from celery import Celery
from paramiko import SSHClient
from paramiko.client import AutoAddPolicy
from paramiko.rsakey import RSAKey
from jinja2 import Template
import paramiko
from .app import create_app
from .models import Beam, db, Pin, File
from celery.schedules import crontab
from celery.signals import worker_init
from raven.contrib.celery import register_signal
from sqlalchemy.orm import joinedload


from celery.signals import after_setup_logger, after_setup_task_logger
from celery.log import redirect_stdouts_to_logger

logger = logbook.Logger(__name__)


queue = Celery('tasks', broker='redis://localhost')
queue.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
    CELERY_RESULT_SERIALIZER='json',
    CELERY_ENABLE_UTC=True,
    CELERYBEAT_SCHEDULE={
        'vacuum': {
            'task': 'flask_app.tasks.vacuum',
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
def setup_log(**args):
    logbook.SyslogHandler().push_application()
    logbook.StreamHandler(sys.stderr, bubble=True).push_application()
    redirect_stdouts_to_logger(args['logger']) # logs to local syslog
    if os.path.exists('/dev/log'):
        h = logging.handlers.SysLogHandler('/dev/log')
    else:
        h = logging.handlers.SysLogHandler()
    h.setLevel(args['loglevel'])
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    h.setFormatter(formatter)
    args['logger'].addHandler(h)

APP = None

def needs_app_context(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        global APP

        if APP is None:
            APP = create_app()

        with APP.app_context():
            return f(*args, **kwargs)

    return wrapper


def create_key(s):
    f = StringIO()
    f.write(s)
    f.seek(0)
    return RSAKey.from_private_key(file_obj=f, password=None)


with open(os.path.join(os.path.dirname(__file__), "..", "static", "assets", "combadge.py"), "r") as combadge:
    _COMBADGE = combadge.read()


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

@queue.task
@needs_app_context
def beam_up(beam_id, host, directory, username, auth_method, pkey, password):
    try:
        beam = db.session.query(Beam).filter_by(id=beam_id).one()
        delay = datetime.utcnow() - beam.start
        if delay.total_seconds() > 10:
            APP.raven.captureMessage("Beam {} took {} to start".format(beam.id, delay))

        transporter = APP.config.get('TRANSPORTER_HOST', 'scotty')
        logger.info('Beaming up {}@{}:{} ({}) to transporter {}. Auth method: {}'.format(
            username, host, directory, beam_id, transporter, auth_method))
        ssh_client = SSHClient()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())

        kwargs = {'username': username, 'look_for_keys': False}
        if auth_method == 'rsa':
            kwargs['pkey'] = create_key(pkey)
        elif auth_method == 'password':
            kwargs['password'] = password
        else:
            raise Exception('Invalid auth method')

        ssh_client.connect(host, **kwargs)
        logger.info('{}: Connected to {}. Uploading combadge'.format(beam_id, host))

        stdin, stdout, stderr = ssh_client.exec_command("sh -c \"cat > /tmp/combadge.py && chmod +x /tmp/combadge.py\"")
        stdin.write(_COMBADGE)
        stdin.channel.shutdown_write()
        retcode = stdout.channel.recv_exit_status()
        if retcode != 0:
            raise Exception(stderr.read().decode("utf-8"))

        logger.info('{}: Running combadge'.format(beam_id))
        _, stdout, stderr = ssh_client.exec_command(
            '/tmp/combadge.py {} "{}" "{}"'.format(str(beam_id), directory, transporter))
        retcode = stdout.channel.recv_exit_status()
        if retcode != 0:
            raise Exception(stderr.read().decode("utf-8"))

        logger.info('{}: Detached from combadge'.format(beam_id))
    except Exception as e:
        beam.error = str(e)
        beam.completed = True
        db.session.commit()

        if not isinstance(e, paramiko.ssh_exception.AuthenticationException):
            raise


def vacuum_beam(beam, storage_path):
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
def mark_timeout():
    timeout = timedelta(seconds=APP.config['COMBADGE_CONTACT_TIMEOUT'])
    timed_out = datetime.utcnow() - timeout
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
def remind_pinned():
    if APP.config.get('PIN_REMIND_THRESHOLD') is None:
        logger.info("Sending email reminders is disabled for this instance")
        return

    for value in _THRESHOLD_VALUES:
        if value not in APP.config:
            logger.error("{} must be specified in the configuration together with PIN_REMIND_THRESHOLD".format(
                value))
            return

    remind_time = datetime.utcnow() - timedelta(days=APP.config['PIN_REMIND_THRESHOLD'])
    emails = defaultdict(list)
    pins = (db.session.query(Pin)
            .join(Pin.beam)
            .options(joinedload(Pin.user), joinedload(Pin.beam))
            .filter(Beam.start <= remind_time))
    for pin in pins:
        emails[pin.user.email].append(pin.beam_id)

    template = Template(_REMINDER)
    s = smtplib.SMTP(APP.config['SMTP'])
    for email, beams in emails.items():
        body = template.render(beams=beams, base_url=APP.config['BASE_URL'])
        msg = MIMEText(body, 'html')
        msg['Subject'] = 'Pinned beams reminder'
        msg['From'] = 'Scotty <scotty@infinidat.com>'
        msg['To'] = email

        s.send_message(msg)

    s.quit()


@queue.task
@needs_app_context
def vacuum():
    logger.info("Vacuum intiated")

    # Make sure that the storage folder is accessable. Whenever deploying scotty to somewhere, one
    # must create this empty file in the storage directory
    os.stat(os.path.join(APP.config['STORAGE_PATH'], ".test"))

    db.engine.execute(
        "UPDATE beam SET pending_deletion=true "
        "WHERE "
        "(NOT beam.pending_deletion AND NOT beam.deleted AND beam.completed)" # Anything which isn't uncompleted or already deleted
        "AND NOT EXISTS (SELECT beam_id FROM pin WHERE pin.beam_id = beam.id) " # which has no pinners
        "AND (NOT EXISTS (SELECT beam_id FROM file WHERE file.beam_id = beam.id)) " # And has no files
        )
    db.engine.execute(
        "UPDATE beam SET pending_deletion=true "
        "WHERE "
        "(NOT beam.pending_deletion AND NOT beam.deleted AND beam.completed)" # Anything which isn't uncompleted or already deleted
        "AND NOT EXISTS (SELECT beam_id FROM pin WHERE pin.beam_id = beam.id) " # which has no pinners
        "AND ((beam.type_id IS NULL) AND (beam.start < now() - '%s days'::interval)) "
            # Belongs to the default type and the default vacuum threshold has been exceeded
        , APP.config['VACUUM_THRESHOLD'])
    db.engine.execute(
        "UPDATE beam SET pending_deletion=true "
        "FROM beam_type "
        "WHERE "
        "(NOT beam.pending_deletion AND NOT beam.deleted AND beam.completed)" # Anything which isn't uncompleted or already deleted
        "AND NOT EXISTS (SELECT beam_id FROM pin WHERE pin.beam_id = beam.id) " # which has no pinners
        "AND ((beam.type_id = beam_type.id) AND (beam.start < now() - (beam_type.vacuum_threshold * INTERVAL '1 DAY')))"
            # Belongs to a specific type which its vacuum threshold has been exceeded
        )
    db.session.commit()
    logger.info("Finished marking vacuum candidates")

    to_delete = db.session.query(Beam).filter(Beam.pending_deletion == True, Beam.deleted == False)
    for beam in to_delete:
        vacuum_beam(beam, APP.config['STORAGE_PATH'])
    logger.info("Vacuum done")

    validate_checksum.delay()


@queue.task
@needs_app_context
def vacuum_check():
    storage_path = APP.config['STORAGE_PATH']
    deleted_beams = db.session.query(Beam).filter(Beam.deleted == True)
    for beam in deleted_beams:
        for file_ in beam.files:
            full_path = os.path.join(storage_path, file_.storage_name)
            if not os.path.exists(full_path):
                continue

            logger.warning("{} still exists".format(full_path))
            os.unlink(full_path)


def _checksum(path):
    return subprocess.check_output([APP.config['SHA512SUM'], path]).decode("utf-8").split(" ")[0]


@queue.task
@needs_app_context
def validate_checksum():
    storage_path = APP.config['STORAGE_PATH']

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
        file_.last_validated = datetime.utcnow()

    db.session.commit()


@queue.task
@needs_app_context
def scrub():
    logger.info("Scrubbing intiated")
    errors = []

    storage_path = APP.config['STORAGE_PATH']

    active_beams = (db.session.query(Beam)
                    .filter(Beam.pending_deletion == False, Beam.deleted == False)
                    .options(joinedload(Beam.files)))
    expected_files = set()
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
def check_free_space():
    if 'FREE_SPACE_THRESHOLD' not in APP.config:
        logger.info("Free space checking is disabled as FREE_SPACE_THRESHOLD is not defined")
        return

    percent = psutil.disk_usage(APP.config['STORAGE_PATH']).percent
    if percent >= APP.config['FREE_SPACE_THRESHOLD']:
        APP.raven.captureMessage("Used space is {}%".format(percent))


@worker_init.connect
def on_init(**_):
    app = create_app()
    register_signal(app.raven.client)


after_setup_logger.connect(setup_log)
after_setup_task_logger.connect(setup_log)
