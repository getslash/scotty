from datetime import timedelta

_DAY = timedelta(days=1)

def test_default_vacuum(scotty, beam, server_config):
    vacuum_threshold = server_config['VACUUM_THRESHOLD']
    assert beam.purge_time == vacuum_threshold
    for i in range(vacuum_threshold - 1):
        scotty.sleep(_DAY)
        beam.update()
        assert beam.purge_time == vacuum_threshold - i - 1
        assert not beam.deleted

    scotty.sleep(_DAY)
    beam.update()
    assert beam.purge_time == 0
    assert beam.deleted


def test_default_vacuum_pin(scotty, beam, server_config):
    vacuum_threshold = server_config['VACUUM_THRESHOLD']
    scotty.pin(beam, True)
    scotty.sleep(_DAY * vacuum_threshold * 2)
    beam.update()
    assert not beam.deleted
    scotty.pin(beam, False)
    scotty.sleep(timedelta(seconds=0))
    beam.update()
    assert beam.deleted
