import pytest

from flask_app.paths import get_combadge_path
import os


@pytest.mark.parametrize('os_type', ['linux', 'windows', 'darwin'])
@pytest.mark.parametrize('combadge_version', ['v1', 'v2'])
def test_get_local_combadge_path(os_type, combadge_version):
    assert os.path.exists(get_combadge_path(combadge_version, os_type=os_type))
