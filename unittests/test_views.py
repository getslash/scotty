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
