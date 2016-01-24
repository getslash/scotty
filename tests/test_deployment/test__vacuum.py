from datetime import timedelta
import slash

_DAY = timedelta(days=1)

@slash.parameters.toggle('pin')
def test_default_vacuum(scotty, typed_beam, server_config, pin):
    beam, beam_type = typed_beam
    vacuum_threshold = server_config['VACUUM_THRESHOLD'] if not beam_type else beam_type.threshold

    if pin:
        scotty.pin(beam, True)

    assert beam.purge_time == vacuum_threshold
    for i in range(vacuum_threshold - 1):
        scotty.sleep(_DAY)
        beam.update()
        assert beam.purge_time == vacuum_threshold - i - 1
        scotty.check_beam_state(beam, False)

    scotty.sleep(_DAY)
    beam.update()
    assert beam.purge_time == 0

    if pin:
        scotty.check_beam_state(beam, False)
        scotty.pin(beam, False)
        scotty.sleep(timedelta(seconds=0))
        beam.update()

    scotty.check_beam_state(beam, True)
