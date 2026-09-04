EXACT, LOWER, UPPER = 0, 1, 2

class Entry:
    __slots__ = ("key", "depth", "score", "flag", "move")

    def __init__(self, key, depth, score, flag, move):
        self.key = key
        self.depth = depth
        self.score = score
        self.flag = flag
        self.move = move

class TranspositionTable:
    DEFAULT_SIZE_MB = 64
    BYTES_PER_ENTRY = 200 # its a python object not a 16 byte structure so

    def __init__(self, size_mb=DEFAULT_SIZE_MB):
        self.resize(size_mb)

    def resize(self, size_mb):
        self.size = max(1024, int(size_mb) * 1024 * 1024 // self.BYTES_PER_ENTRY)
        self.table = [None] * self.size

    def clear(self):
        self.table = [None] * self.size

    def get(self, key):
        entry = self.table[key % self.size]
        return entry if entry is not None and entry.key == key else None

    def put(self, key, depth, score, flag, move):
        index = key % self.size
        entry = self.table[index]
        #deeper searched result should be overwritten or if it is more shallow, keep the deeper
        if entry is None or entry.key != key or depth >= entry.depth:
            self.table[index] = Entry(key, depth, score, flag, move)