from flask_app.paths import get_combadge_path
import os

def test_get_local_combadge_path():
    for os_type in ['linux', 'windows', 'darwin']:
        assert os.path.exists(get_combadge_path(os_type))