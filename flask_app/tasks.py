import os
from io import StringIO
from celery import Celery
from paramiko import SSHClient
from paramiko.client import AutoAddPolicy
from paramiko.rsakey import RSAKey
import socket
from .app import create_app
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

queue = Celery('tasks', broker='redis://localhost')
queue.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
    CELERY_RESULT_SERIALIZER='json',
    CELERY_ENABLE_UTC=True,
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
