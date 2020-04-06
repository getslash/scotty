import datetime
import json


def assert_is_jsonifiable(obj):
    try:
        json.dumps(obj)
    except Exception as e:
        raise AssertionError(f"Couldn't jsonify {obj}") from e


def test_set_completed(create_beam, db_session):
    start = datetime.datetime.utcnow()
    beam = create_beam(start=start, completed=False)
    assert beam.end is None
    assert_is_jsonifiable(beam.to_dict(0))
    end = datetime.datetime.utcnow()
    beam.set_completed(True)
    db_session.commit()
    assert beam.end is not None
    assert beam.end >= end
    assert_is_jsonifiable(beam.to_dict(0))


def test_set_completed_twice_doesnt_change_end_date(create_beam, db_session):
    start = datetime.datetime.utcnow()
    beam = create_beam(start=start, completed=False)
    assert beam.end is None
    beam.set_completed(True)
    db_session.commit()
    end = beam.end
    assert end is not None
    beam.set_completed(True)
    db_session.commit()
    assert beam.end == end


def test_set_completed_to_false_removes_end(create_beam, db_session):
    start = datetime.datetime.utcnow()
    beam = create_beam(start=start, completed=False)
    assert beam.end is None
    beam.set_completed(True)
    db_session.commit()
    assert beam.end is not None
    beam.set_completed(False)
    db_session.commit()
    assert beam.end is None


