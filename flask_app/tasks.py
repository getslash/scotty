import os
import traceback
from io import StringIO
from celery import Celery
from paramiko import SSHClient
from paramiko.client import AutoAddPolicy
from paramiko.rsakey import RSAKey
import socket
from .app import create_app
from .models import Beam, db
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from celery.signals import worker_init, task_failure
from raven.contrib.celery import register_signal


logger = get_task_logger(__name__)

queue = Celery('tasks', broker='redis://localhost')
queue.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
    CELERY_RESULT_SERIALIZER='json',
    CELERY_ENABLE_UTC=True,
    CELERYBEAT_SCHEDULE = {
        'vacuum': {
            'task': 'flask_app.tasks.vacuum',
            'schedule': crontab(hour=0, minute=0),
        }},
    CELERY_TIMEZONE='UTC'
)

def create_key(s):
    f = StringIO()
    f.write(s)
    f.seek(0)
    return RSAKey.from_private_key(file_obj=f, password=None)


with open(os.path.join(os.path.dirname(__file__), "../scripts/combadge.py"), "r") as f:
    _COMBADGE = f.read()


@queue.task
def beam_up(beam_id, host, directory, username, pkey):
    app = create_app()
    transporter = app.config.get('TRANSPORTER_HOST', 'scotty')
    logger.info('Beaming up {}@{}:{} ({}) to transporter {}'.format(username, host, directory, beam_id, transporter))
    pkey = create_key(pkey)
    ssh_client = SSHClient()
    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
    ssh_client.connect(host, username=username, pkey=pkey, look_for_keys=False)
    logger.info('{}: Connected to {}. Uploading combadge'.format(beam_id, host))

    stdin, stdout ,stderr = ssh_client.exec_command("cat > /tmp/combadge.py && chmod +x /tmp/combadge.py")
    stdin.write(_COMBADGE)
    stdin.channel.shutdown_write()
    retcode = stdout.channel.recv_exit_status()
    assert retcode == 0

    logger.info('{}: Running combadge'.format(beam_id))
    _, stdout, stderr = ssh_client.exec_command(
        '/tmp/combadge.py {} "{}" "{}"'.format(str(beam_id), directory, transporter))
    retcode = stdout.channel.recv_exit_status()
    assert retcode == 0, (stderr.read(), stdout.read())
    logger.info('{}: Beam completed'.format(beam_id))


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
def vacuum():
    logger.info("Vacuum intiated")
    app = create_app()

    # Make sure that the storage folder is accessable. Whenever deploying scotty to somewhere, one
    # must create this empty file in the storage directory
    os.stat(os.path.join(app.config['STORAGE_PATH'], ".test"))

    with app.app_context():
        db.engine.execute(
            "update beam set pending_deletion=true where not beam.pending_deletion and not beam.deleted and beam.id not in (select beam_id from pin)")
        db.session.commit()

        to_delete = db.session.query(Beam).filter(Beam.pending_deletion == True, Beam.deleted == False)
        for beam in to_delete:
            vacuum_beam(beam, app.config['STORAGE_PATH'])
    logger.info("Vacuum done")


@worker_init.connect
def on_init(**kwargs):
    app = create_app()
    register_signal(app.raven.client)
