import enum
from datetime import timedelta
from ..conftest import issue
import logging

import pytest

_DAY = timedelta(days=1)


def _validate_no_purge_time(beam):
        beam.update()
        assert beam.purge_time == None


def test_short_beam_vacuum(scotty, short_beam):
    beam, beam_type = short_beam
    vacuum_threshold = beam_type.threshold

    for i in range(vacuum_threshold - 1):
        scotty.sleep(_DAY)
        beam.update()
        assert beam.purge_time == vacuum_threshold - i - 1
        scotty.check_if_beam_deleted(beam, False)

    scotty.sleep(_DAY)
    beam.update()
    assert beam.purge_time == 0
    scotty.check_if_beam_deleted(beam, True)


def test_long_beam_vacuum(scotty, long_beam):
    beam, beam_type = long_beam
    vacuum_threshold = beam_type.threshold

    for i in range(vacuum_threshold - 1):
        scotty.sleep(_DAY)
        beam.update()
        assert beam.purge_time == vacuum_threshold - i - 1
        scotty.check_if_beam_deleted(beam, False)

    scotty.sleep(_DAY)
    beam.update()
    assert beam.purge_time == 0
    scotty.check_if_beam_deleted(beam, True)


def test_pinned_beam(scotty, short_beam):
    beam, beam_type = short_beam
    vacuum_threshold = beam_type.threshold
    assert beam.purge_time == vacuum_threshold

    scotty.pin(beam, True)

    scotty.sleep(_DAY * vacuum_threshold)
    _validate_no_purge_time(beam)
    scotty.check_if_beam_deleted(beam, False)

    scotty.pin(beam, False)
    scotty.sleep(_DAY)
    beam.update()
    scotty.check_if_beam_deleted(beam, True)


def test_short_beam_with_issue_closed(scotty, short_beam, issue):
    beam, beam_type = short_beam
    vacuum_threshold = beam_type.threshold
    assert beam.purge_time == vacuum_threshold

    beam.set_issue_association(issue.id_in_scotty, True)

    scotty.sleep(_DAY * (vacuum_threshold+1))
    _validate_no_purge_time(beam)
    scotty.check_if_beam_deleted(beam, False)

    issue.set_open(False)
    scotty.sleep(_DAY)
    beam.update()
    scotty.check_if_beam_deleted(beam, True)


def test_long_beam_with_issue_closed(scotty, long_beam, issue):
    beam, beam_type = long_beam
    vacuum_threshold = beam_type.threshold

    assert beam.purge_time == vacuum_threshold

    beam.set_issue_association(issue.id_in_scotty, True)

    scotty.sleep(_DAY * vacuum_threshold)
    _validate_no_purge_time(beam)
    scotty.check_if_beam_deleted(beam, False)

    issue.set_open(False)
    scotty.sleep(_DAY)
    beam.update()
    scotty.check_if_beam_deleted(beam, True)


def test_beam_with_issue_unassigned(scotty, short_beam, issue):
    beam, beam_type = short_beam
    vacuum_threshold = beam_type.threshold
    assert beam.purge_time == vacuum_threshold

    beam.set_issue_association(issue.id_in_scotty, True)

    scotty.sleep(_DAY * vacuum_threshold)
    _validate_no_purge_time(beam)
    scotty.check_if_beam_deleted(beam, False)

    beam.set_issue_association(issue.id_in_scotty, False)
    scotty.sleep(timedelta(seconds=0))
    beam.update()
    scotty.check_if_beam_deleted(beam, True)


def test_multiple_issues(tracker, scotty, beam, server_config, long_term_beam, issue_factory):
    vacuum_threshold = server_config['VACUUM_THRESHOLD']
    beam, _ = beam

    issue1 = issue_factory.get()
    issue2 = issue_factory.get()

    for i in [issue1, issue2]:
        beam.set_issue_association(i.id_in_scotty, True)

    _validate_no_purge_time(beam)

    scotty.sleep(_DAY * vacuum_threshold)
    _validate_no_purge_time(beam)

    scotty.check_if_beam_deleted(beam, False)

    scotty.sleep(_DAY)
    _validate_no_purge_time(beam)

    issue1.set_open(False)

    scotty.sleep(_DAY)
    _validate_no_purge_time(beam)

    scotty.check_if_beam_deleted(beam, False)

    issue2.set_open(False)

    scotty.sleep(_DAY)
    beam.update()

    scotty.check_if_beam_deleted(beam, True)
    scotty.check_if_beam_deleted(long_term_beam, False)


