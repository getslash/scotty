import functools
import os
import subprocess
import sys

PYTHON_INTERPRETER = "python3.9"
_PREVENT_FORK_MARKER = 'WEBER_PREVENT_FORK'

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ENV_DIR = os.environ.get("VIRTUALENV_PATH", os.path.join(_PROJECT_ROOT, ".venv"))

from_project_root = functools.partial(os.path.join, _PROJECT_ROOT)
from_env = functools.partial(os.path.join, _ENV_DIR)
from_env_bin = functools.partial(from_env, "bin")



def which(bin):
    for directory in os.environ['PATH'].split(':'):
        full_path = os.path.join(directory, bin)
        if os.path.isfile(full_path):
            return full_path

    raise ValueError('Could not find a python interpreter named {}'.format(bin))


def _is_dep_out_of_date(dep):
    depfile_mtime = os.stat(_get_depfile_path(dep)).st_mtime
    try:
        timestamp = os.stat(_get_timestamp_path(dep)).st_mtime
    except OSError:
        timestamp = 0
    return depfile_mtime >= timestamp


def _get_depfile_path(dep):
    return os.path.join(_PROJECT_ROOT, "deps", dep + ".txt")


def _mark_up_to_date(dep):
    with open(_get_timestamp_path(dep), "w"):
        pass


def _get_timestamp_path(dep):
    return os.path.join(_ENV_DIR, "{}_dep_timestamp".format(dep))
