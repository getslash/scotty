import os
import sys
import tempfile
import shutil
import json
import uuid
from collections import namedtuple
from functools import partial

from urlobject import URLObject as URL

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scottypy import Scotty
import slash
import flask.ext.login
from flask_app import app, models



BeamType = namedtuple('BeamType', ('name', 'threshold'))
BeamInfo = namedtuple('BeamInfo', ('beam', 'type'))


class FileTracker(object):
    class Issue(object):
        def __init__(self, tracker, id_in_scotty, id_in_tracker):
            self._id_in_tracker = id_in_tracker
            self._id_in_scotty = id_in_scotty
            self._tracker = tracker

        @property
        def id_in_scotty(self):
            return self._id_in_scotty

        @property
        def id_in_tracker(self):
            return self._id_in_tracker

        def set_state(self, open_):
            self._tracker.set_state(self._id_in_tracker, open_)

        def delete(self):
            self._tracker._scotty.delete_issue(self._id_in_scotty)

    def __init__(self, scotty, path, id_):
        self._scotty = scotty
        self._path = path
        self._id = id_
        self._issues = {}

    @classmethod
    def create(cls, scotty):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        id_ = scotty.create_tracker('tests_tracker', 'file', path, '')
        return cls(scotty, path, id_)

    def dump(self):
        with open(self._path, 'w') as f:
            json.dump(self._issues, f)

    def delete(self):
        os.unlink(self._path)

    def create_issue(self, id_in_tracker=None):
        if id_in_tracker is None:
            id_in_tracker = str(uuid.uuid4())
        self._issues[id_in_tracker] = True
        id_in_scotty = self._scotty.create_issue(self._id, id_in_tracker)
        issue = self.Issue(self, id_in_scotty, id_in_tracker)
        self.dump()
        return issue

    def set_state(self, issue_id, open_):
        self._issues[issue_id] = open_
        self.dump()

    @property
    def path(self):
        return self._path

    @property
    def id(self):
        return self._id

    def delete_from_scotty(self):
        self._scotty.delete_tracker(self._id)

    def update(self, *args, **kwargs):
        self._scotty.update_tracker(self._id, *args, **kwargs)


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
        self._session.put("{}/pin".format(self._url), data=json.dumps(data)).raise_for_status()

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
            'long_term': _beam_type('long_term', 99999),
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
def tracker(scotty):
    return FileTracker.create(scotty)


@slash.fixture
def faulty_tracker(scotty):
    return scotty.create_tracker('faulty_tracker', 'faulty', '', '')


@slash.fixture
def issue(tracker):
    return tracker.create_issue()


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
    assert beam.completed
    return BeamInfo(beam, None)


@slash.parametrize('beam_type', [None, 'short', 'long'])
@slash.fixture
def typed_beam(scotty, local_beam_dir, beam_type, beam_types):
    beam = scotty.get_beam(scotty.beam_up(local_beam_dir, beam_type=beam_type))
    beam_type = beam_types[beam_type] if beam_type else None
    return BeamInfo(beam, beam_type)


@slash.fixture
def long_term_beam(scotty, local_beam_dir, beam_types):
    beam = scotty.get_beam(scotty.beam_up(local_beam_dir, beam_type='long_term'))
    return beam
