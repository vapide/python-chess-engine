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

def material_gain(pos, move):
    # add see static exchange evaluation
    promotion = (move >> 16) & 0xF
    if (move >> 12) & types.EN_PASSANT:
        gain = tables.PIECE_VALUES[types.PAWN]
    else:
        victim = pos.mailbox[(move >> 6) & 0x3F]
        gain = tables.PIECE_VALUES[victim % 6] if victim is not None else 0
    if promotion:
        gain += tables.PIECE_VALUES[promotion] - tables.PIECE_VALUES[types.PAWN]
    return gain

def move_score(pos, move, tt_move):
    if move == tt_move:
        return TT_MOVE
    aggression = aggression_score(pos, move)
    if aggression >= AGGRESSIVE_MOVE:
        return AGGRESSIVE_MOVE + aggression * 1000
    if is_noisy(move):
        # add see and put clearly losing moves under quiet moves
        return GOOD_CAPTURE + material_gain(pos, move)
    return QUIET + aggression * 1000

def ordered_moves(pos, tt_move=None):
    moves = MoveGenerator.generate_legal_moves(pos)
    moves.sort(key=lambda move: move_score(pos, move, tt_move), reverse=True)
    return moves


def mate_adjust(score, ply):
    if score > MATE_THRESHOLD:
        return score + ply
    if score < -MATE_THRESHOLD:
        return score - ply
    return score

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
                break                       # stopped or no legal moves at all
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
    def _root(self, pos, depth):
        entry = self.tt.get(pos.zobrist.hash)
        margin = TIE_MARGIN * self.aggression // 50

        scored = []
        alpha = -INF
        for move in ordered_moves(pos, entry.move if entry else None):
            # alpha - tie
            # any move can win
            # rest fail low and that gets them rejected
            pos.make_move(move)
            score = -self._negamax(pos, depth - 1, -INF, -(alpha - margin), 1)
            pos.unmake_move()
            if self.stop:
                return None             # a partial score would be a lie
            scored.append((score, move))
            alpha = max(alpha, score)
        if not scored:
            return None

        best_score, best_move = max(scored, key=lambda pair: pair[0])
        self.tt.put(pos.zobrist.hash, depth, best_score, EXACT, best_move)

        # aggression tie breaker
        if margin and abs(best_score) <= MATE_THRESHOLD:
            near_best = [pair for pair in scored if best_score - pair[0] < margin]
            best_move = max(near_best, key=lambda pair: (aggression_score(pos, pair[1]), pair[0]))[1]
        return best_score, best_move

    def _negamax(self, pos, depth, alpha, beta, ply):
        self.nodes += 1
        if self._out_of_time():
            return alpha
        if pos.halfmove_clock >= 100 or pos.is_repetition() or pos.is_insufficient_material():
            return 0
        if depth <= 0 or ply >= MAX_PLY:
            return self._quiescence(pos, alpha, beta, ply)

        key = pos.zobrist.hash
        entry = self.tt.get(key)
        if entry is not None and entry.depth >= depth:
            score = mate_adjust(entry.score, -ply)
            if entry.flag == EXACT or (entry.flag == LOWER and score >= beta) or (entry.flag == UPPER and score <= alpha):
                return score

        moves = ordered_moves(pos, entry.move if entry else None)
        if not moves:
            return -MATE + ply if pos.in_check(pos.side_to_move) else 0

        original_alpha = alpha
        best_score, best_move = -INF, None
        for move in moves:
            pos.make_move(move)
            score = -self._negamax(pos, depth - 1, -beta, -alpha, ply + 1)
            pos.unmake_move()
            if self.stop:
                return alpha            # nothing is stored from a node that was cut short
            if score > best_score:
                best_score, best_move = score, move
                alpha = max(alpha, score)
                if alpha >= beta:
                    break

        flag = (LOWER if best_score >= beta else
                EXACT if best_score > original_alpha else UPPER)
        self.tt.put(key, depth, mate_adjust(best_score, ply), flag, best_move)
        return best_score

    def _quiescence(self, pos, alpha, beta, ply):
        self.nodes += 1
        if self._out_of_time():
            return alpha
        if ply >= MAX_PLY:
            return self._evaluate(pos)

        in_check = pos.in_check(pos.side_to_move)
        if in_check:
            best = -INF # in check before nothing
        else:
            best = self._evaluate(pos)
            if best >= beta:
                return best
            alpha = max(alpha, best)

        moves = MoveGenerator.generate_legal_moves(pos)
        if not moves:
            return -MATE + ply if in_check else 0
        if not in_check:
            # nothing is dropped meaning a sacrifice is refuted, or confirmed.
            # quiescence buys cutoffs and forcing moves costs a lot for no new results so add see and order by exchange value and skip losing moves and captures
            # that arent forcing
            moves = sorted((move for move in moves if is_noisy(move)), key=lambda move: material_gain(pos, move), reverse=True)

        for move in moves:
            pos.make_move(move)
            score = -self._quiescence(pos, -beta, -alpha, ply + 1)
            pos.unmake_move()
            if self.stop:
                return alpha
            if score > best:
                best = score
                alpha = max(alpha, score)
                if alpha >= beta:
                    break
        return best

    def _evaluate(self, pos):
        score = self.nnue.evaluate(pos)                  # pov of white
        return score if pos.side_to_move == types.WHITE else -score

    def _principal_variation(self, pos, limit=8):
        line = []
        while len(line) < limit:
            entry = self.tt.get(pos.zobrist.hash)
            if entry is None or entry.move is None or entry.move not in MoveGenerator.generate_legal_moves(pos):
                break
            line.append(entry.move)
            pos.make_move(entry.move)
        for _ in line:
            pos.unmake_move()
        return line

    def _report(self, pos, depth):
        line = self._principal_variation(pos)
        self.last_ponder_move = line[1] if len(line) > 1 else None
        elapsed = max(1e-6, time.perf_counter() - self.start_time)
        if abs(self.last_score) > MATE_THRESHOLD:
            moves = (MATE - abs(self.last_score) + 1) // 2
            score = f"mate {moves if self.last_score > 0 else -moves}"
        else:
            score = f"cp {self.last_score}"
        print(f"info depth {depth} score {score} nodes {self.nodes} " + f"nps {int(self.nodes / elapsed)} time {int(elapsed * 1000)}" + f"pv {' '.join(to_uci(move) for move in line)}", flush=True)

    def _set_time_limit(self, side_to_move):
        limits = self.limits
        self.time_limit_ms = None
        if limits.movetime is not None:
            self.time_limit_ms = max(1, limits.movetime - self.move_overhead_ms)
            return
        remaining = limits.wtime if side_to_move == types.WHITE else limits.btime
        if remaining is not None:
            increment = (limits.winc if side_to_move == types.WHITE else limits.binc) or 0
            budget = max(1, remaining - self.move_overhead_ms)
            self.time_limit_ms = budget / 30 + increment * 0.75

    def _time_up(self, fraction=1.0):
        if self.limits.nodes and self.nodes >= self.limits.nodes:
            return True
        if self.pondering or self.limits.infinite or self.time_limit_ms is None:
            return False
        return (time.perf_counter() - self.start_time) * 1000 >= self.time_limit_ms * fraction

    def _out_of_time(self):
        if not self.stop and not self.nodes & 1023 and self._time_up():
            self.stop = True
        return self.stop
