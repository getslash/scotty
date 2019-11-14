import os

COMBADGE_PATH_V1 = os.path.join(os.path.dirname(__file__), "..", "webapp", "dist", "assets", "combadge.py")
COMBADGE_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "combadge_assets")
COMBADGE_PATH_LINUX = os.path.join(COMBADGE_ASSETS_DIR "combadge_linux")
COMBADGE_PATH_WINDOWS = os.path.join(COMBADGE_ASSETS_DIR "combadge_windows")
COMBADGE_PATH_DARWIN = os.path.join(COMBADGE_ASSETS_DIR "combadge_darwin")

_COMBADGE_PATHS = {'linux': COMBADGE_PATH_LINUX,
                   'windows': COMBADGE_PATH_WINDOWS,
                   'darwin': COMBADGE_PATH_DARWIN,
                   'v1': COMBADGE_PATH_V1}


def get_combadge_path(combadge_version):
    return _COMBADGE_PATHS.get(combadge_version)