@pytest.mark.parametrize("combadge_version", ['v1', 'v2'])
def test_faulty_tracker(scotty, issue, server_config, faulty_tracker, beam_factory, combadge_version):
    vacuum_threshold = server_config['VACUUM_THRESHOLD']
    beams = []

    regular_beam = beam_factory.get(combadge_version=combadge_version)
    beams.append(regular_beam)

    beam_with_issue = beam_factory.get(combadge_version=combadge_version)
    beam_with_issue.set_issue_association(issue.id_in_scotty, True)
    beam_with_issue.update()
    beams.append(beam_with_issue)

    faulty_issue = scotty.create_issue(faulty_tracker, '1')
    beam_with_faulty_issue = beam_factory.get(combadge_version=combadge_version)
    beam_with_faulty_issue.set_issue_association(faulty_issue, True)
    beam_with_faulty_issue.update()
    beams.append(beam_with_faulty_issue)

    assert beam_with_issue.purge_time is None
    assert beam_with_faulty_issue.purge_time is None
    assert regular_beam.purge_time == vacuum_threshold
    scotty.sleep(_DAY * vacuum_threshold)

    for beam in beams:
        beam.update()

    scotty.check_if_beam_deleted(regular_beam, True)
    scotty.check_if_beam_deleted(beam_with_faulty_issue, False)
    scotty.check_if_beam_deleted(beam_with_issue, False)

    issue.set_open(False)
    scotty.sleep(_DAY)
    beam_with_issue.update()
    scotty.check_if_beam_deleted(beam_with_issue, True)


@pytest.mark.parametrize("combadge_version", ['v1', 'v2'])
def test_multiple_issues_and_multiple_beams(local_beam_dir, scotty, server_config, long_term_beam, issue_factory, combadge_version):
    vacuum_threshold = server_config['VACUUM_THRESHOLD']
    beam1 = scotty.get_beam(scotty.beam_up(local_beam_dir, combadge_version=combadge_version))
    beam2 = scotty.get_beam(scotty.beam_up(local_beam_dir, combadge_version=combadge_version))
    states = {beam1: False, beam2: False}
    issue1 = issue_factory.get()
    issue2 = issue_factory.get()

    beam1.set_issue_association(issue1.id_in_scotty, True)
    beam2.set_issue_association(issue2.id_in_scotty, True)

    def validate():
        for beam, should_be_deleted in states.items():
            beam.update()
            if not should_be_deleted:
                assert beam.purge_time is None
                scotty.check_if_beam_deleted(beam, should_be_deleted)

    scotty.sleep(_DAY * vacuum_threshold)
    validate()

    scotty.sleep(_DAY)

    validate()

    issue1.set_open(False)
    scotty.sleep(timedelta(seconds=0))

    states[beam1] = True
    validate()
    scotty.check_if_beam_deleted(long_term_beam, False)


@pytest.mark.parametrize("combadge_version", ['v1', 'v2'])
def test_rolling(scotty, beam_factory, combadge_version):
    def update_beams(beams):
        for beam in beams:
            beam.update()

    def check_deleted_by_index(beams, idx):
        for beam in beams[:idx]:
            scotty.check_if_beam_deleted(beam, True)
        for beam in beams[idx:]:
            scotty.check_if_beam_deleted(beam, False)

    beams = []

    pinned_beam = beam_factory.get(combadge_version=combadge_version)
    scotty.pin(pinned_beam, True)

    beams.append(beam_factory.get(combadge_version=combadge_version))
    scotty.sleep(_DAY * 7)
    update_beams(beams)
    scotty.check_if_beam_deleted(beams[0], False)

    pinned_beam.update()
    scotty.check_if_beam_deleted(pinned_beam, False)

    for idx in range(1, 10):
        beams.append(beam_factory.get(combadge_version=combadge_version))
        scotty.sleep(_DAY * 7)
        update_beams(beams)
        check_deleted_by_index(beams, idx)

        pinned_beam.update()
        scotty.check_if_beam_deleted(pinned_beam, False)

    scotty.pin(pinned_beam, False)
    scotty.sleep(timedelta(seconds=0))
    pinned_beam.update()
    scotty.check_if_beam_deleted(pinned_beam, True)
