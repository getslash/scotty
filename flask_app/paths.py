import os

COMBADGE_PATH_V1 = os.path.join(os.path.dirname(__file__), "..", "webapp", "dist", "assets", "combadge.py")
COMBADGE_PATH_V2 = os.path.join(os.path.dirname(__file__), "..", "combadge", "target", "x86_64-unknown-linux-musl", "release", "combadge")


_COMBADGE_PATHS = {'v2': COMBADGE_PATH_V2,
                   'v1': COMBADGE_PATH_V1}


def get_combadge_path(combadge_version):
    return _COMBADGE_PATHS.get(combadge_version)
