import io
from unittest import mock

import logbook
import pytest
from paramiko import SSHException

from flask_app.utils.remote_combadge import RemoteCombadge
from flask_app.utils.remote_host import RemoteHost


@pytest.fixture
def caplog():
    sio = io.StringIO()
    handler = logbook.StreamHandler(sio)
    handler.push_application()
    yield sio
    handler.pop_application()


def test_remove_combadge_fails_silently_on_ssh_exception(
    mock_ssh_client, mock_sftp_client, caplog, monkeypatch, combadge_assets_dir
):
    mock_remove = mock.MagicMock()
    reason = "Mock reason"
    mock_remove.side_effect = SSHException(reason)
    monkeypatch.setattr(mock_sftp_client, "remove", mock_remove)
    host = RemoteHost(
        host="mock-host", username="mock-user", auth_method="password", password="blah"
    )
    combadge = RemoteCombadge(remote_host=host, combadge_version="v2")
    # combadge is removed on __exit__
    with host, combadge:
        pass
    assert len(mock_remove.call_args_list) == 1
    file_name = list(mock_remove.call_args_list[0])[0][0]
    caplog.seek(0)
    assert f"Failed to remove {file_name}: {reason}" in caplog.read()
