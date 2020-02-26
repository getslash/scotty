import datetime

from flask_app.models import Beam, Pin, BeamType
from flask_app.tasks import vacuum


def is_vacuumed(db_session, beam):
    beam = db_session.query(Beam).filter_by(id=beam.id).one_or_none()
    if beam is None:
        raise RuntimeError(f"Beam {beam.id} not found")
    return beam.deleted


def test_completed_beam_past_date_should_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date):
    beam = create_beam(start=expired_beam_date, completed=True)
    vacuum.delay()
    assert is_vacuumed(db_session, beam)


def test_beam_before_date_should_not_be_vacuumed(eager_celery, db_session, create_beam, now):
    beam = create_beam(start=now, completed=True)
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_not_completed_beam_should_not_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date):
    beam = create_beam(start=expired_beam_date, completed=False)
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_beam_with_open_issues_should_not_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date, issue):
    beam = create_beam(start=expired_beam_date, completed=True)
    beam.issues.append(issue)
    db_session.commit()
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_pinned_beam_should_not_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date, user):
    beam = create_beam(start=expired_beam_date, completed=True)
    pin = Pin(user_id=user.id, beam_id=beam.id)
    db_session.add(pin)
    db_session.commit()
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_beam_without_file_should_be_vacuumed(eager_celery, db_session, create_beam, expired_beam_date):
    beam = create_beam(start=expired_beam_date, completed=True, add_file=False)
    db_session.commit()
    vacuum.delay()
    assert is_vacuumed(db_session, beam)


def test_beam_with_beam_type_greater_threshold_is_not_vacuumed(eager_celery, db_session, create_beam, expired_beam_date, vacuum_threshold):
    # threshold       default threshold                 now
    #   |    10 days        |            60 days         |
    # -----------------------------------------------------> date
    #         |
    #        beam
    #
    # beam is before the default threshold (60 days) so it should usually be vacuumed
    # but here we increase the threshold by 10 more days (vacuum_threshold=vacuum_threshold + 10)
    # and therefore the beam is *within* the threshold and will *not* be vacuumed
    beam = create_beam(start=expired_beam_date, completed=True)
    beam_type = BeamType(name="beam_type_1", vacuum_threshold=vacuum_threshold + 10)
    db_session.add(beam_type)
    beam.type = beam_type
    db_session.commit()
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_beam_with_beam_type_smaller_threshold_is_vacuumed(eager_celery, db_session, create_beam, now):
    # default threshold                threshold      now
    # |  59 days                        |   1 day      |
    # --------------------------------------------------> date
    #                           |
    #                         beam
    #
    # beam is within the default threshold (60 days) so it should usually *not* be vacuumed
    # but here we make the threshold 1 day (vacuum_threshold=1)
    # and therefore the beam is outside the threshold and *should* be vacuumed
    vacuum_threshold = 1
    beam = create_beam(start=now - datetime.timedelta(days=2), completed=True)
    beam_type = BeamType(name="beam_type_1", vacuum_threshold=vacuum_threshold)
    db_session.add(beam_type)
    beam.type = beam_type
    db_session.commit()
    vacuum.delay()
    assert is_vacuumed(db_session, beam)
