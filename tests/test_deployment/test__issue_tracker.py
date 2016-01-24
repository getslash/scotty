def test_issue_issue_creation(scotty, beam, issue):
    beam, _ = beam
    assert len(beam.associated_issues) == 0
    beam.set_issue_association(issue.id_in_scotty, True)
    beam.update()
    assert beam.associated_issues == [issue.id_in_scotty]
    beam.set_issue_association(issue.id_in_scotty, False)
    beam.update()
    assert len(beam.associated_issues) == 0
