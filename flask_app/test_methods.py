import os
from flask import Blueprint, send_file, current_app

test_methods = Blueprint("test_methods", __name__, template_folder="templates")

@test_methods.route("/file_contents/<path:storage_path>")
def file_contents(storage_path):
    return send_file(os.path.join(current_app.config['STORAGE_PATH'], storage_path))
