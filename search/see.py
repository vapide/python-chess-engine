# if i keep recapturing how much material do i win or lose
# see (Static Exchange Evaluation)

from core import tables, types
from core.bitboard import Bitboard
from movegen.move_generator import MoveGenerator

VALUE = [tables.PIECE_VALUES[piece] for piece in range(5)] + 10000

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

    occ = pos.all_occ & ~(1 << from_sq)
    # flags
    # promotion
    # loop attackers
    #walk back
    pass
