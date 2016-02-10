import time
import subprocess
import http.client
import slash
from requests.exceptions import HTTPError

def test_sanity(scotty):
    scotty.sanity_check()


def test_forbid_root_beam(scotty):
    with slash.assert_raises(HTTPError) as e:
        scotty.beam_up("/")

    assert e.exception.response.status_code == http.client.CONFLICT


def test_independent_beam(beam, local_beam_dir, download_dir):
    for file_ in beam.beam.iter_files():
        file_.download(download_dir)

    assert beam.beam.completed

    subprocess.check_call(['diff', '-rq', local_beam_dir, download_dir])
