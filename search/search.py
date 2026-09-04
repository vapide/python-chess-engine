# find best move() -> negamax() -> _order_moves() -> _quiescence()

import time

from core import types
from core.move import to_uci
from movegen.move_generator import MoveGenerator

from .aggression import AGG, aggression_score
from .see import see
from .transposition import EXACT, LOWER, UPPER, TranspositionTable

INF = 1000000
MATE = 900000
MAX_PLY = 64
MATE_THRESHOLD = MATE - MAX_PLY

# within this play the most "aggressive" one (centipawns)
TIE_MARGIN = 30

TT_MOVE, AGGRESSIVE_MOVE, GOOD_CAPTURE, QUIET = 1000000, 900000, 800000, 100000

def is_noisy(move):
    return bool((move >> 12) & (types.CAPTURE | types.EN_PASSANT) or (move >> 16) & 0xF)


class Search:
    DEFAULT_MOVE_OVERHEAD_MS = 50

    def __init__(self, nnue_instance=None):
        self.nnue = nnue_instance
        self.tt = TranspositionTable()
        self.move_overhead_ms = self.DEFAULT_MOVE_OVERHEAD_MS
        self.aggression = 50            # yci option, 0-100, scales the tie margin parameter
        self.stop = False
        self.nodes = 0
        self.last_score = 0
        self.last_ponder_move = None
        self.pondering = False
        self.limits = None
        self.time_limit_ms = None
        self.start_time = 0.0

    # public
    def find_best_move(self, pos, limits):
        self.stop = False
        self.nodes = 0
        self.limits = limits
        self.start_time = time.perf_counter()
        self.pondering = bool(getattr(limits, "ponder", False))
        self.nnue.refresh_from_pos(pos)
        self._set_time_limit(limits, pos.side_to_move)
        best_move = None
        max_depth = limits.depth or MAX_PLY - 1

        for depth in range(1, max_depth + 1):
            scored = self._search_root(pos, depth)
            if not scored:
                break                       # stopped, or no legal moves at all
            best_move = self._pick_root_move(pos, scored)
            self.last_score = max(score for score, _ in scored)
            self._print_info(pos, depth)
            if abs(self.last_score) > MATE_THRESHOLD or self._should_stop(limits):
                break

        if best_move is None:
            legal = MoveGenerator.generate_legal_moves(pos)
            best_move = legal[0] if legal else None
        return best_move

    def ponder_hit(self):
        self.pondering = False
        self.start_time = time.perf_counter()

    # root