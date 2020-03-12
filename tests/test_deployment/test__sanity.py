import gzip
import http.client
import os
import shutil
import subprocess

import pytest
from requests.exceptions import HTTPError


def test_sanity(scotty):
    scotty.sanity_check()

@pytest.mark.parametrize("combadge_version", ['v1', 'v2'])
def test_forbid_root_beam(scotty, combadge_version):
    with pytest.raises(HTTPError) as e:
        scotty.beam_up("/", combadge_version=combadge_version)

    assert e._excinfo[1].response.status_code == http.client.CONFLICT


def test_independent_beam(beam, local_beam_dir, download_dir):
    for file_ in beam.beam.iter_files():
        file_.download(download_dir)

    assert beam.beam.completed

    for subdir, _, files in os.walk(download_dir):
        for downloaded_file in files:
            file_name, file_extension = os.path.splitext(downloaded_file)
            if file_extension != '.gz':
                continue

            compressed_path = os.path.join(subdir, downloaded_file)
            non_compressed_path = os.path.join(subdir, file_name)
            with gzip.open(compressed_path, 'rb') as f_in:
                with open(non_compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            subprocess.check_call(['rm', compressed_path])

    subprocess.check_call(['diff', '-rq', local_beam_dir, download_dir])


def test_filter_by_tag(scotty, short_beam):
    scotty.add_tag(short_beam.beam.id, 'dummy_tag')
    beams = scotty.get_beams_by_tag('dummy_tag')
    assert len(beams) == 1
    assert beams[0].id == short_beam.beam.id

    scotty.remove_tag(short_beam.beam.id, 'dummy_tag')
    beams = scotty.get_beams_by_tag('dummy_tag')
    assert not beams
