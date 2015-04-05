import os
from celery import Celery
from paramiko import SSHClient
from paramiko.client import AutoAddPolicy
from paramiko.rsakey import RSAKey

queue = Celery('tasks', broker='redis://localhost')
queue.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
    CELERY_RESULT_SERIALIZER='json',
    CELERY_ENABLE_UTC=True,
)


with open(os.path.join(os.path.dirname(__file__), "../scripts/combadge.py"), "r") as f:
    _COMBADGE = f.read()


@queue.task
def beam_up(host, directory, username, pkey):
    ssh_client = SSHClient()
    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
    ssh_client.connect(host, username=username, pkey=pkey, look_for_keys=False)

    stdin, stdout ,stderr = ssh_client.exec_command("cat > /tmp/combadge.py && chmod +x /tmp/combadge.py")
    stdin.write(_COMBADGE)
    stdin.channel.shutdown_write()
    retcode = stdout.channel.recv_exit_status()
    assert retcode == 0

    #_, stdout, stderr = ssh_client.exec_command("")



if __name__ == '__main__':
    import os
    with open(os.path.expanduser("~/.ssh/qa-io.id_rsa"), 'r') as f:
        key = RSAKey.from_private_key(file_obj=f, password=None)
        beam_up("roeyd-ubuntu", "/home/roey", "roeyd", key)
