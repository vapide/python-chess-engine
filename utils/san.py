from core import types
from core.move import (get_from, get_to, get_flags, get_promotion, square_name)
from movegen.move_generator import MoveGenerator


PIECE_SYMBOLS = {
    types.PAWN: "",
    types.KNIGHT: "N",
    types.BISHOP: "B",
    types.ROOK: "R",
    types.QUEEN: "Q",
    types.KING: "K",
}


PROMOTION_SYMBOLS = {
    types.PROMO_KNIGHT: "N",
    types.PROMO_BISHOP: "B",
    types.PROMO_ROOK: "R",
    types.PROMO_QUEEN: "Q",
}


def piece_type(piece):
    return piece % 6


def is_capture(pos, move):
    flags = get_flags(move)
    if flags & types.CAPTURE:
        return True
    if flags & types.EN_PASSANT:
        return True
    return pos.piece_at(get_to(move)) is not None

def is_capture(pos, move):
    to_sq = (move >> 6) & 0x3F
    if pos.piece_at(to_sq):
        return True

    flags = (move >> 12) & 0xF
    if flags & types.EN_PASSANT:
        return True

    return False

def square_name(square):
    file = square % 8
    rank = square // 8

    return (chr(ord("a") + file) + str(rank + 1))

def disambiguation(pos, move, ptype):
    from_sq = get_from(move)
    to_sq = get_to(move)
    conflicts = []

    for other in MoveGenerator.generate_legal_moves(pos):
        if other == move:
            continue

        other_from = get_from(other)
        other_to = get_to(other)

        if other_to != to_sq:
            continue

        piece = pos.piece_at(other_from)

        if piece is None:
            continue
        if piece_type(piece) == ptype:
            conflicts.append(other_from)

    if not conflicts:
        return ""

    same_file = any(sq % 8 == from_sq % 8 for sq in conflicts)
    same_rank = any(sq // 8 == from_sq // 8 for sq in conflicts)

    if not same_file:
        return types.FILES[from_sq % 8]
    if not same_rank:
        return str(from_sq // 8 + 1)

    return (types.FILES[from_sq % 8] + str(from_sq // 8 + 1))
    
def add_check_suffix(pos, move, san):
    pos.make_move(move)
    enemy = pos.side_to_move

    if MoveGenerator.in_check(pos, enemy):
        legal = MoveGenerator.generate_legal_moves(pos)
        if len(legal) == 0:
            san += "#"
        else:
            san += "+"

    pos.unmake_move()
    return san

def move_to_san(pos, move):
    from_sq = get_from(move)
    to_sq = get_to(move)
    flags = get_flags(move)
    promotion = get_promotion(move)
    piece = pos.piece_at(from_sq)

    if piece is None:
        raise ValueError(f"No piece on {square_name(from_sq)}")

    ptype = piece_type(piece)

    if flags & types.CASTLE:
        if to_sq > from_sq:
            san = "O-O"
        else:
            san = "O-O-O"

        return add_check_suffix(pos, move, san)

    capture = is_capture(pos, move )

    san = ""
    san += PIECE_SYMBOLS[ptype]

    if ptype == types.PAWN and capture:
        san += types.FILES[from_sq % 8]

    if ptype != types.PAWN:
        san += disambiguation(pos, move, ptype)

    if capture:
        san += "x"

    san += square_name(to_sq)

    if promotion:
        san += "="
        san += PROMOTION_SYMBOLS[promotion]

    return add_check_suffix(pos, move, san)