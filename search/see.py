# if i keep recapturing how much material do i win or lose
# see (Static Exchange Evaluation)

from core import tables, types
from core.bitboard import Bitboard
from movegen.move_generator import MoveGenerator

VALUE = [tables.PIECE_VALUES[piece] for piece in range(5)] + [10000]

def _cheapest_attacker(pos, attackers, color):
    base = color * 6
    for piece_type in range(6):
        bb = pos.pieces[base + piece_type] & attackers
        if bb:
            return piece_type, Bitboard.lsb(bb)
    return -1, None

def see(pos, move):
    from_sq = move & 0x3F
    to_sq = (move >> 6) & 0x3F
    flags = (move >> 12) & 0xF
    promotion = (move >> 16) & 0xF

    us = pos.side_to_move
    moving = pos.mailbox[from_sq]
    if moving is None:
        return 0

    occupancy = pos.all_occ & ~(1 << from_sq)
    if flags & types.EN_PASSANT:
        occupancy &= ~(1 << (to_sq - 8 if us == types.WHITE else to_sq + 8))
        gained = VALUE[types.PAWN]
    else:
        victim = pos.mailbox[to_sq]
        gained = VALUE[victim % 6] if victim is not None else 0
    occupancy |= 1 << to_sq

    # swap piece before promotion
    if promotion:
        gained += VALUE[promotion] - VALUE[types.PAWN]
        on_square = VALUE[promotion]
    else:
        on_square = VALUE[moving % 6]

    gain = [gained]
    side = us ^ 1

    while True:
        attackers = MoveGenerator.attackers_to(pos, to_sq, side, occupancy) & occupancy
        if not attackers:
            break
        square, attacker = _cheapest_attacker(pos, attackers, side)
        if attacker is None:
            break
        # cant go into check
        if attacker == types.KING:
            rest = occupancy & ~(1 << square)
            if MoveGenerator.attackers_to(pos, to_sq, side ^ 1, rest) & rest:
                break

        gain.append(on_square - gain[-1])
        if max(-gain[-2], gain[-1]) < 0:
            break

        occupancy &= ~(1 << square)
        on_square = VALUE[attacker]
        side ^= 1

    # walk back 
    for i in range(len(gain) - 1, 0, -1):
        gain[i - 1] = -max(-gain[i - 1], gain[i])
    return gain[0]

