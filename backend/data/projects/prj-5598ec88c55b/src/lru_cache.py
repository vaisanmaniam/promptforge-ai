class LRUCache:
    # Implements REQ-001
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}
    def get(self, key):
        return self.cache.get(key)
    def put(self, key, value):
        self.cache[key] = value
