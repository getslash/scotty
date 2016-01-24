import os
import sys
import uuid
import tempfile
import shutil
import json
from collections import namedtuple
from functools import partial

import requests
from urlobject import URLObject as URL

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scottypy import Scotty
import slash
import flask.ext.login
from flask_app import app, models



BeamType = namedtuple('BeamType', ('name', 'threshold'))
BeamInfo = namedtuple('BeamInfo', ('beam', 'type'))


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

    def check_beam_state(self, beam_obj, deleted):
        assert beam_obj.deleted == deleted



@slash.fixture
def deployment_webapp_url():
    return URL("http://127.0.0.1:8000")


@slash.fixture
def webapp():
    from flask.ext import login

    return app.create_app()


@slash.fixture
def server_config(webapp):
    return webapp.config


@slash.fixture
def db(webapp):
    with webapp.app_context():
        models.db.session.close()
        models.db.drop_all()
        models.db.create_all()


def _beam_type(name, threshold):
    t = models.BeamType(
        name=name,
        vacuum_threshold=threshold)
    models.db.session.add(t)
    models.db.session.commit()
    return BeamType(name, threshold)


@slash.fixture
def beam_types(server_config, db, webapp):
    with webapp.app_context():
        return {
            'short': _beam_type('short', server_config['VACUUM_THRESHOLD'] - 2),
            'long': _beam_type('long', server_config['VACUUM_THRESHOLD'] + 2)}


@slash.fixture
def scotty(db, deployment_webapp_url):
    return TestingScotty(deployment_webapp_url)


@slash.fixture
def tempdir():
    d = tempfile.mkdtemp()
    slash.add_critical_cleanup(partial(shutil.rmtree, d))
    return d


@slash.fixture
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


@slash.fixture
def download_dir(tempdir):
    d = os.path.join(tempdir, 'dest')
    os.mkdir(d)
    return d


@slash.fixture
def beam(scotty, local_beam_dir):
    beam = scotty.get_beam(scotty.beam_up(local_beam_dir))
    return BeamInfo(beam, None)


@slash.parametrize('beam_type', [None, 'short', 'long'])
@slash.fixture
def typed_beam(scotty, local_beam_dir, beam_type, beam_types):
    beam = scotty.get_beam(scotty.beam_up(local_beam_dir, beam_type=beam_type))
    beam_type = beam_types[beam_type] if beam_type else None
    return BeamInfo(beam, beam_type)


class Webapp(object):

    def __init__(self, app):
        super(Webapp, self).__init__()
        self.app = app
        from flask.ext.loopback import FlaskLoopback
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
