from cache import SafeCache

def test_missing_key():
    c = SafeCache()
    assert c.fetch("missing") is None
