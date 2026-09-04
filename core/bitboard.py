import core.types

class Bitboard:
    def __init__(self, bitboard: int):
        self.bitboard = bitboard
    
    def getBitboard(self) -> int:
        return self.bitboard

    def setBitboard(self, bitboard: int):
        self.bitboard = bitboard

    def getBitInPos(self, pos: int) -> int:
        return 1 if ((self.bitboard >> pos) & 1) == 1 else 0
    
    def setBit(self, pos: int):
        self.bitboard |= (1 << pos)

    def clearBit(self, pos: int):
        self.bitboard &= ~(1 << pos)

    #  noWe         nort         noEa
    #          +7    +8    +9
    #              \  |  /
    #  west    -1 <-  0 -> +1    east
    #              /  |  \
    #          -9    -8    -7
    #  soWe         sout         soEa

    def northOne(self):
        return (self.bitboard << 8) & 0xFFFFFFFFFFFFFFFF
    
    def southOne(self):
        return (self.bitboard >> 8) & 0xFFFFFFFFFFFFFFFF
    
    def westOne(self):
        return (self.bitboard >> 1) & ~core.types.FILE_H
    
    def eastOne(self):
        return (self.bitboard << 1) & ~core.types.FILE_A
    
    def northWestOne(self):
        return (self.bitboard << 7) & ~core.types.FILE_H
    
    def southEastOne(self):
        return (self.bitboard >> 7) & ~core.types.FILE_A
    
    def northEastOne(self):
        return (self.bitboard << 9) & ~core.types.FILE_A
    
    def southWestOne(self):
        return (self.bitboard >> 9) & ~core.types.FILE_H
    
    def setNorthOne(self):
        self.bitboard = (self.bitboard << 8) & 0xFFFFFFFFFFFFFFFF
    
    def setSouthOne(self):
        self.bitboard = (self.bitboard >> 8) & 0xFFFFFFFFFFFFFFFF
    
    def setWestOne(self):
        self.bitboard = (self.bitboard >> 1) & core.types.FILE_H
    
    def setEastOne(self):
        self.bitboard = (self.bitboard << 1) & ~core.types.FILE_A
    
    def setNorthWestOne(self):
        self.bitboard = (self.bitboard << 7) & ~core.types.FILE_H
    
    def setSouthEastOne(self):
        self.bitboard = (self.bitboard >> 7) & ~core.types.FILE_A
    
    def setNorthEastOne(self):
        self.bitboard = (self.bitboard << 9) & ~core.types.FILE_A
    
    def setSouthWestOne(self):
        self.bitboard = (self.bitboard >> 9) & ~core.types.FILE_H

    def bitswap(self):
        return int.from_bytes(self.bitboard.to_bytes(8, byteorder='little'), byteorder='big') # uses faster method

    @staticmethod
    def lsb(bb: int) -> int:
        return (bb & -bb).bit_length() - 1

    @staticmethod
    def pop_lsb(bb: int):
        lsb = bb & -bb
        square = lsb.bit_length() - 1
        bb &= bb - 1
        return square, bb
        
    #   EXAMPLE USAGE:
    #   bb = self.pieces[WP]
    #   while bb:
    #      sq, bb = Bitboard.pop_lsb(bb)      


    def prettyPrint(self): # prints backwards as we are using little endian rank file mapping
        print("  A B C D E F G H")
        for rank in range(7, -1, -1):
            line = f"{rank + 1} "
            for file in range(8):
                square = rank * 8 + file
                if (self.getBitboard() >> square) & 1:
                    line += "X "
                else:
                    line += ". "
            line += f"{rank + 1}"
            print(line)
        print("  A B C D E F G H\n")
