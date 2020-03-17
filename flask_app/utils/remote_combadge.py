import os
import stat
from pathlib import PureWindowsPath
from uuid import uuid4

import logbook

from flask_app.paths import get_combadge_path
from flask_app.utils.remote_host import RemoteHost

_COMBADGE_UUID_PART_LENGTH = 10
DEFAULT_COMBADGE_VERSION = (
    "v1"  # the current version (v2) is not the default because it's not as stable as v1
)


logger = logbook.Logger(__name__)


class RemoteCombadge:
    def __init__(self, *, remote_host: RemoteHost, combadge_version: str):
        self._combadge_version = combadge_version
        self._remote_host = remote_host
        self._remote_combadge_path = None
        self._sftp = None

    def _generate_random_combadge_name(self, string_length: int) -> str:
        random_string = str(uuid4().hex)[:string_length]
        return f"combadge_{random_string}"

    def _get_remote_combadge_path(self):
        combadge_name = self._generate_random_combadge_name(
            string_length=_COMBADGE_UUID_PART_LENGTH
        )
        remote_combadge_dir = self._remote_host.get_temp_dir()
        if self._remote_host.get_os_type() == "windows":
            combadge_name = f"{combadge_name}.exe"
            remote_combadge_path = str(
                PureWindowsPath(os.path.join(remote_combadge_dir, combadge_name))
            )
        else:
            remote_combadge_path = os.path.join(remote_combadge_dir, combadge_name)
        logger.debug(f"combadge path: {remote_combadge_path}")
        return remote_combadge_path

    def _upload_combadge(self):
        os_type = self._remote_host.get_os_type()

        local_combadge_path = get_combadge_path(self._combadge_version, os_type=os_type)
        assert os.path.exists(
            local_combadge_path
        ), f"Combadge at {local_combadge_path} does not exist"
        remote_combadge_path = self._get_remote_combadge_path()

        logger.info(
            f"uploading combadge {self._combadge_version} for {os_type} to {remote_combadge_path}"
        )
        self._sftp = self._remote_host.get_sftp_client()
        self._sftp.put(local_combadge_path, remote_combadge_path)
        if os_type != "windows":
            combadge_st = os.stat(local_combadge_path)
            self._sftp.chmod(remote_combadge_path, combadge_st.st_mode | stat.S_IEXEC)
        self._remote_combadge_path = remote_combadge_path

    def _remove_combadge(self):
        if self._remote_combadge_path is not None and self._sftp is not None:
            try:
                self._sftp.remove(self._remote_combadge_path)
            except FileNotFoundError:
                logger.warn(
                    f"Combadge {self._remote_combadge_path} not found when trying to remove it"
                )

    def __enter__(self):
        self._upload_combadge()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_combadge()
        if self._sftp is not None:
            self._sftp.close()

    def run(self, *, beam_id: int, directory: str, transporter: str) -> None:
        combadge_commands = {
            "v1": f'{self._remote_combadge_path} {beam_id} "{directory}" "{transporter}"',
            "v2": f"{self._remote_combadge_path} -b {beam_id} -p {directory} -t {transporter}",
        }
        combadge_command = combadge_commands[self._combadge_version]
        self._remote_host.exec_ssh_command(combadge_command)

    def ping(self):
        _, stdout, stderr = self._remote_host.raw_exec_ssh_command(
            self._remote_combadge_path
        )
        return "usage" in (stdout.read().decode() + stderr.read().decode()).lower()
