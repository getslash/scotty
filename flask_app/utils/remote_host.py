import functools
from io import StringIO

import logbook
from paramiko import AutoAddPolicy, RSAKey, SFTPClient, SSHClient

logger = logbook.Logger(__name__)


def create_key(s: str) -> str:
    f = StringIO()
    f.write(s)
    f.seek(0)
    return RSAKey.from_private_key(file_obj=f, password=None)


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
            raise RuntimeError(f"Failed to execute command {command}: {stderr.read().decode('utf-8')}")

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
            raise ValueError(f'Invalid auth method: {self._auth_method}')

        self._ssh_client.connect(self.host, **kwargs)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
