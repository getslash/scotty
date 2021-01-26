import http
import uuid
from itertools import chain, combinations

import pytest
import requests
import slash


def powerset(iterable):
    s = list(iterable)
    return (
        frozenset(p) for p in chain.from_iterable((combinations(s, r)) for r in range(len(s) + 1))
    )


def test_empty_issue(tracker):
    with pytest.raises(requests.exceptions.HTTPError) as e:
        tracker.create_issue(" ")
    assert e._excinfo[1].response.status_code == http.client.CONFLICT


def test_issue_creation(beam, issue_factory):
    issue = issue_factory.get()
    beam, _ = beam
    assert len(beam.associated_issues) == 0
    beam.set_issue_association(issue.id_in_scotty, True)
    beam.update()
    assert beam.associated_issues == [issue.id_in_scotty]
    beam.set_issue_association(issue.id_in_scotty, False)
    beam.update()
    assert len(beam.associated_issues) == 0


def test_issue_deletion(beam, issue_factory):
    issue = issue_factory.get()
    beam, _ = beam
    assert len(beam.associated_issues) == 0
    beam.set_issue_association(issue.id_in_scotty, True)
    beam.update()
    assert beam.associated_issues == [issue.id_in_scotty]
    issue.delete()
    beam.update()
    assert len(beam.associated_issues) == 0


def test_tracker_deletion(beam, tracker, issue_factory):
    issue = issue_factory.get()
    beam, _ = beam
    assert len(beam.associated_issues) == 0
    beam.set_issue_association(issue.id_in_scotty, True)
    beam.update()
    assert beam.associated_issues == [issue.id_in_scotty]
    tracker.delete_from_scotty()
    beam.update()
    assert len(beam.associated_issues) == 0


def test_tracker_get_by_name(tracker, scotty):
    assert scotty.get_tracker_id("tests_tracker") == tracker.id


@pytest.mark.parametrize("add_spaces", [True, False])
def test_create_issue_twice(issue_factory, tracker, scotty, add_spaces):
    issue = issue_factory.get()
    new_name = issue.id_in_tracker
    if add_spaces:
        new_name = "  " + new_name + "  "
    assert scotty.create_issue(tracker.id, new_name) == issue.id_in_scotty


_TRACKER_PARAMS = frozenset(["url", "name", "config"])


@pytest.mark.parametrize("params", powerset(_TRACKER_PARAMS))
def test_tracker_modification(scotty, tracker, params):
    def _get_tracker_data():
        response = scotty._session.get("{}/trackers/{}".format(scotty._url, tracker.id))
        response.raise_for_status()
        return response.json()["tracker"]

    original_data = _get_tracker_data()

    unmodified_params = _TRACKER_PARAMS - params
    kwargs = {p: str(uuid.uuid4()) for p in params}
    if "config" in kwargs:
        kwargs["config"] = {"value": str(uuid.uuid4())}

    tracker.update(**kwargs)

    data = _get_tracker_data()

    for p in unmodified_params:
        assert data[p] == original_data[p]

    for p in params:
        assert data[p] == kwargs[p]
