from core.move import encode_move, to_uci
from core.bitboard import Bitboard
from core import types

from core.bitboard import Bitboard
import core.move as move
import core.tables as tables

from utils import magics

def knightAttacksMask(square: int):
    b = 1 << square
    attacks = 0

    attacks |= (b & types.NOT_H) << 17
    attacks |= (b & types.NOT_A) << 15

    attacks |= (b & types.NOT_GH) << 10
    attacks |= (b & types.NOT_AB) << 6


    attacks |= (b & types.NOT_H) >> 15
    attacks |= (b & types.NOT_A) >> 17

    attacks |= (b & types.NOT_GH) >> 6
    attacks |= (b & types.NOT_AB) >> 10

    return attacks & 0xFFFFFFFFFFFFFFFF


def kingAttacksMask(square: int) -> int: # need is square attacked function in position class but first we should iomplement attacks
    b = 1 << square

    attacks = 0

    attacks |= (b << 8)
    attacks |= (b >> 8)

    attacks |= (b << 1) & types.NOT_A
    attacks |= (b >> 1) & types.NOT_H

    attacks |= (b << 9) & types.NOT_A
    attacks |= (b << 7) & types.NOT_H

    attacks |= (b >> 9) & types.NOT_H
    attacks |= (b >> 7) & types.NOT_A

    return attacks & 0xFFFFFFFFFFFFFFFF

def pawnAttacksMask(square: int, color: int) -> int: # 0 for white, 1 for black
    b = 1 << square

    attacks = 0

    if color == 0:  # white
        attacks |= (b << 7) & types.NOT_H
        attacks |= (b << 9) & types.NOT_A
    elif color == 1:  # black
        attacks |= (b >> 7) & types.NOT_A
        attacks |= (b >> 9) & types.NOT_H
    else:
        raise ValueError(f"Invalid color: {color}")
    
    return attacks & 0xFFFFFFFFFFFFFFFF

def get_knight_attacks(square: int) -> int:
    return tables.KNIGHT_ATTACKS[square]

def get_rook_attacks(square: int, occupancy: int) -> int:
    return magics.get_rook_attacks(square, occupancy)

def get_bishop_attacks(square: int, occupancy: int) -> int:
    return magics.get_bishop_attacks(square, occupancy)

def get_queen_attacks(square: int,  occupancy: int) -> int:
    return get_rook_attacks(square, occupancy) | get_bishop_attacks(square, occupancy)


def get_king_attacks(square: int) -> int:
    return tables.KING_ATTACKS[square]


def get_pawn_attacks(square: int, color: int) -> int:
    return tables.WHITE_PAWN_ATTACKS[square] if color == 0 else tables.BLACK_PAWN_ATTACKS[square]

""" # precoded tables that will be in tables.py
# knight attacks table
KNIGHT_ATTACKS = [0] * 64

for square in range(64):
    KNIGHT_ATTACKS[square] = knightAttacksMask(square)

# king attacks table
KING_ATTACKS = [0] * 64

for square in range(64):
    KING_ATTACKS[square] = kingAttacksMask(square)

# pawn attack tables
WHITE_PAWN_ATTACKS = [0] * 64
BLACK_PAWN_ATTACKS = [0] * 64

for square in range(64):
    WHITE_PAWN_ATTACKS[square] = pawnAttacksMask(square, 0)
    BLACK_PAWN_ATTACKS[square] = pawnAttacksMask(square, 1)

print(KNIGHT_ATTACKS)
print(KING_ATTACKS)
print(WHITE_PAWN_ATTACKS)
print(BLACK_PAWN_ATTACKS)

"""





# add checks for attacking own pieces and legality

