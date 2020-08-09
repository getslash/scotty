import datetime
import os
import stat

import pytest
from flask import current_app

from flask_app.models import Beam, BeamType, Pin
from flask_app.tasks import beam_up, delete_beam, vacuum
from flask_app.utils.remote_combadge import _COMBADGE_UUID_PART_LENGTH
from flask_app.utils.remote_host import RemoteHost

_TEMPDIR_COMMAND = RemoteHost._TEMPDIR_COMMAND


def is_vacuumed(db_session, beam):
    beam = db_session.query(Beam).filter_by(id=beam.id).one_or_none()
    if beam is None:
        raise RuntimeError(f"Beam {beam.id} not found")
    return beam.deleted


def test_completed_beam_past_date_should_be_vacuumed(
    eager_celery, db_session, create_beam, expired_beam_date
):
    beam = create_beam(start=expired_beam_date, completed=True)
    vacuum.delay()
    assert is_vacuumed(db_session, beam)


def test_beam_before_date_should_not_be_vacuumed(
    eager_celery, db_session, create_beam, now
):
    beam = create_beam(start=now, completed=True)
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_not_completed_beam_past_date_should_be_vacuumed(
    eager_celery, db_session, create_beam, expired_beam_date
):
    beam = create_beam(start=expired_beam_date, completed=False)
    vacuum.delay()
    assert is_vacuumed(db_session, beam)


def test_not_completed_beam_before_date_should_not_be_vacuumed(
    eager_celery, db_session, create_beam, now
):
    beam = create_beam(start=now, completed=False)
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_beam_with_open_issues_should_not_be_vacuumed(
    eager_celery, db_session, create_beam, expired_beam_date, issue
):
    beam = create_beam(start=expired_beam_date, completed=True)
    beam.issues.append(issue)
    db_session.commit()
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_pinned_beam_should_not_be_vacuumed(
    eager_celery, db_session, create_beam, expired_beam_date, user
):
    beam = create_beam(start=expired_beam_date, completed=True)
    pin = Pin(user_id=user.id, beam_id=beam.id)
    db_session.add(pin)
    db_session.commit()
    vacuum.delay()
    assert not is_vacuumed(db_session, beam)


def test_beam_without_file_should_be_vacuumed(
    eager_celery, db_session, create_beam, expired_beam_date
):
    beam = create_beam(start=expired_beam_date, completed=True, add_file=False)
    db_session.commit()
    vacuum.delay()
    assert is_vacuumed(db_session, beam)


def test_beam_with_beam_type_greater_threshold_is_not_vacuumed(
    eager_celery, db_session, create_beam, expired_beam_date, vacuum_threshold
):
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


def test_beam_with_beam_type_smaller_threshold_is_vacuumed(
    eager_celery, db_session, create_beam, now
):
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


@pytest.mark.parametrize("os_type", ["linux", "windows"])
def test_beam_up(
    db_session,
    now,
    create_beam,
    eager_celery,
    monkeypatch,
    mock_ssh_client,
    mock_sftp_client,
    mock_rsa_key,
    uuid4,
    os_type,
    combadge_assets_dir,
):
    beam = create_beam(start=now, completed=False)
    if os_type == "windows":
        beam.host = "mock-windows-host"
        db_session.commit()
    result = beam_up.delay(
        beam_id=beam.id,
        host=beam.host,
        directory=beam.directory,
        username="root",
        auth_method="stored_key",
        pkey="mock-pkey",
        password=None,
        combadge_version="v2",
    )
    assert result.successful(), result.traceback
    beam = db_session.query(Beam).filter_by(id=beam.id).one()
    assert beam.error is None
    assert len(mock_ssh_client.instances) == 1
    uuid_part = uuid4.hex[:_COMBADGE_UUID_PART_LENGTH]
    ext = ".exe" if os_type == "windows" else ""
    remote_dir = (
        fr"C:\Users\root\AppData\Local\Temp" if os_type == "windows" else "/tmp"
    )
    sep = "\\" if os_type == "windows" else "/"
    combadge = f"{remote_dir}{sep}combadge_{uuid_part}{ext}"
    assert mock_ssh_client.instances[0].commands == [
        "uname",
        _TEMPDIR_COMMAND,
        f"{combadge} -b {beam.id} -p {beam.directory} -t scotty",
    ]
    assert len(mock_sftp_client.instances) == 1
    expected_calls = [
        {
            "action": "put",
            "args": {
                "local": f"{combadge_assets_dir}/v2/combadge_{os_type}/combadge{ext}",
                "remote": combadge,
            },
        },
    ]
    if os_type == "linux":
        expected_calls.append(
            {"action": "chmod", "args": {"remote": combadge, "mode": stat.S_IEXEC,},}
        )
    expected_calls.append({"action": "remove", "args": {"remote": combadge}})

    mock_sftp_client.get_one_instance_or_raise().assert_calls_equal_to(expected_calls)
    assert mock_sftp_client.files == {}
    assert len(mock_sftp_client.trash) == 1
    assert mock_sftp_client.trash[0] == combadge


def test_delete_beam(eager_celery, beam_with_real_file):
    beam = beam_with_real_file
    full_file_location = os.path.join(
        current_app.config["STORAGE_PATH"], beam.files[0].storage_name
    )
    assert os.path.exists(full_file_location)
    assert not beam.deleted
    delete_beam.delay(beam.id)
    assert not os.path.exists(full_file_location)
    assert beam.deleted
