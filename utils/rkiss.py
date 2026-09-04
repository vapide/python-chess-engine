class RKISS:
    def __init__(self, seed: int = 1):
        self._MASK64 = 0xFFFFFFFFFFFFFFFF
        self.setSeed(seed)

    def setSeed(self, seed: int):
        self.a = 0xF1EA5EED
        self.b = self.c = self.d = seed & self._MASK64
        for _ in range(20):
            self.rand64()

    def rand64(self) -> int:
        e = (self.a - self._rotate_left(self.b, 7)) & self._MASK64
        self.a = (self.b ^ self._rotate_left(self.c, 13)) & self._MASK64
        self.b = (self.c + self._rotate_left(self.d, 37)) & self._MASK64
        self.c = (self.d + e) & self._MASK64
        self.d = (e + self.a) & self._MASK64
        return self.d

    def _rotate_left(self, val: int, shift: int) -> int:
        return ((val << shift) | (val >> (64 - shift))) & self._MASK64
    
    def rand64_sparse(self) -> int:
        return self.rand64() & self.rand64() & self.rand64()