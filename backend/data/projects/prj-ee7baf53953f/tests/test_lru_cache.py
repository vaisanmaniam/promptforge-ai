from src.lru_cache import LRUCache
def test_req_001_cache_operations():
    c = LRUCache(2)
    c.put('a', 1)
    assert c.get('a') == 1
