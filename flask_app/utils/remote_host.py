import functools
from io import StringIO

import logbook
from paramiko import AuthenticationException, AutoAddPolicy, PKey, RSAKey, SFTPClient, SSHClient

logger = logbook.Logger(__name__)


def create_key(s: str) -> PKey:
    f = StringIO()
    f.write(s)
    f.seek(0)
    return RSAKey.from_private_key(file_obj=f, password=None)


class RemoteHost:
    _TEMPDIR_COMMAND = "python -c 'import tempfile; print(tempfile.gettempdir())'"

    def __init__(self, *, host, username, auth_method, pkey=None, password=None):
        self._host = host
        self._username = username
        self._auth_method = auth_method
        self._pkey = pkey
        self._password = password
        self._ssh_client = None

    @functools.lru_cache(maxsize=None)
    def get_os_type(self) -> str:
        return (self.exec_ssh_command("uname", raise_on_failure=False) or "windows").lower()

    def get_temp_dir(self) -> str:
        try:
            return self.exec_ssh_command(self._TEMPDIR_COMMAND)
        except RuntimeError:
            return self.exec_ssh_command(self._TEMPDIR_COMMAND.replace("python", "python3"))

    def exec_ssh_command(self, command, raise_on_failure=True):
        _, stdout, stderr = self.raw_exec_ssh_command(command)
        retcode = stdout.channel.recv_exit_status()
        stdout_text = stdout.read().decode().strip()
        stderr_text = stderr.read().decode().strip()
        if retcode == 0:
            logger.debug(
                f"Command {command} completed successfully."
                f"\nstdout: {stdout_text}"
                f"\nstderr: {stderr_text}"
            )
            return stdout_text
        if raise_on_failure:
            raise RuntimeError(
                f"Failed to execute command {command}:"
                f"\nstdout:\n{stdout_text}"
                f"\nstderr:\n{stderr_text}"
            )

    def raw_exec_ssh_command(self, command):
        logger.info(f"executing on host {self._host} command {command}")
        return self._ssh_client.exec_command(command)

    def get_sftp_client(self):
        return SFTPClient.from_transport(self._ssh_client.get_transport())

    def close(self):
        if self._ssh_client is not None:
            self._ssh_client.close()

    def __enter__(self):
        self._ssh_client = ssh_client = SSHClient()
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())

        kwargs = {"username": self._username, "look_for_keys": False}
        if self._auth_method in ("rsa", "stored_key"):
            kwargs["pkey"] = create_key(self._pkey)
        elif self._auth_method == "password":
            kwargs["password"] = self._password
        else:
            raise ValueError(f"Invalid auth method: {self._auth_method}")

        try:
            self._ssh_client.connect(self._host, **kwargs)
        except AuthenticationException:
            self._ssh_client.connect(
                self._host,
                disabled_algorithms={
                    "keys": ["rsa-sha2-256", "rsa-sha2-512"],
                    "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"],
                },
                **kwargs,
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
