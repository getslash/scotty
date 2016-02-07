import os
import flux
from flask import Blueprint, send_file, current_app, request
from ..tasks import sleep as celery_sleep

test_methods = Blueprint("test_methods", __name__, template_folder="templates")

@test_methods.route("/sleep", methods=['POST'])
def sleep():
    time = request.json['time']
    flux.current_timeline.set_time_factor(0)
    flux.current_timeline.sleep(time)
    celery_sleep.delay(time).wait()
    return ''


@test_methods.route("/file_contents/<path:storage_path>")
def file_contents(storage_path):
    return send_file(os.path.join(current_app.config['STORAGE_PATH'], storage_path))
