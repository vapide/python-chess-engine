from core import tables, types
from movegen.move_generator import MoveGenerator

AGG = 3 # aggression move scoring

KING_ZONE = []
for _square in range(64):
    _zone = tables.KING_ATTACKS[_square] | (1 << _square)
    _zone |= (_zone << 8) & 0xFFFFFFFFFFFFFFFF # mask
    _zone |= (_zone >> 8) # no mask due to shift direction
    KING_ZONE.append(_zone)

def aggression_score(pos, move): 
    # 0 quiet move through 8 check that goes next to the king
    to_sq = (move >> 6) & 0x3F
    flags = (move >> 12) & 0xF
    promotion = (move >> 16) & 0xF

    score = 0
    if MoveGenerator.gives_check(pos, move):
        score += 3
    if (1 << to_sq) & KING_ZONE[pos.king_square(pos.side_to_move ^ 1)]:
        score += 2
        if flags & (types.CAPTURE | types.EN_PASSANT):
            score += 1                      # removing a defender of the king
    if promotion == types.PROMO_QUEEN:
        score += 2
    return score
