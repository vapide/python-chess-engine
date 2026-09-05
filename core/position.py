import os

import numpy as np

import core.bitboard as bitboard
from core.bitboard import Bitboard
from evaluation.nnue import NNUE
from movegen.move_generator import MoveGenerator
from utils import zobrist
import utils.rkiss as rkiss
from utils.zobrist import Zobrist
from core.move import to_uci
import core.types
from core import types

_DEFAULT_NNUE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nets", "bunnynator.nnue"
)


class PositionState:
    __slots__ = (
        "move",
        "moved_piece",
        "captured_piece",
        "captured_square",
        "castling_rights",
        "castling_rights_old",
        "ep_square",
        "halfmove_clock",
        "fullmove_number",
        "hash",
        "pawn_hash",
        "non_pawn_hash_white",
        "non_pawn_hash_black",
        "promotion_piece",
        "was_ep",
        "was_castle",
        "was_promotion",
        "flags",
        "accumulator",
    )

    def __init__(
        self,
        move=None,
        moved_piece=None,
        captured_piece=None,
        captured_square=-1,
        castling_rights=0,
        castling_rights_old=0,
        ep_square=-1,
        halfmove_clock=0,
        fullmove_number=1,
        hash=0,
        flags = 0,
        pawn_hash = 0,
        non_pawn_hash_white = 0,
        non_pawn_hash_black = 0,
        accumulator = None
    ):
        self.move = move
        self.moved_piece = moved_piece
        self.captured_piece = captured_piece
        self.captured_square = captured_square
        self.castling_rights = castling_rights
        self.castling_rights_old = castling_rights_old
        self.ep_square = ep_square
        self.halfmove_clock = halfmove_clock
        self.fullmove_number = fullmove_number
        self.hash = hash
        self.pawn_hash = 0
        self.non_pawn_hash_white = 0
        self.non_pawn_hash_black = 0
        self.promotion_piece = None
        self.flags = flags
        self.accumulator = None


