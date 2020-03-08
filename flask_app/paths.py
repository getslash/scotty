import os

COMBADGE_PATH_V1 = os.path.join(os.path.dirname(__file__), "..", "webapp", "dist", "assets", "combadge.py")
COMBADGE_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "combadge_assets")


def get_combadge_path(combadge_version, *, os_type):
    if combadge_version == 'v1':
        return COMBADGE_PATH_V1
    asset_name = 'combadge.exe' if os_type == 'windows' else 'combadge'
    return os.path.join(COMBADGE_ASSETS_DIR, combadge_version, f"combadge_{os_type}", asset_name)
