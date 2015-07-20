from __future__ import absolute_import
import os
from datetime import timedelta, datetime
from io import StringIO
from celery import Celery
from paramiko import SSHClient
from paramiko.client import AutoAddPolicy
from paramiko.rsakey import RSAKey
import paramiko
from .app import create_app
from .models import Beam, db
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from celery.signals import worker_init
from raven.contrib.celery import register_signal


logger = get_task_logger(__name__)

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
        'mark-timeout': {
            'task': 'flask_app.tasks.mark_timeout',
            'schedule': timedelta(minutes=15),
        },
    },
    CELERY_TIMEZONE='UTC'
)


def create_key(s):
    f = StringIO()
    f.write(s)
    f.seek(0)
    return RSAKey.from_private_key(file_obj=f, password=None)


with open(os.path.join(os.path.dirname(__file__), "..", "static", "assets", "combadge.py"), "r") as combadge:
    _COMBADGE = combadge.read()


@queue.task
def beam_up(beam_id, host, directory, username, auth_method, pkey, password):
    app = create_app()
    try:
        transporter = app.config.get('TRANSPORTER_HOST', 'scotty')
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

        stdin, stdout, stderr = ssh_client.exec_command("cat > /tmp/combadge.py && chmod +x /tmp/combadge.py")
        stdin.write(_COMBADGE)
        stdin.channel.shutdown_write()
        retcode = stdout.channel.recv_exit_status()
        if retcode != 0:
            raise Exception(stderr.read().decode("ascii"))

        logger.info('{}: Running combadge'.format(beam_id))
        _, stdout, stderr = ssh_client.exec_command(
            '/tmp/combadge.py {} "{}" "{}"'.format(str(beam_id), directory, transporter))
        retcode = stdout.channel.recv_exit_status()
        if retcode != 0:
            raise Exception(stderr.read().decode("ascii"))

        logger.info('{}: Detached from combadge'.format(beam_id))
    except Exception as e:
        with app.app_context():
            beam = db.session.query(Beam).filter_by(id=beam_id).first()
            beam.error = str(e)
            beam.completed = True
            db.session.commit()

        if type(e) is not paramiko.ssh_exception.AuthenticationException:
            raise


def vacuum_beam(beam, storage_path):
    logger.info("Vacuuming {}".format(beam.id))
    for f in beam.files:
        path = os.path.join(storage_path, f.storage_name)
        if os.path.exists(path):
            logger.info("Deleting {}".format(path))
            os.unlink(path)

    logger.info("Vacuumed {} successfully".format(beam.id))
    beam.deleted = True
    db.session.commit()


@queue.task
def mark_timeout():
    app = create_app()
    with app.app_context():
        timeout = timedelta(seconds=app.config['COMBADGE_CONTACT_TIMEOUT'])
        timed_out = datetime.utcnow() - timeout
        dead_beams = (
            db.session.query(Beam).filter_by(completed=False)
            .filter(Beam.combadge_contacted == False, Beam.start < timed_out))
        for beam in dead_beams:
            logger.info("Combadge of {} did not contact for more than {}".format(beam.id, timeout))
            beam.completed = True
            beam.error = "Combadge didn't contact the transporter"

        db.session.commit()


@queue.task
def vacuum():
    logger.info("Vacuum intiated")
    app = create_app()

    # Make sure that the storage folder is accessable. Whenever deploying scotty to somewhere, one
    # must create this empty file in the storage directory
    os.stat(os.path.join(app.config['STORAGE_PATH'], ".test"))

    with app.app_context():
        db.engine.execute(
            "update beam set pending_deletion=true where "
            "(not beam.pending_deletion and not beam.deleted and beam.completed)" # Anything which isn't uncompleted or already deleted
            "and beam.id not in (select beam_id from pin) " # which has no pinners
            "and ("
                "(beam.id not in (select beam_id from file)) " # Either has no files
                "or (beam.start < now() - '%s days'::interval)" # or has files but is VACUUM_THRESHOLD days old
            ")",
            app.config['VACUUM_THRESHOLD'])
        db.session.commit()

        to_delete = db.session.query(Beam).filter(Beam.pending_deletion == True, Beam.deleted == False)
        for beam in to_delete:
            vacuum_beam(beam, app.config['STORAGE_PATH'])
    logger.info("Vacuum done")


@worker_init.connect
def on_init(**_):
    app = create_app()
    register_signal(app.raven.client)
