import os
import sys
import uuid
import tempfile
import shutil
import json
from functools import partial

import requests
from flask.ext.loopback import FlaskLoopback
from urlobject import URLObject as URL

from scottypy import Scotty
import pytest
from flask_app import app, models

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def pytest_addoption(parser):
    parser.addoption("--www-port", action="store", default=8000, type=int)


class TestingScotty(Scotty):
    def __init__(self, *args, **kwargs):
        super(TestingScotty, self).__init__(*args, **kwargs)
        self._session.headers['X-Scotty-Email'] = "test@getslash.org"

    def sleep(self, time_to_sleep):
        response = self._session.post("{}/sleep".format(self._url),
                           data=json.dumps({'time': time_to_sleep.total_seconds()}))
        response.raise_for_status()

    def pin(self, beam_obj, should_pin):
        data = {
            'beam_id': beam_obj.id,
            'should_pin': should_pin
        }
        self._session.put("{}/pin".format(self._url), data=json.dumps(data))


@pytest.fixture
def deployment_webapp_url(request):
    port = request.config.getoption("--www-port")
    return URL("http://127.0.0.1").with_port(port)


@pytest.fixture
def webapp():
    return app.create_app()


@pytest.fixture
def server_config(webapp):
    return webapp.config


@pytest.fixture
def db(webapp):
    with webapp.app_context():
        models.db.session.close()
        models.db.drop_all()
        models.db.create_all()


@pytest.fixture
def scotty(db, deployment_webapp_url):
    return TestingScotty(deployment_webapp_url)


@pytest.fixture
def tempdir(request):
    d = tempfile.mkdtemp()
    request.addfinalizer(partial(shutil.rmtree, d))
    return d


@pytest.fixture
def local_beam_dir(tempdir):
    source_dir = os.path.join(tempdir, 'source')
    os.mkdir(source_dir)

    with open(os.path.join(source_dir, 'a.txt'), 'w') as f:
        f.write('Hello')

    with open(os.path.join(source_dir, 'b.bin'), 'wb') as f:
        f.write(b'\x10\x12\x04')

    subdir = os.path.join(source_dir, 'subdir')
    os.mkdir(subdir)

    with open(os.path.join(subdir, 'c.txt'), 'w') as f:
        f.write('Hello in subdir')

    return source_dir


@pytest.fixture
def download_dir(tempdir):
    d = os.path.join(tempdir, 'dest')
    os.mkdir(d)
    return d


@pytest.fixture
def beam(scotty, local_beam_dir):
    return scotty.get_beam(scotty.beam_up(local_beam_dir))


class Webapp(object):

    def __init__(self, app):
        super(Webapp, self).__init__()
        self.app = app
        self.loopback = FlaskLoopback(self.app)
        self.hostname = str(uuid.uuid1())

    def activate(self):
        self.loopback.activate_address((self.hostname, 80))

    def deactivate(self):
        self.loopback.deactivate_address((self.hostname, 80))

    def _request(self, method, path, *args, **kwargs):
        raw_response = kwargs.pop("raw_response", False)
        if path.startswith("/"):
            path = path[1:]
            assert not path.startswith("/")
        returned = requests.request(method, "http://{0}/{1}".format(self.hostname, path), *args, **kwargs)
        if raw_response:
            return returned

        returned.raise_for_status()
        return returned.json()

def _make_request_shortcut(method_name):
    def json_method(self, *args, **kwargs):
        return self._request(method_name, *args, **kwargs)

    json_method.__name__ = method_name
    setattr(Webapp, method_name, json_method)

    def raw_method(self, *args, **kwargs):
        return self._request(method_name, raw_response=True, *args, **kwargs)

    raw_method.__name__ = "{0}_raw".format(method_name)
    setattr(Webapp, raw_method.__name__, raw_method)

for _method in ("get", "put", "post", "delete"):
    _make_request_shortcut(_method)
