import subprocess


def test_sanity(scotty):
    scotty.sanity_check()


def test_independent_beam(beam, local_beam_dir, download_dir):
    for file_ in beam.beam.iter_files():
        file_.download(download_dir)

    subprocess.check_call(['diff', '-rq', local_beam_dir, download_dir])