class MoveGenerator:

    @staticmethod
    def attackers_to(pos, square, color):
        attackers = 0
        occupancy = pos.all_occ

        # pawns
        if color == types.WHITE:
            attackers |= (get_pawn_attacks(square, types.BLACK) & pos.pieces[types.WP])
        else:
            attackers |= (get_pawn_attacks(square, types.WHITE) & pos.pieces[types.BP])


        # knights
        attackers |= (get_knight_attacks(square) & pos.pieces[color * 6 + types.WN])

        # bishops and queens
        diagonal_attackers = (get_bishop_attacks(square, occupancy))

        attackers |= (diagonal_attackers & (pos.pieces[color * 6 + types.WB] | pos.pieces[color * 6 + types.WQ]))

        # rooks and queens
        straight_attackers = (get_rook_attacks(square, occupancy))

        attackers |= (straight_attackers & (pos.pieces[color * 6 + types.WR] | pos.pieces[color * 6 + types.WQ]))

        # kings
        attackers |= (get_king_attacks(square) & pos.pieces[color * 6 + types.WK])
        
        return attackers

    @staticmethod
    def generate_pseudo_legal_moves(pos) -> list[int]:
        moves = []
        side = pos.side_to_move
        occ = pos.all_occ
        if side == types.WHITE:
            own_occ = pos.white_occ
            enemy_occ = pos.black_occ
            #enemy_king_bb = pos.pieces[types.BK]
            pieces = range(0, 6)
        else:
            own_occ = pos.black_occ
            enemy_occ = pos.white_occ
            #enemy_king_bb = pos.pieces[types.WK]
            pieces = range(6, 12)

        for piece in pieces:
            bb = pos.pieces[piece]
            while bb:
                from_sq, bb = Bitboard.pop_lsb(bb)
                targets = 0
                flags = 0
                if piece in (types.WP, types.BP):
                    color = (types.WHITE if piece < 6 else types.BLACK)

                    if color == types.WHITE:
                        one_step = from_sq + 8
                        two_step = from_sq + 16
                        
                        if one_step < 64 and not (pos.all_occ & (1 << one_step)):
                            # if 8th rank only append promotions not regular moves
                            if one_step // 8 == 7:  
                                for promo in [types.PROMO_QUEEN, types.PROMO_ROOK, types.PROMO_BISHOP, types.PROMO_KNIGHT]:
                                    moves.append(encode_move(from_sq, one_step, promotion=promo))
                                    #print(to_uci(from_sq), to_uci(one_step), promo)
                            else:  
                                # 1 step
                                moves.append(encode_move(from_sq, one_step, flags=0))
                                # 2 step
                                if from_sq // 8 == 1 and not (pos.all_occ & (1 << two_step)):
                                    moves.append(encode_move(from_sq, two_step, flags=types.DOUBLE_PAWN_PUSH))
                                    #print(to_uci(from_sq), to_uci(two_step), "double pawn push")

                    # bp
                    else:
                        one_step = from_sq - 8
                        two_step = from_sq - 16
                        
                        if one_step >= 0 and not (pos.all_occ & (1 << one_step)):
                            # 1st rank same thing
                            if one_step // 8 == 0:  
                                for promo in [types.PROMO_QUEEN, types.PROMO_ROOK, types.PROMO_BISHOP, types.PROMO_KNIGHT]:
                                    moves.append(encode_move(from_sq, one_step, promotion=promo))
                                    #print(to_uci(from_sq), to_uci(one_step), promo)
                            else:  
                                # 1 step
                                moves.append(encode_move(from_sq, one_step))
                                #print(to_uci(from_sq), to_uci(one_step), "1 step")
                                # 2 step from rank 7
                                if from_sq // 8 == 6 and not (pos.all_occ & (1 << two_step)):
                                    moves.append(encode_move(from_sq, two_step, flags=types.DOUBLE_PAWN_PUSH))
                                    #print(to_uci(from_sq), to_uci(two_step), "double pawn push")


                    # --- diag captures ---
                    cap_targets = (get_pawn_attacks(from_sq, color) & enemy_occ)
                    while cap_targets:
                        to_sq, cap_targets = Bitboard.pop_lsb(cap_targets)
                        is_promo_rank = (to_sq // 8 == 7 if color == types.WHITE else to_sq // 8 == 0)
                        
                        if is_promo_rank:
                            for promo in [types.PROMO_QUEEN, types.PROMO_ROOK, types.PROMO_BISHOP, types.PROMO_KNIGHT]:
                                moves.append(encode_move(from_sq, to_sq, promotion=promo, flags=types.CAPTURE))
                                #print(to_uci(from_sq), to_uci(to_sq), promo, "capture promotion")
                        else:
                            moves.append(encode_move(from_sq, to_sq, flags=types.CAPTURE))
                            #print(to_uci(from_sq), to_uci(to_sq), "capture")

                    # --- en passant ---
                    if pos.ep_square != -1:
                        ep_target = pos.ep_square
                        if get_pawn_attacks(from_sq, color) & (1 << ep_target):
                            capture_sq = (ep_target - 8 if color == types.WHITE else ep_target + 8)

                            captured_piece = pos.piece_at(capture_sq)
                            expected = (types.BP if color == types.WHITE else types.WP)

                            if captured_piece == expected:
                                moves.append(encode_move(from_sq, ep_target, flags=types.CAPTURE | types.EN_PASSANT))
                                #print(to_uci(from_sq), to_uci(ep_target), "en passant")

                else:
                    if piece in (types.WN, types.BN):
                        targets = (get_knight_attacks(from_sq) & ~own_occ)
                    elif piece in (types.WB, types.BB):
                        targets = get_bishop_attacks(from_sq, occ) & ~own_occ
                    elif piece in (types.WR, types.BR):
                        targets = get_rook_attacks(from_sq, occ) & ~own_occ
                    elif piece in (types.WQ, types.BQ):
                        targets = get_queen_attacks(from_sq, occ) & ~own_occ
                    elif piece in (types.WK, types.BK):
                        targets = (get_king_attacks(from_sq) & ~own_occ)
                        
                        # castling
                        if piece == types.WK and from_sq == types.E1:
                            if (pos.castling_rights & types.WK_CASTLE and 
                                not (pos.all_occ & ((1 << types.F1) | (1 << types.G1))) and 
                                pos.piece_at(types.H1) == types.WR):
                                moves.append(encode_move(from_sq, types.G1, flags=types.CASTLE))
                                #print(to_uci(from_sq), to_uci(types.G1), "white king castle")
                                targets &= ~(1 << types.G1)

                            if (pos.castling_rights & types.WQ_CASTLE and 
                                not (pos.all_occ & ((1 << types.D1) | (1 << types.C1) | (1 << types.B1))) and 
                                pos.piece_at(types.A1) == types.WR):
                                moves.append(encode_move(from_sq, types.C1, flags=types.CASTLE))
                                #print(to_uci(from_sq), to_uci(types.C1), "white queen castle")
                                targets &= ~(1 << types.C1)

                        # black castling
                        elif piece == types.BK and from_sq == types.E8:
                            if (pos.castling_rights & types.BQ_CASTLE and 
                                not (pos.all_occ & ((1 << types.D8) | (1 << types.C8) | (1 << types.B8))) and 
                                pos.piece_at(types.A8) == types.BR):
                                moves.append(encode_move(from_sq, types.C8, flags=types.CASTLE))
                                #print(to_uci(from_sq), to_uci(types.C8), "black queen castle")
                                targets &= ~(1 << types.C8)

                            if (pos.castling_rights & types.BK_CASTLE and 
                                not (pos.all_occ & ((1 << types.F8) | (1 << types.G8))) and 
                                pos.piece_at(types.H8) == types.BR):
                                moves.append(encode_move(from_sq, types.G8, flags=types.CASTLE))
                                #print(to_uci(from_sq), to_uci(types.G8), "black king castle")
                                targets &= ~(1 << types.G8)

                    # add to list with flags
                    while targets:
                        to_sq, targets = Bitboard.pop_lsb(targets)
                        move_flag = types.CAPTURE if (enemy_occ & (1 << to_sq)) else 0
                        move = encode_move(from_sq, to_sq, flags=move_flag)
                        #print(to_uci(from_sq), to_uci(to_sq), "capture" if move_flag else "quiet")
                        moves.append(move)

        return moves

    @staticmethod
    def generate_non_king_moves(pos, safety) -> list[int]:
        moves = []
        side = pos.side_to_move
        occ = pos.all_occ
        if side == types.WHITE:
            own_occ = pos.white_occ
            enemy_occ = pos.black_occ
            #enemy_king_bb = pos.pieces[types.BK]
            pieces = range(0, 6)
        else:
            own_occ = pos.black_occ
            enemy_occ = pos.white_occ
            #enemy_king_bb = pos.pieces[types.WK]
            pieces = range(6, 12)

        if side == types.WHITE:
            enemy_king_bb = pos.pieces[types.BK]
        else:
            enemy_king_bb = pos.pieces[types.WK]

        capture_targets = enemy_occ & ~enemy_king_bb

        for piece in pieces:
            bb = pos.pieces[piece]
            while bb:
                from_sq, bb = Bitboard.pop_lsb(bb)
                targets = 0
                flags = 0
                if piece in (types.WP, types.BP):
                    color = (types.WHITE if piece < 6 else types.BLACK)
                    allowed = safety["evasion"]
                    if safety["pinned"] & (1 << from_sq):
                        allowed &= safety["pin_masks"][from_sq]
                    if color == types.WHITE:
                        one_step = from_sq + 8
                        two_step = from_sq + 16

                        if one_step < 64 and not (pos.all_occ & (1 << one_step)):
                            # if 8th rank only append promotions not regular moves
                            if one_step // 8 == 7:
                                if allowed & (1 << one_step):
                                    for promo in [types.PROMO_QUEEN, types.PROMO_ROOK, types.PROMO_BISHOP, types.PROMO_KNIGHT]:
                                        moves.append(encode_move(from_sq, one_step, promotion=promo))
                                        ##print(to_uci(from_sq), to_uci(one_step), promo)
                            else:
                                # 1 step
                                if allowed & (1 << one_step):
                                    moves.append(encode_move(from_sq, one_step, flags=0))
                                # 2 step
                                if from_sq // 8 == 1 and not (pos.all_occ & (1 << two_step)) and (allowed & (1 << two_step)):
                                    moves.append(encode_move(from_sq, two_step, flags=types.DOUBLE_PAWN_PUSH))

                    # bp
                    else:
                        one_step = from_sq - 8
                        two_step = from_sq - 16

                        if one_step >= 0 and not (pos.all_occ & (1 << one_step)):
                            # 1st rank same thing
                            if one_step // 8 == 0:
                                if allowed & (1 << one_step):
                                    for promo in [types.PROMO_QUEEN, types.PROMO_ROOK, types.PROMO_BISHOP, types.PROMO_KNIGHT]:
                                        moves.append(encode_move(from_sq, one_step, promotion=promo))
                            else:
                                # 1 step
                                if allowed & (1 << one_step):
                                    moves.append(encode_move(from_sq, one_step, flags=0))
                                # 2 step from rank 7
                                if from_sq // 8 == 6 and not (pos.all_occ & (1 << two_step)) and (allowed & (1 << two_step)):
                                    moves.append(encode_move(from_sq, two_step, flags=types.DOUBLE_PAWN_PUSH))

                    # --- diag captures ---
                    cap_targets = get_pawn_attacks(from_sq, color) & capture_targets & allowed
                    while cap_targets:
                        to_sq, cap_targets = Bitboard.pop_lsb(cap_targets)
                        is_promo_rank = (to_sq // 8 == 7 if color == types.WHITE else to_sq // 8 == 0)

                        if is_promo_rank:
                            for promo in [types.PROMO_QUEEN, types.PROMO_ROOK, types.PROMO_BISHOP, types.PROMO_KNIGHT]:
                                moves.append(encode_move(from_sq, to_sq, promotion=promo, flags=(types.CAPTURE)))
                        else:
                            moves.append(encode_move(from_sq, to_sq, flags=types.CAPTURE))

                    # --- en passant ---
                    if pos.ep_square != -1:
                        ep_target = pos.ep_square
                        if get_pawn_attacks(from_sq, color) & (1 << ep_target):
                            capture_sq = (ep_target - 8 if color == types.WHITE else ep_target + 8)

                            captured_piece = pos.piece_at(capture_sq)
                            expected = (types.BP if color == types.WHITE else types.WP)
                            if captured_piece == expected:
                                candidate = encode_move(from_sq, ep_target, flags=types.CAPTURE | types.EN_PASSANT)
                                pos.make_move(candidate)
                                leaves_king_in_check = pos.in_check(color)
                                pos.unmake_move()
                                if not leaves_king_in_check:
                                    moves.append(candidate)
                else:
                    if piece in (types.WN, types.BN):
                        targets = get_knight_attacks(from_sq) & ~(own_occ | enemy_king_bb)
                    elif piece in (types.WB, types.BB):
                        targets = get_bishop_attacks(from_sq, occ) & ~(own_occ | enemy_king_bb)
                    elif piece in (types.WR, types.BR):
                        targets = get_rook_attacks(from_sq, occ) & ~(own_occ | enemy_king_bb)
                    elif piece in (types.WQ, types.BQ):
                        targets = get_queen_attacks(from_sq, occ) & ~(own_occ | enemy_king_bb)

                    if safety["pinned"] & (1 << from_sq):
                        targets &= safety["pin_masks"][from_sq]

                    targets &= safety["evasion"]
                    # add to list with flags
                    while targets:
                        to_sq, targets = Bitboard.pop_lsb(targets)
                        move_flag = types.CAPTURE if (enemy_occ & (1 << to_sq)) else 0
                        move = encode_move(from_sq, to_sq, flags=move_flag)
                        moves.append(move)

        return moves

    @staticmethod
    def find_pins(pos, color, king_sq):
        pinned = 0
        pin_masks = {}

        enemy = (types.BLACK if color == types.WHITE else types.WHITE)
        directions = [
            (1,0),
            (-1,0),
            (0,1),
            (0,-1),
            (1,1),
            (-1,-1),
            (1,-1),
            (-1,1),
        ]

        for df, dr in directions:
            blocker = None
            file = king_sq % 8
            rank = king_sq // 8
            f = file + df
            r = rank + dr
            while 0 <= f < 8 and 0 <= r < 8:
                sq = r * 8 + f
                piece = pos.piece_at(sq)
                if piece is not None:
                    piece_color = types.WHITE if piece < 6 else types.BLACK
                    if piece_color == color:
                        if blocker is not None:
                            break
                        blocker = sq
                    else:
                        if blocker is not None:
                            piece_type = piece % 6
                            diagonal = df != 0 and dr != 0
                            slider = (piece_type == types.QUEEN or (diagonal and piece_type == types.BISHOP) or (not diagonal and piece_type == types.ROOK))
                            if slider:
                                pinned |= 1 << blocker
                                pin_masks[blocker] = tables.LINE[king_sq][sq]
                        break
                f += df
                r += dr
        return pinned, pin_masks

    @staticmethod
    def analyze_king_safety(pos):
        color = pos.side_to_move

        king_sq = pos.king_square(color)

        enemy = types.BLACK if color == types.WHITE else types.WHITE
        checkers = MoveGenerator.attackers_to(pos, king_sq, enemy)

        pinned, pin_masks = MoveGenerator.find_pins(pos, color, king_sq)


        if checkers.bit_count() == 1:
            checker_sq = Bitboard.lsb(checkers)
            evasion_mask = (tables.BETWEEN[king_sq][checker_sq] | (1 << checker_sq))
        elif checkers:
            # double check
            evasion_mask = 0
        else:
            evasion_mask = (1 << 64) - 1

        return {
            "king": king_sq,
            "checkers": checkers,
            "pinned": pinned,
            "pin_masks": pin_masks,
            "evasion": evasion_mask
        }
    
    @staticmethod
    def generate_king_moves(pos, safety):
        moves = []
        king_sq = safety["king"]
        color = pos.side_to_move

        enemy = (types.BLACK if color == types.WHITE else types.WHITE)
        friendly_occ = pos.white_occ if color == types.WHITE else pos.black_occ

        attacks = get_king_attacks(king_sq)
        attacks &= ~friendly_occ

        occ_without_king = pos.all_occ & ~(1 << king_sq)

        enemy_attacks = MoveGenerator.generate_attack_map(pos, enemy, occ_without_king)

        attacks &= ~enemy_attacks

        enemy_occ = pos.black_occ if color == types.WHITE else pos.white_occ

        while attacks:
            to_sq, attacks = Bitboard.pop_lsb(attacks)

            flags = types.CAPTURE if (enemy_occ & (1 << to_sq)) else 0

            moves.append(encode_move(from_sq=king_sq, to_sq=to_sq, flags=flags))

        for move in moves:
            from_sq = move & 0x3F
            to_sq = (move >> 6) & 0x3F
            flags = (move >> 12) & 0xF

            if pos.piece_at(to_sq) is not None:
                assert flags & types.CAPTURE, (
                    move,
                    from_sq,
                    to_sq,
                    pos.piece_at(from_sq),
                    pos.piece_at(to_sq),
                    flags,
                )

        return moves

    @staticmethod
    def generate_castling_moves(pos):
        moves = []

        if pos.side_to_move == types.WHITE:
            king_sq = types.E1

            if (pos.castling_rights & types.WK_CASTLE and pos.piece_at(types.H1) == types.WR):
                if (
                    not (pos.all_occ & ((1 << types.F1) | (1 << types.G1)))
                    and not MoveGenerator.is_square_attacked(pos, types.E1, types.BLACK)
                    and not MoveGenerator.is_square_attacked(pos, types.F1, types.BLACK)
                    and not MoveGenerator.is_square_attacked(pos, types.G1, types.BLACK)
                ):
                    moves.append(encode_move(types.E1, types.G1, flags = types.CASTLE))

            if (pos.castling_rights & types.WQ_CASTLE and pos.piece_at(types.A1) == types.WR):
                if (
                    not (pos.all_occ & ((1 << types.B1) | (1 << types.C1) | (1 << types.D1)))
                    and not MoveGenerator.is_square_attacked(pos, types.E1, types.BLACK)
                    and not MoveGenerator.is_square_attacked(pos, types.D1, types.BLACK)
                    and not MoveGenerator.is_square_attacked(pos, types.C1, types.BLACK)
                ):
                    moves.append(encode_move(types.E1, types.C1, flags = types.CASTLE))
        elif pos.side_to_move == types.BLACK:
            king_sq = types.E8

            if (pos.castling_rights & types.BK_CASTLE and pos.piece_at(types.H8) == types.BR):
                if (
                    not (pos.all_occ & ((1 << types.F8) | (1 << types.G8)))
                    and not MoveGenerator.is_square_attacked(pos, types.E8, types.WHITE)
                    and not MoveGenerator.is_square_attacked(pos, types.F8, types.WHITE)
                    and not MoveGenerator.is_square_attacked(pos, types.G8, types.WHITE)
                ):
                    moves.append(encode_move(types.E8, types.G8, flags = types.CASTLE))

            if (pos.castling_rights & types.BQ_CASTLE and pos.piece_at(types.A8) == types.BR):
                if (
                    not (pos.all_occ & ((1 << types.B8) | (1 << types.C8) | (1 << types.D8)))
                    and not MoveGenerator.is_square_attacked(pos, types.E8, types.WHITE)
                    and not MoveGenerator.is_square_attacked(pos, types.D8, types.WHITE)
                    and not MoveGenerator.is_square_attacked(pos, types.C8, types.WHITE)
                ):
                    moves.append(encode_move(types.E8, types.C8, flags = types.CASTLE))
        return moves

    @staticmethod
    def generate_legal_moves(pos):
        moves = []
        safety = MoveGenerator.analyze_king_safety(pos)
        checker_count = bin(safety["checkers"]).count('1') if isinstance(safety["checkers"], int) else len(safety["checkers"])

        if checker_count > 1:
            moves.extend(MoveGenerator.generate_king_moves(pos, safety))
            return moves

        moves.extend(MoveGenerator.generate_king_moves(pos, safety))

        if checker_count == 0:
            moves.extend(MoveGenerator.generate_castling_moves(pos))

        moves.extend(MoveGenerator.generate_non_king_moves(pos, safety))

        return moves

    @staticmethod
    def generate_legal_captures(pos) -> list[int]:
        return [
            move
            for move in MoveGenerator.generate_legal_moves(pos)
            if (
                ((move >> 12) & 0xF) & (types.CAPTURE | types.EN_PASSANT)
                or ((move >> 16) & 0xF)
            )
        ]
    
    @staticmethod
    def attackers_to(pos, square, color, occupancy=None):
        attackers = 0
        occ = pos.all_occ if occupancy is None else occupancy

        # pawns
        if color == types.WHITE:
            attackers |= (get_pawn_attacks(square, types.BLACK) & pos.pieces[types.WP])
        else:
            attackers |= (get_pawn_attacks(square, types.WHITE) & pos.pieces[types.BP])

        # knights
        attackers |= (get_knight_attacks(square) & pos.pieces[color * 6 + types.WN])

        # bishops and queens
        diagonal_attackers = get_bishop_attacks(square, occ)
        attackers |= (diagonal_attackers & (pos.pieces[color * 6 + types.WB] | pos.pieces[color * 6 + types.WQ]))

        # rooks and queens
        straight_attackers = get_rook_attacks(square, occ)
        attackers |= (straight_attackers & (pos.pieces[color * 6 + types.WR] | pos.pieces[color * 6 + types.WQ]))

        # kings
        attackers |= (get_king_attacks(square) & pos.pieces[color * 6 + types.WK])

        return attackers
    
    @staticmethod
    def generate_attack_map(pos, color, occupancy=None):
        attack_map = 0
        if occupancy is None:
            occupancy = pos.all_occ

        start = 0 if color == types.WHITE else 6
        end = start + 6

        for piece in range(start, end):
            piece_type = piece % 6

            bb = pos.pieces[piece]

            while bb:
                from_sq, bb = Bitboard.pop_lsb(bb)
                if piece_type == types.PAWN:  # pawn
                    attack_map |= get_pawn_attacks(from_sq, color)
                elif piece_type == types.KNIGHT:  # knight
                    attack_map |= get_knight_attacks(from_sq)
                elif piece_type == types.BISHOP:  # bishop
                    # no ~self_occ
                    attack_map |= get_bishop_attacks(from_sq, occupancy)
                elif piece_type == types.ROOK:  # rook
                    # no ~self_occ
                    attack_map |= get_rook_attacks(from_sq, occupancy)
                elif piece_type == types.QUEEN:  # queen
                    # no ~self_occ
                    attack_map |= get_queen_attacks(from_sq, occupancy)
                elif piece_type == types.KING:  # king
                    attack_map |= get_king_attacks(from_sq)

        return attack_map
    
    @staticmethod
    def is_square_attacked(pos, square: int, attacker_color: int, custom_occ=None) -> bool:
        board = pos if hasattr(pos, 'pieces') else pos.position 
        occ = custom_occ if custom_occ is not None else board.all_occ

        if attacker_color == types.WHITE:
            pawns   = board.pieces[types.WP]
            knights = board.pieces[types.WN]
            bishops = board.pieces[types.WB]
            rooks   = board.pieces[types.WR]
            queens  = board.pieces[types.WQ]
            king    = board.pieces[types.WK]
            pawn_lookup_color = types.BLACK
        else:
            pawns   = board.pieces[types.BP]
            knights = board.pieces[types.BN]
            bishops = board.pieces[types.BB]
            rooks   = board.pieces[types.BR]
            queens  = board.pieces[types.BQ]
            king    = board.pieces[types.BK]
            pawn_lookup_color = types.WHITE

        if get_knight_attacks(square) & knights: return True
        if get_king_attacks(square) & king: return True
        if get_pawn_attacks(square, pawn_lookup_color) & pawns: return True
        if get_bishop_attacks(square, occ) & (bishops | queens): return True
        if get_rook_attacks(square, occ) & (rooks | queens): return True
        return False
    
    @staticmethod
    def in_check(pos, color):
        king_piece = (types.WK if color == types.WHITE else types.BK)
        king_bb = pos.pieces[king_piece]
        if king_bb == 0:
            raise ValueError(f"No king found for {color}!!")
        # remove the king
        king_square = (king_bb & -king_bb).bit_length() - 1 # Long.SIZE - Long.numberOfLeadingZeros(num) in java
        # no xor bit flip because different scopes mess it up
        attacker_col = types.BLACK if color == types.WHITE else types.WHITE
        return MoveGenerator.is_square_attacked(pos, king_square, attacker_col)

    @staticmethod
    def gives_check(pos, move):
        from_sq = move & 0x3F
        to_sq = (move >> 6) & 0x3F
        promotion = (move >> 16) & 0xF
        flags = (move >> 12) & 0xF

        moving_piece = pos.piece_at(from_sq)

        enemy = types.BLACK if pos.side_to_move == types.WHITE else types.WHITE
        enemy_king_sq = pos.king_square(enemy)

        occ = pos.all_occ

        occ &= ~(1 << from_sq)

        if flags & types.CAPTURE:
            captured_sq = to_sq
            # en passant capture removes pawn behind target
            if flags & types.EN_PASSANT:
                captured_sq = to_sq - 8 if pos.side_to_move == types.WHITE else to_sq + 8
            occ &= ~(1 << captured_sq)
        occ |= (1 << to_sq)


        # promo changes piece type
        if promotion:
            piece_type = promotion
        else:
            piece_type = moving_piece % 6

        if piece_type == types.PAWN:
            return bool(get_pawn_attacks(to_sq, pos.side_to_move) & (1 << enemy_king_sq))

        elif piece_type == types.KNIGHT:
            return bool(get_knight_attacks(to_sq) & (1 << enemy_king_sq))

        elif piece_type == types.BISHOP:
            return bool(get_bishop_attacks(to_sq, occ) & (1 << enemy_king_sq))

        elif piece_type == types.ROOK:
            return bool(get_rook_attacks(to_sq, occ) & (1 << enemy_king_sq))

        elif piece_type == types.QUEEN:
            return bool(get_queen_attacks(to_sq, occ) & (1 << enemy_king_sq))

        elif piece_type == types.KING:
            return bool(get_king_attacks(to_sq) & (1 << enemy_king_sq))
        
        # discovered check
        return MoveGenerator.is_square_attacked(pos, enemy_king_sq, pos.side_to_move, custom_occ=occ)


    # impleemnt following functions
    # gencaps
    # genquiets
    # genevasions
    # genchecks
    # genpromos
    # gencastles
    # genenpassant

    

    @staticmethod
    def format_moves(moves):
        return [m.to_uci() for m in moves]
    

"""
 @staticmethod
    def generate_legal_moves(pos) -> list[Move]:
        legal_moves = []
        pseudo_moves = MoveGenerator.generate_pseudo_legal_moves(pos)

        king_piece = types.WK if pos.side_to_move == types.WHITE else types.BK
        enemy_color = types.BLACK if pos.side_to_move == types.WHITE else types.WHITE

        for move in pseudo_moves:
            us = pos.side_to_move
            pos.make_move(move)
            #print(pos.prettyPrint())
            #print(pos.to_fen())

            king_bb = pos.pieces[king_piece]
            king_sq, _ = Bitboard.pop_lsb(king_bb) if king_bb else (-1, 0)

            if not MoveGenerator.is_square_attacked(pos, king_sq, enemy_color):
                legal_moves.append(move)

            pos.unmake_move()
            #try:
            #    if not MoveGenerator.in_check(pos, us):
            #        legal_moves.append(move)
            #finally:
            #    pos.unmake_move()


        return legal_moves
        """