from utils.rkiss import RKISS
from core import types
from core.bitboard import Bitboard

SIDE_KEY = 768
CASTLING_START = 769
EP_START = 773

class Zobrist:
    def __init__(self, seed=67676767):
        self.hash = 0
        self.pawn_hash = 0
        self.non_pawn_hash = [0, 0]  # indexed by types.WHITE / types.BLACK
        r = RKISS(seed)
        self.keys = [r.rand64() for _ in range(781)]

    def toggle_piece(self, piece, square):
        key = self.keys[piece * 64 + square]
        self.hash ^= key

        if piece % 6 == types.PAWN:
            self.pawn_hash ^= key
        else:
            color = types.WHITE if piece < 6 else types.BLACK
            self.non_pawn_hash[color] ^= key

    def toggle_castling(self, rights):
        self.hash ^= self.keys[CASTLING_START + rights]

    def toggle_ep(self, square):
        if square != -1:
            self.hash ^= self.keys[EP_START + square % 8]

    def flip_side(self):
        self.hash ^= self.keys[SIDE_KEY]

    def compute(self, position):
        h = 0
        pawn_h = 0
        non_pawn_h = [0, 0]

        for piece in range(12):
            bb = position.pieces[piece]
            while bb:
                sq, bb = Bitboard.pop_lsb(bb)
                key = self.keys[piece * 64 + sq]
                h ^= key
                if piece % 6 == types.PAWN:
                    pawn_h ^= key
                else:
                    color = types.WHITE if piece < 6 else types.BLACK
                    non_pawn_h[color] ^= key

        if position.side_to_move == types.BLACK:
            h ^= self.keys[SIDE_KEY]

        for i in range(4):
            if position.castling_rights & (1 << i):
                h ^= self.keys[CASTLING_START + i]

        if position.ep_square != -1:
            h ^= self.keys[EP_START + position.ep_square % 8]

        self.pawn_hash = pawn_h
        self.non_pawn_hash = non_pawn_h

        return h