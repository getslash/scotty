import os
import time as real_time

import flux
from flask import (Blueprint, Response, current_app, make_response, request,
                   send_file)

from ..tasks import sleep as celery_sleep

test_methods = Blueprint("test_methods", __name__, template_folder="templates")

@test_methods.route("/sleep", methods=['POST'])
def sleep() -> str:
    time = request.json['time']
    flux.current_timeline.set_time_factor(0)
    flux.current_timeline.sleep(time)
    celery_sleep.delay(time)
    real_time.sleep(1)
    return ''


@test_methods.route("/file_contents/<path:storage_path>")
def file_contents(storage_path: str) -> Response:
    mimetype = None
    path = os.path.join(current_app.config['STORAGE_PATH'], storage_path)
    if not os.path.exists(path):
        mimetype = "text/plain"
        path += ".gz"
        response = make_response(open(path, "rb").read())
        response.headers['Content-Encoding'] = 'gzip'
        return response
    else:
        assert os.path.exists(path)
        return send_file(path, mimetype=mimetype)
