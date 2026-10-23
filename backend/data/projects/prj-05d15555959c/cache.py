class SafeCache:
    def __init__(self):
        self.cache = {}
    def fetch(self, key):
        return self.cache[key]
