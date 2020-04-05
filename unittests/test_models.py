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
