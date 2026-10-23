from validator import check_age

def test_boundary_age():
    # Verifies REQ-002
    assert check_age(18) is True
