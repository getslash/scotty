from datetime import timedelta

_DAY = timedelta(days=1)

def test_default_vacuum(scotty, beam, server_config):
    vacuum_threshold = server_config['VACUUM_THRESHOLD']
    assert beam.purge_time == vacuum_threshold
    for i in range(vacuum_threshold - 1):
        scotty.sleep(_DAY)
        beam.update()
        assert beam.purge_time == vacuum_threshold - i - 1
        scotty.check_beam_state(beam, False)

    scotty.sleep(_DAY)
    beam.update()
    assert beam.purge_time == 0
    scotty.check_beam_state(beam, True)


def test_default_vacuum_pin(scotty, beam, server_config):
    vacuum_threshold = server_config['VACUUM_THRESHOLD']
    scotty.pin(beam, True)
    scotty.sleep(_DAY * vacuum_threshold * 2)
    beam.update()
    scotty.check_beam_state(beam, False)
    scotty.pin(beam, False)
    scotty.sleep(timedelta(seconds=0))
    beam.update()
    scotty.check_beam_state(beam, True)
