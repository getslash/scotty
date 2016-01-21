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