class Position:
    def __init__(self):
        self.pieces = [0] * 12
        # Mailbox mirror of self.pieces for O(1) piece_at() lookups, kept in
        # sync by add_piece/remove_piece/move_piece (the only places that
        # mutate self.pieces). piece_at() used to rescan all 12 bitboards on
        # every call - a hot path (move ordering, SEE, make/unmake) - so this
        # trades 64 extra ints of memory for an O(12) -> O(1) lookup there.
        self.mailbox = [None] * 64

        self.white_occ = 0
        self.black_occ = 0
        self.all_occ = 0

        self.side_to_move = core.types.WHITE

        self.castling_rights = (
            core.types.WK_CASTLE |
            core.types.WQ_CASTLE |
            core.types.BK_CASTLE |
            core.types.BQ_CASTLE
        )


        self.ep_square = -1

        self.halfmove_clock = 0
        self.fullmove_number = 1

        self.zobrist = Zobrist()

        self.flags = 0

        self.nnue = NNUE(_DEFAULT_NNUE_PATH)

        self.history = [PositionState() for _ in range(256)]

        self.nnue.refresh_from_pos(self)
        start_accumulator = {
            'white': np.copy(self.nnue.acc_white),
            'black': np.copy(self.nnue.acc_black)
        }
        self.history[0].accumulator = start_accumulator
        

        self.ply = 0

    def is_game_over(self):
        legal_moves = MoveGenerator.generate_legal_moves(self)
        
        if legal_moves:
            return False

        if MoveGenerator.in_check(self, self.side_to_move):
            return True # checkmate

        return True # stalemate

    @staticmethod
    def from_fen(fen: str, nnue_instance=None):
        position = Position()

        if nnue_instance is not None:
            position.nnue = nnue_instance
        else:
            position.nnue = NNUE(_DEFAULT_NNUE_PATH)

        parts = fen.split()

        piece_map = {
            "P": core.types.WP, "N": core.types.WN, "B": core.types.WB,
            "R": core.types.WR, "Q": core.types.WQ, "K": core.types.WK,
            "p": core.types.BP, "n": core.types.BN, "b": core.types.BB,
            "r": core.types.BR, "q": core.types.BQ, "k": core.types.BK
        }

        # Piece placement
        ranks = parts[0].split('/')

        for row in range(8): 
            file = 0
            for char in ranks[row]:
                if char.isdigit():
                    file += int(char)
                else:
                    square = (7 - row) * 8 + file
                    position.add_piece(
                        piece_map[char],
                        square
                    )
                    file += 1

        # Side to move
        position.side_to_move = (
            core.types.WHITE if parts[1] == 'w'
            else core.types.BLACK
        )

        # Castling rights
        position.castling_rights = 0

        if 'K' in parts[2]:
            position.castling_rights |= core.types.WK_CASTLE

        if 'Q' in parts[2]:
            position.castling_rights |= core.types.WQ_CASTLE

        if 'k' in parts[2]:
            position.castling_rights |= core.types.BK_CASTLE

        if 'q' in parts[2]:
            position.castling_rights |= core.types.BQ_CASTLE

        # En-passant
        if parts[3] == '-':
            position.ep_square = -1

        else:
            file = ord(parts[3][0]) - ord('a')
            rank = int(parts[3][1]) - 1

            position.ep_square = rank * 8 + file

        # Move counters
        position.halfmove_clock = int(parts[4])
        position.fullmove_number = int(parts[5])

        position.update_occupancy()

        position.zobrist.hash = position.zobrist.compute(position)

        position.nnue.refresh_from_pos(position)
    
        #assert position.zobrist.hash == position.zobrist.compute(position)

        return position

    def to_fen(self) -> str:
        fen = ""

        for rank in range(7, -1, -1):
            empty_count = 0
            for file in range(8):
                square = rank * 8 + file
                piece = self.piece_at(square)

                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen += str(empty_count)
                        empty_count = 0

                    piece_char = (
                        "PNBRQK" if piece < 6 else "pnbrqk"
                    )[piece % 6]

                    fen += piece_char

            if empty_count > 0:
                fen += str(empty_count)

            if rank > 0:
                fen += "/"

        fen += " "
        fen += "w" if self.side_to_move == core.types.WHITE else "b"
        fen += " "

        castling_str = ""
        if self.castling_rights & core.types.WK_CASTLE:
            castling_str += "K"
        if self.castling_rights & core.types.WQ_CASTLE:
            castling_str += "Q"
        if self.castling_rights & core.types.BK_CASTLE:
            castling_str += "k"
        if self.castling_rights & core.types.BQ_CASTLE:
            castling_str += "q"

        fen += castling_str if castling_str else "-"
        fen += " "

        if self.ep_square == -1:
            fen += "-"
        else:
            file = self.ep_square % 8
            rank = self.ep_square // 8
            fen += f"{chr(file + ord('a'))}{rank + 1}"

        fen += f" {self.halfmove_clock} {self.fullmove_number}"

        return fen


    def is_checkmate(self, color):
        if not self.in_check(color):
            return False
        legal_moves = MoveGenerator.generate_legal_moves(self)
        return len(legal_moves) == 0

    #def is_square_attacked(self, square: int, color: int) -> int:
    #    occupancy = self.white_occ if color == core.types.WHITE else self.black_occ
        

        # save for legality check
        #if self.pieces[(color + 1) * 6]: # king attacks
        #    self.pieces[(color + 1) * 6] & attacks.get_king_attacks(1 << square): # white = white king, black = black king
        #        raise ValueError("Kings are touching each other, illegal position")
        
    @staticmethod
    def startpos(nnue_instance = None):
        pos = Position.from_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            nnue_instance=nnue_instance
        )
        return pos
    
    def update_occupancy(self):
        self.white_occ = 0
        self.black_occ = 0
        for piece in range(6):
            self.white_occ |= self.pieces[piece]

        for piece in range(6, 12):
            self.black_occ |= self.pieces[piece]
        self.all_occ = self.white_occ | self.black_occ

    def update_occupancy_after_move(self, move, moving_piece, captured_square=-1):
        from_bb = 1 << (move & 0x3F)
        to_bb = 1 << ((move >> 6) & 0x3F)

        if moving_piece < 6: # white
            self.white_occ &= ~from_bb
            self.white_occ |= to_bb

            if captured_square != -1:
                self.black_occ &= ~(1 << captured_square)

        else: # black
            self.black_occ &= ~from_bb
            self.black_occ |= to_bb

            if captured_square != -1:
                self.white_occ &= ~(1 << captured_square)

    def sync_occupancies(self):
        self.white_occ = 0
        self.black_occ = 0

        for piece in range(0, 6):
            self.white_occ |= self.pieces[piece]
            
        for piece in range(6, 12):
            self.black_occ |= self.pieces[piece]
            
        self.all_occ = self.white_occ | self.black_occ

    def piece_at(self, square: int) -> int | None:
        return self.mailbox[square]

    def add_piece(self, piece, square):
        #assert self.piece_at(square) is None

        bb = 1 << square
        self.pieces[piece] |= bb
        self.mailbox[square] = piece
        if piece < 6:
            self.white_occ |= bb
        else:
            self.black_occ |= bb
        self.all_occ |= bb

    def remove_piece(self, piece, square):
        #assert self.piece_at(square) == piece

        bb = 1 << square
        self.pieces[piece] &= ~bb
        self.mailbox[square] = None
        if piece < 6:
            self.white_occ &= ~bb
        else:
            self.black_occ &= ~bb
        self.all_occ &= ~bb

    def move_piece(self, piece, from_sq, to_sq):

        assert self.mailbox[from_sq] == piece, (
            piece,
            from_sq,
            self.mailbox[from_sq],
        )

        assert self.mailbox[to_sq] is None, (
            piece,
            to_sq,
            self.mailbox[to_sq],
        )

        from_mask = ~(1 << from_sq)
        to_bb = 1 << to_sq
        self.pieces[piece] &= from_mask
        self.pieces[piece] |= to_bb
        self.mailbox[from_sq] = None
        self.mailbox[to_sq] = piece
        if piece < 6:
            self.white_occ &= from_mask
            self.white_occ |= to_bb
        else:
            self.black_occ &= from_mask
            self.black_occ |= to_bb
        self.all_occ &= from_mask
        self.all_occ |= to_bb

    def king_square(self, color: int) -> int: # useful for legality checks
        king_bb = self.pieces[
            core.types.WK if color == core.types.WHITE else core.types.BK
        ]
        return (king_bb & -king_bb).bit_length() - 1 # -1 because bit_length returns index based on 1 not 0
    
    def in_check(self, color: int) -> bool:
        king_sq = self.king_square(color)
        return MoveGenerator.is_square_attacked(self, king_sq, color ^ 1)
    
    def make_move(self, move):
        old_hash = self.zobrist.hash
        if self.ply >= len(self.history):
            self.history.append(PositionState())
        state = self.history[self.ply]
        state.hash = self.zobrist.hash
        state.pawn_hash = self.zobrist.pawn_hash
        state.non_pawn_hash_white = self.zobrist.non_pawn_hash[core.types.WHITE]
        state.non_pawn_hash_black = self.zobrist.non_pawn_hash[core.types.BLACK]

        from_sq = (move & 0x3F)
        to_sq = (move >> 6) & 0x3F
        flags = (move >> 12) & 0xF
        moving_piece = self.piece_at(from_sq)

        captured_square = to_sq
        captured_piece = self.piece_at(to_sq)

        if flags & core.types.EN_PASSANT:
            captured_square = (to_sq - 8 if moving_piece == core.types.WP else to_sq + 8)
            captured_piece = self.piece_at(captured_square)

        self.nnue.push()
        removed_pieces = []
        added_pieces = []

        state.captured_piece = captured_piece
        state.captured_square = captured_square if captured_piece is not None else -1

        if moving_piece is None:
            raise ValueError(f"No piece on square {(move & 0x3F)}")
             
        state.move = move
        state.moved_piece = moving_piece
        state.castling_rights = self.castling_rights
        state.ep_square = self.ep_square
        state.halfmove_clock = self.halfmove_clock
        state.fullmove_number = self.fullmove_number
        state.promotion_piece = None
        state.flags = flags

        removed_pieces.append((moving_piece, (move & 0x3F))) # first piece leaves its location
        if self.ep_square != -1:
            self.zobrist.toggle_ep(self.ep_square)

        self.ep_square = -1
        old_castling = self.castling_rights

        self.castling_rights &= core.types.CASTLING_MASKS[from_sq]
        if state.captured_square != -1:
            self.castling_rights &= core.types.CASTLING_MASKS[state.captured_square]

        new_castling = self.castling_rights
        changed_castling = old_castling ^ new_castling

        for i in range(4):
            if changed_castling & (1 << i):
                self.zobrist.toggle_castling(i)

        self.zobrist.toggle_piece(moving_piece, from_sq)

        is_pawn = moving_piece in (core.types.WP, core.types.BP)

        if captured_piece is not None:
            self.zobrist.toggle_piece(captured_piece, captured_square)
            self.remove_piece(captured_piece, captured_square)
            removed_pieces.append((captured_piece, captured_square))

        self.move_piece(moving_piece, from_sq, to_sq)

        if (moving_piece == core.types.WK or moving_piece == core.types.BK) and abs(from_sq - to_sq) == 2:
            if moving_piece == core.types.WK:
                if to_sq == core.types.G1:
                    self.move_piece(core.types.WR, core.types.H1, core.types.F1)
                    removed_pieces.append((core.types.WR, core.types.H1))
                    added_pieces.append((core.types.WR, core.types.F1))
                    self.zobrist.toggle_piece(core.types.WR, core.types.H1)
                    self.zobrist.toggle_piece(core.types.WR, core.types.F1)
                elif to_sq == core.types.C1:
                    self.move_piece(core.types.WR, core.types.A1, core.types.D1)
                    removed_pieces.append((core.types.WR, core.types.A1))
                    added_pieces.append((core.types.WR, core.types.D1))
                    self.zobrist.toggle_piece(core.types.WR, core.types.A1)
                    self.zobrist.toggle_piece(core.types.WR, core.types.D1)
            else:
                if to_sq == core.types.G8:
                    self.move_piece(core.types.BR, core.types.H8, core.types.F8)
                    removed_pieces.append((core.types.BR, core.types.H8))
                    added_pieces.append((core.types.BR, core.types.F8))
                    self.zobrist.toggle_piece(core.types.BR, core.types.H8)
                    self.zobrist.toggle_piece(core.types.BR, core.types.F8)
                elif to_sq == core.types.C8:
                    self.move_piece(core.types.BR, core.types.A8, core.types.D8)
                    removed_pieces.append((core.types.BR, core.types.A8))
                    added_pieces.append((core.types.BR, core.types.D8))
                    self.zobrist.toggle_piece(core.types.BR, core.types.A8)
                    self.zobrist.toggle_piece(core.types.BR, core.types.D8)
        promotion = (move >> 16) & 0xF
        #promotion_chars = {core.types.PROMO_QUEEN: 'q', core.types.PROMO_ROOK: 'r', core.types.PROMO_BISHOP: 'b', core.types.PROMO_KNIGHT: 'n'}
        if promotion != 0 and is_pawn:
            #print("PROMOTING", move, promotion, moving_piece)
            promotion_map = {
                core.types.PROMO_QUEEN:
                    core.types.WQ if moving_piece == core.types.WP else core.types.BQ,

                core.types.PROMO_ROOK:
                    core.types.WR if moving_piece == core.types.WP else core.types.BR,

                core.types.PROMO_BISHOP:
                    core.types.WB if moving_piece == core.types.WP else core.types.BB,

                core.types.PROMO_KNIGHT:
                    core.types.WN if moving_piece == core.types.WP else core.types.BN,
            }

            promoted_piece = promotion_map[promotion]
            self.remove_piece(moving_piece, to_sq)
            self.zobrist.toggle_piece(moving_piece, to_sq)

            self.add_piece(promoted_piece, to_sq)
            self.zobrist.toggle_piece(promoted_piece, to_sq)
            added_pieces.append((promoted_piece, to_sq))
            state.promotion_piece = promoted_piece
        else:
            self.zobrist.toggle_piece(moving_piece, to_sq)
            added_pieces.append((moving_piece, to_sq))

        if is_pawn or captured_piece is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if self.side_to_move == core.types.BLACK:
            self.fullmove_number += 1

        if is_pawn and abs(from_sq - to_sq) == 16:
            self.ep_square = (from_sq + to_sq) // 2
            self.zobrist.toggle_ep(self.ep_square)
        #print("Removed:", removed_pieces)
        #print("Added:", added_pieces)

        self.nnue.update(removed_pieces, added_pieces)

        self.zobrist.flip_side()
        self.side_to_move ^= 1

        expected = old_hash

        expected ^= self.zobrist.keys[types.WK * 64 + types.E1]
        expected ^= self.zobrist.keys[types.WK * 64 + types.D1]
        expected ^= self.zobrist.keys[zobrist.CASTLING_START + 0]
        expected ^= self.zobrist.keys[zobrist.CASTLING_START + 1]
        expected ^= self.zobrist.keys[zobrist.SIDE_KEY]
        
        self.sync_occupancies()
        self.ply += 1

        #for color, king_piece in [(types.WHITE, types.WK), (types.BLACK, types.BK)]:
        #    if self.pieces[king_piece].bit_count() != 1:
        #        raise ValueError(
        #           f"Corrupt king after move {move}: {self.pieces[king_piece]:064b}"
        #       )

    def unmake_move(self):
        self.nnue.pop()

        self.ply -= 1
        state = self.history[self.ply]

        move = state.move
        moving_piece = state.moved_piece

        if moving_piece is None:
            raise ValueError(f"No move state stored for ply {self.ply}")


        from_sq = move & 0x3F
        to_sq = (move >> 6) & 0x3F
        flags = (move >> 12) & 0xF
        promotion = (move >> 16) & 0xF

        if promotion:
            self.remove_piece(state.promotion_piece, to_sq)
            self.add_piece(moving_piece, from_sq)

            if state.captured_piece is not None:
                self.add_piece(state.captured_piece, state.captured_square)

        elif flags & core.types.EN_PASSANT:
            self.move_piece(moving_piece, to_sq, from_sq)
            self.add_piece(state.captured_piece, state.captured_square)

        elif (moving_piece == core.types.WK or moving_piece == core.types.BK) and abs(from_sq - to_sq) == 2:

            self.move_piece(moving_piece, to_sq, from_sq)

            if moving_piece == core.types.WK:
                if to_sq == core.types.G1:
                    self.move_piece(core.types.WR, core.types.F1, core.types.H1)
                elif to_sq == core.types.C1:
                    self.move_piece(core.types.WR, core.types.D1, core.types.A1)

            else:
                if to_sq == core.types.G8:
                    self.move_piece(core.types.BR, core.types.F8, core.types.H8)
                elif to_sq == core.types.C8:
                    self.move_piece(core.types.BR, core.types.D8, core.types.A8)

            #self.move_piece(moving_piece, to_sq, from_sq)

        else:
            self.move_piece(moving_piece, to_sq, from_sq)

            if state.captured_piece is not None:
                self.add_piece(state.captured_piece, state.captured_square)

        self.side_to_move ^= 1

        self.castling_rights = state.castling_rights
        self.ep_square = state.ep_square
        self.halfmove_clock = state.halfmove_clock
        self.fullmove_number = state.fullmove_number
        self.zobrist.hash = state.hash


        self.sync_occupancies()

        #saved_acc = getattr(state, "accumulator", None)
        #if saved_acc is not None:
        #    self.nnue.acc_white = np.copy(saved_acc['white'])
        #    self.nnue.acc_black = np.copy(saved_acc['black'])

    def make_null_move(self):
        if self.ply >= len(self.history):
            self.history.append(PositionState())
        state = self.history[self.ply]

        self.nnue.push()

        state.castling_rights = self.castling_rights
        state.ep_square = self.ep_square
        state.halfmove_clock = self.halfmove_clock
        state.fullmove_number = self.fullmove_number
        state.hash = self.zobrist.hash
        state.non_pawn_hash_white = self.zobrist.non_pawn_hash[0]
        state.non_pawn_hash_black = self.zobrist.non_pawn_hash[1]
        state.pawn_hash = self.zobrist.pawn_hash

        if self.ep_square != -1:
            self.zobrist.toggle_ep(self.ep_square)
        self.zobrist.flip_side()
        self.ply += 1
        self.ep_square = -1
        self.side_to_move ^= 1

    def unmake_null_move(self):
        self.ply -= 1

        state = self.history[self.ply]

        self.nnue.pop()

        self.castling_rights = state.castling_rights
        self.ep_square = state.ep_square
        self.halfmove_clock = state.halfmove_clock
        self.fullmove_number = state.fullmove_number
        self.zobrist.hash = state.hash
        self.zobrist.pawn_hash = state.pawn_hash
        self.zobrist.non_pawn_hash[0] = state.non_pawn_hash_white
        self.zobrist.non_pawn_hash[1] = state.non_pawn_hash_black

        self.side_to_move ^= 1

    def king_square(self, color: int) -> int:
        king_bb = self.pieces[core.types.WK if color == core.types.WHITE else core.types.BK]
        return (king_bb & -king_bb).bit_length() - 1  # -1 because bit_length returns index based on 1 not 0
    
    def has_non_pawn_material(self, color: int) -> bool: # king and pawns are not considered non-pawn material, so we check for knights, bishops, rooks, and queens
        if color == core.types.WHITE:
            return (self.pieces[core.types.WN] != 0 or 
                    self.pieces[core.types.WB] != 0 or 
                    self.pieces[core.types.WR] != 0 or 
                    self.pieces[core.types.WQ] != 0)
        else:
            return (self.pieces[core.types.BN] != 0 or 
                    self.pieces[core.types.BB] != 0 or 
                    self.pieces[core.types.BR] != 0 or 
                    self.pieces[core.types.BQ] != 0)

    def is_repetition(self) -> bool:
        limit = min(self.halfmove_clock, self.ply)
        idx = self.ply - 2
        steps = 2
        while steps <= limit:
            if self.history[idx].hash == self.zobrist.hash:
                return True
            idx -= 2
            steps += 2
        return False

    def is_insufficient_material(self) -> bool:
        if (self.pieces[core.types.WP] | self.pieces[core.types.BP] |
                self.pieces[core.types.WR] | self.pieces[core.types.BR] |
                self.pieces[core.types.WQ] | self.pieces[core.types.BQ]):
            return False

        wn = self.pieces[core.types.WN].bit_count()
        bn = self.pieces[core.types.BN].bit_count()
        wb = self.pieces[core.types.WB].bit_count()
        bb = self.pieces[core.types.BB].bit_count()
        minors = wn + bn + wb + bb

        if minors <= 1:
            return True  # king vs king cant do mate

        if minors == 2 and wb == 1 and bb == 1:
            # kb kb is draw when both are on same color
            w_sq = Bitboard.lsb(self.pieces[core.types.WB])
            b_sq = Bitboard.lsb(self.pieces[core.types.BB])
            return (w_sq // 8 + w_sq % 8) % 2 == (b_sq // 8 + b_sq % 8) % 2

        return False

    def prettyPrint(self): # prints backwards as we are using little endian rank file mapping
        print("  A B C D E F G H")
        for rank in range(7, -1, -1):
            line = f"{rank + 1} "
            for file in range(8):
                square = rank * 8 + file
                piece = self.piece_at(square)
                if piece is None:
                    line += ". "
                else:
                    piece_char = (
                        "PNBRQK" if piece < 6 else "pnbrqk"
                    )[piece % 6]
                    line += f"{piece_char} "
            print(line)

# todo:
# - implement transposition table  ex: transposition_table[position.zobrist_hash] = { "depth": depth, "score": score, "best_move": move }

""" old make_move where I recomputed piece types instead of storing them in the stack
    def make_move(self, move):
        state = self.history[self.ply] # get the current position state from the history stack

        state.move = move
        state.captured_piece = self.piece_at(((move >> 6) & 0x3F))
        state.captured_square = ((move >> 6) & 0x3F)
        state.castling_rights = self.castling_rights
        state.ep_square = self.ep_square
        state.halfmove_clock = self.halfmove_clock
        state.zobrist_hash = self.zobrist_hash
        state.captured_piece = self.piece_at(((move >> 6) & 0x3F))
        state.captured_square = ((move >> 6) & 0x3F) if state.captured_piece is not None else -1
        state.moved_piece = self.piece_at((move & 0x3F))
        state.promotion_piece = move.promotion

        if move.promotion is not None:
            self.remove_piece(moving_piece, ((move >> 6) & 0x3F))
            self.add_piece(move.promotion, ((move >> 6) & 0x3F))


        self.ply += 1 # add one to the ply

        moving_piece = self.piece_at((move & 0x3F))

        if self.side_to_move == WHITE:
            if moving_piece is not None and moving_piece >= 6:
                raise ValueError(
                    f"Trying to move black piece {moving_piece} on white's turn"
                )
        elif self.side_to_move == BLACK:
            if moving_piece is not None and moving_piece < 6:
                raise ValueError(
                    f"Trying to move white piece {moving_piece} on black's turn"\
                )
        else:
            raise ValueError(
                f"Invalid side to move: {self.side_to_move}"
            )

        if self.ep_square != -1:
            self.zobrist_hash ^= self.keys[773 + (self.ep_square % 8)]


        if moving_piece is None:
            raise ValueError(
                f"No piece on square {(move & 0x3F)}"
            )

        self.zobrist_hash ^= self.keys[moving_piece * 64 + (move & 0x3F)]

        is_pawn = (moving_piece % 6 == WP)

        if is_pawn and ((move >> 6) & 0x3F) == self.ep_square and state.captured_piece is None: # en passant
            self.captured_square = ((move >> 6) & 0x3F) - 8 if moving_piece < 6 else ((move >> 6) & 0x3F) + 8
            state.captured_square = capture_sq
            state.captured_piece = self.piece_at(capture_sq)

        if state.captured_piece is not None:
            self.zobrist_hash ^= self.keys[state.captured_piece * 64 + ((move >> 6) & 0x3F)]
            self.remove_piece(state.captured_piece, ((move >> 6) & 0x3F))

        self.move_piece(moving_piece, (move & 0x3F), ((move >> 6) & 0x3F))
        self.zobrist_hash ^= self.keys[moving_piece * 64 + ((move >> 6) & 0x3F)]

        for i in range(4):
            if self.castling_rights & (1 << i):
                self.zobrist_hash ^= self.keys[769 + i]


        self.castling_rights &= CASTLING_MASKS[(move & 0x3F)]
        self.castling_rights &= CASTLING_MASKS[((move >> 6) & 0x3F)]

        for i in range(4):
            if self.castling_rights & (1 << i):
                self.zobrist_hash ^= self.keys[769 + i]

        if is_pawn or state.captured_piece is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if (is_pawn and abs((move & 0x3F) - ((move >> 6) & 0x3F)) == 16): # if a pawn moved two squares forward, set the en passant square
            self.ep_square = ((move & 0x3F) + ((move >> 6) & 0x3F)) // 2
            self.zobrist_hash ^= self.keys[773 + (self.ep_square % 8)]
        else:
            self.ep_square = -1

        self.zobrist_hash ^= self.keys[768]
        self.side_to_move ^= 1

        self.update_occupancy()
    
    def unmake_move(self):
        # decrease ply
        self.ply -= 1

        # save state
        state = self.history[self.ply]

        # get pos
        move = state.move

        moving_piece = state.moved_piece

        if moving_piece is None:
            raise ValueError(f"No piece on square {((move >> 6) & 0x3F)}")

        if state.promotion_piece is not None:
            self.remove_piece(state.promotion_piece, ((move >> 6) & 0x3F))
            self.add_piece(moving_piece, ((move >> 6) & 0x3F))

        # undo move
        self.move_piece(moving_piece, ((move >> 6) & 0x3F), (move & 0x3F))

        if state.captured_piece is not None:
            self.add_piece(state.captured_piece, state.captured_square)

        # state restoration
        self.castling_rights = state.castling_rights
        self.ep_square = state.ep_square
        self.halfmove_clock = state.halfmove_clock
        self.zobrist_hash = state.zobrist_hash # no xors needed


        self.side_to_move ^= 1

        self.update_occupancy()
"""

"""
    
    # 0-63 correspond to white pawns
    # 64-127 correspond to white knights
    # 128-191 correspond to white bishops
    # 192-255 correspond to white rooks
    # 256-319 correspond to white queens
    # 320-383 correspond to white kings (only 1 but need a number)
    # 384-447 correspond to black pawns
    # 448-511 correspond to black knights
    # 512-575 correspond to black bishops
    # 576-639 correspond to black rooks
    # 640-703 correspond to black queens
    # 704-767 correspond to black kings (only 1 but need a number)
    # 768 for which side to move (0 for white, 1 for black)
    # 769-773 for castling rights (white kingside, white queenside, black kingside, black queenside)
    # 773-781 for en passant files (if any)

    def compute_hash(self) -> int:
        r = rkiss.RKISS(seed = 67676767)
        self.keys = [r.rand64() for _ in range(781)]
        hash = 0
        for piece in range(12):
            bb = self.pieces[piece]
            while bb:
                square, bb = Bitboard.pop_lsb(bb)
                hash ^= self.keys[piece * 64 + square]
                #print(piece * 64 + square, piece, square, hash)
        hash ^= self.keys[768] if self.side_to_move == core.types.BLACK else 0
        for i in range(4):
            if self.castling_rights & (1 << i): # just goes through the bitmap
                hash ^= self.keys[769 + i]
        if self.ep_square != -1:
            file = self.ep_square % 8
            hash ^= self.keys[773 + file]
        
        return hash
"""