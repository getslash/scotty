import os

from flask import current_app


def test_delete_beam(client, eager_celery, storage_path, beam_with_real_file):
    client.delete(f"/beams/{beam_with_real_file.id}")
    response = client.get(f"/beams/{beam_with_real_file.id}")
    assert response.json["beam"]["deleted"]
    assert not os.path.exists(
        os.path.join(
            current_app.config["STORAGE_PATH"],
            beam_with_real_file.files[0].storage_name,
        )
    )


def test_filter_beams_by_issue(client, create_beam, issue, db_session):
    beam = create_beam()
    beam.issues.append(issue)
    db_session.commit()
    response = client.get(f"/beams?issue={issue.id_in_tracker}")
    beams = response.json["beams"]
    assert len(beams) == 1
    assert beams[0]["id"] == beam.id
