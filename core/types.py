# bitboard constants
DIAG_A1H8 = 0x8040201008040201
DIAG_H1A8 = 0x0102040810204080
FILE_A = 0x0101010101010101
FILE_H = 0x8080808080808080
RANK_1 = 0x00000000000000FF
RANK_2 = 0x000000000000FF00
RANK_7 = 0x00FF000000000000
RANK_8 = 0xFF00000000000000
LIGHT = 0x55AA55AA55AA55AA
DARK = 0xAA55AA55AA55AA55

# attacks constants
#FILE_A = 0x0101010101010101 # already used
FILE_B = 0x0202020202020202
FILE_G = 0x4040404040404040
#FILE_H = 0x8080808080808080 # already used

NOT_A  = ~FILE_A  & 0xFFFFFFFFFFFFFFFF
NOT_B  = ~FILE_B  & 0xFFFFFFFFFFFFFFFF
NOT_G  = ~FILE_G  & 0xFFFFFFFFFFFFFFFF
NOT_H  = ~FILE_H  & 0xFFFFFFFFFFFFFFFF
NOT_AB = ~(FILE_A | FILE_B) & 0xFFFFFFFFFFFFFFFF
NOT_GH = ~(FILE_G | FILE_H) & 0xFFFFFFFFFFFFFFFF


# sides
WHITE = 0
BLACK = 1

# squares
A1, B1, C1, D1, E1, F1, G1, H1, A2, B2, C2, D2, E2, F2, G2, H2, A3, B3, C3, D3, E3, F3, G3, H3, A4, B4, C4, D4, E4, F4, G4, H4, A5, B5, C5, D5, E5, F5, G5, H5, A6, B6, C6, D6, E6, F6, G6, H6, A7, B7, C7, D7, E7, F7, G7, H7, A8, B8, C8, D8, E8, F8, G8, H8 = range(64)

# files
FILES = "abcdefgh"

PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = range(6)

# pieces
WP, WN, WB, WR, WQ, WK = range(6)
BP, BN, BB, BR, BQ, BK = range(6, 12)

NO_PIECE = -1

# move flags (half of them are gone because im using bitflags for moves)
CAPTURE = 1 << 0
DOUBLE_PAWN_PUSH = 1 << 1
EN_PASSANT = 1 << 2
CASTLE = 1 << 3

"""
QUIET = 0
CAPTURE = 1 << 0
DOUBLE_PAWN_PUSH = 1 << 1
EN_PASSANT = 1 << 2
KING_CASTLE = 1 << 3
QUEEN_CASTLE = 1 << 4
PROMOTION = 1 << 5
IN_CHECK = 1 << 6
"""

# promotion flags
PROMO_NONE = 0
PROMO_KNIGHT = 1
PROMO_BISHOP = 2
PROMO_ROOK = 3
PROMO_QUEEN = 4

# position castling flags
WK_CASTLE = 1 << 0 # 1
WQ_CASTLE = 1 << 1 # 2 
BK_CASTLE = 1 << 2 # 4
BQ_CASTLE = 1 << 3 # 8

# castling masks
CASTLING_MASKS = [15] * 64 # 15 is default castling rights (1+2+4+8)

# intial white squares
CASTLING_MASKS[7]  = 13  # h1 clears White King side (15 & ~1)
CASTLING_MASKS[0]  = 11  # a1 clears White Queen side (15 & ~2)
CASTLING_MASKS[4]  = 12  # e1 clears all White rights (15 & ~3)

# intial black squares
CASTLING_MASKS[63] = 11   # h8 clears Black King side (15 & ~8)
CASTLING_MASKS[56] = 14  # a8 clears Black Queen side (15 & ~1)


# i=0: WK, i=1: WQ, i=2: BK, i=3: BQ
# bit 1 (1<<0) = WK, bit 2 (1<<1) = WQ, bit 4 (1<<2) = BK, bit 8 (1<<3) = BQ

CASTLING_MASKS[7]  = ~1 & 15  # h1 clears White King
CASTLING_MASKS[0]  = ~2 & 15  # a1 clears White Queen
CASTLING_MASKS[4]  = ~3 & 15  # e1 clears White King & Queen

CASTLING_MASKS[63] = ~4 & 15  # h8 clears Black King
CASTLING_MASKS[56] = ~8 & 15  # a8 clears Black Queen
CASTLING_MASKS[60] = ~12 & 15 # e8 clears Black King & Queen