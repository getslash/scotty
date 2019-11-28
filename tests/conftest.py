# pylint: disable=redefined-outer-name
import json
import os
import tempfile
import uuid
from collections import namedtuple

import pytest
from scottypy import Scotty
from urlobject import URLObject as URL

from flask_app import app, models

from time import sleep

BeamType = namedtuple('BeamType', ('name', 'threshold'))
BeamInfo = namedtuple('BeamInfo', ('beam', 'type'))

TESTS_TRACKER_NAME = 'tests_tracker'

class FileTracker:
    class Issue:
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

        def set_open(self, is_open):
            self._tracker.set_open(self._id_in_tracker, is_open)

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
        tracker = scotty.get_tracker_by_name(TESTS_TRACKER_NAME)
        if tracker is None:
            id_ = scotty.create_tracker(TESTS_TRACKER_NAME, 'file', path, '')
        else:
            id_ = tracker['id']
        return cls(scotty, path, id_)

    def dump(self):
        with open(self._path, 'w') as f:
            json.dump(self._issues, f)

    def delete(self):
        os.unlink(self._path)

    def create_issue(self, id_in_tracker):
        issue_in_scotty = None
        if id_in_tracker is None:
            id_in_tracker = str(uuid.uuid4())
        else:
            issue_in_scotty = self._scotty.get_issue_by_tracker(self._id, id_in_tracker)

        if issue_in_scotty is not None:
            id_in_scotty = issue_in_scotty.id
        else:
            id_in_scotty = self._scotty.create_issue(self._id, id_in_tracker)

        issue = self.Issue(self, id_in_scotty, id_in_tracker)
        self._issues[id_in_tracker] = True
        self.dump()
        return issue

    def set_open(self, issue_id, is_open):
        self._issues[issue_id] = is_open
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

    def check_if_beam_deleted(self, beam_obj, deleted):
        assert beam_obj.deleted == deleted


@pytest.fixture
def webapp():
    return app.create_app()


@pytest.fixture
def db(webapp):
    with webapp.app_context():
        models.db.session.close()
        models.db.drop_all()
        models.db.create_all()


@pytest.fixture
def deployment_webapp_url():
    return URL("http://127.0.0.1:8000")


@pytest.fixture
def scotty(db, deployment_webapp_url):
    return TestingScotty(deployment_webapp_url)


@pytest.fixture
def tempdir(scope="test"):
    return tempfile.mkdtemp()


@pytest.fixture
def download_dir(tempdir):
    d = os.path.join(tempdir, 'dest')
    os.mkdir(d)
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
def tracker(scotty):
    return FileTracker.create(scotty)


@pytest.fixture
def issue(tracker):
    return tracker.create_issue(id_in_tracker=None)


@pytest.fixture
def issue_factory(tracker):
    class IssueFactory:
        def get(self):
            return tracker.create_issue(id_in_tracker=None)
    return IssueFactory()


@pytest.fixture
def beam_factory(scotty, local_beam_dir):
    class BeamFactory:
        def get(self, combadge_version):
            beam_data = scotty.beam_up(local_beam_dir, combadge_version=combadge_version)
            beam = scotty.get_beam(beam_data)
            return beam
    return BeamFactory()


@pytest.fixture
def server_config(webapp):
    return webapp.config


def _beam_type(name, threshold):
    t = models.BeamType(
        name=name,
        vacuum_threshold=threshold)
    models.db.session.add(t)
    models.db.session.commit()
    return BeamType(name, threshold)


@pytest.fixture
def beam_types(server_config, db, webapp):
    with webapp.app_context():
        return {
            'short': _beam_type('short', server_config['VACUUM_THRESHOLD'] - 2),
            'long_term': _beam_type('long_term', 99999),
            'long': _beam_type('long', server_config['VACUUM_THRESHOLD'] + 2)}


def _wait_for_beam(beam_id, *, scotty):
    for _ in range(3):
        beam = scotty.get_beam(beam_id)
        if beam.completed:
            return beam

        sleep(1)

    raise RuntimeError("Beam is incomplete")


@pytest.fixture
def beam(scotty, local_beam_dir):
    beam = _wait_for_beam(scotty.beam_up(local_beam_dir), scotty=scotty)
    return BeamInfo(beam, None)


@pytest.fixture
def short_beam(scotty, local_beam_dir, beam_types):
    beam = _wait_for_beam(scotty.beam_up(local_beam_dir, beam_type='short'), scotty=scotty)
    beam_type = beam_types['short']
    return BeamInfo(beam, beam_type)


@pytest.fixture
def long_beam(scotty, local_beam_dir, beam_types):
    beam = _wait_for_beam(scotty.beam_up(local_beam_dir, beam_type='long'), scotty=scotty)
    beam_type = beam_types['long']
    return BeamInfo(beam, beam_type)


@pytest.fixture
def long_term_beam(scotty, local_beam_dir, beam_types):
    beam = scotty.get_beam(scotty.beam_up(local_beam_dir, beam_type='long_term'))
    return beam


@pytest.fixture
def faulty_tracker(scotty):
    return scotty.create_tracker('faulty_tracker', 'faulty', '', '')
