from calculator import add, subtract

def test_add():
    # Verifies REQ-001
    assert add(2, 3) == 5

def test_subtract():
    assert subtract(5, 3) == 2
