import enum
from datetime import timedelta
import slash

_DAY = timedelta(days=1)

class IssueHandling(enum.Enum):
    none = 1  # Do not assign an issue to the beam
    close = 2  # Assign an issue to the beam and close it
    unassign = 3  # Assign an issue to the beam and then unassign it


@slash.parameters.toggle('should_pin')
@slash.parametrize('issue_handling', iter(IssueHandling))
def test_default_vacuum(scotty, typed_beam, server_config, should_pin, issue, issue_handling):
    beam, beam_type = typed_beam
    vacuum_threshold = server_config['VACUUM_THRESHOLD'] if not beam_type else beam_type.threshold

    if should_pin:
        scotty.pin(beam, True)

    if issue_handling is not IssueHandling.none:
        beam.set_issue_association(issue.id_in_scotty, True)

    beam.update()

    pin_active = should_pin
    issue_active = issue_handling is not IssueHandling.none

    def should_vaccuum():
        return not pin_active and not issue_active

    assert beam.purge_time == (vacuum_threshold if should_vaccuum() else None)
    for i in range(vacuum_threshold - 1):
        scotty.sleep(_DAY)
        beam.update()
        assert beam.purge_time == (vacuum_threshold - i - 1 if should_vaccuum() else None)
        scotty.check_beam_state(beam, False)

    scotty.sleep(_DAY)
    beam.update()
    assert beam.purge_time == (0 if should_vaccuum() else None)


    if pin_active:
        scotty.check_beam_state(beam, should_vaccuum())
        scotty.pin(beam, False)
        scotty.sleep(timedelta(seconds=0))
        beam.update()
        pin_active = False
        scotty.check_beam_state(beam, should_vaccuum())

    if issue_active:
        scotty.check_beam_state(beam, should_vaccuum())
        if issue_handling is IssueHandling.close:
            issue.set_state(False)
        elif issue_handling is IssueHandling.unassign:
            beam.set_issue_association(issue.id_in_scotty, False)
        else:
            raise AssertionError()

        issue_active = False

        scotty.sleep(timedelta(seconds=0))
        beam.update()
        scotty.check_beam_state(beam, should_vaccuum())

    scotty.check_beam_state(beam, should_vaccuum())
