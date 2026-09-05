import threading

from core.position import Position
from evaluation.nnue import NNUE, find_nnue
from search.search import Search
from search.transposition import TranspositionTable
from testing.perft import perft


class Engine:
    DEFAULT_NNUE_FILE = find_nnue()

    def __init__(self):
        self.nnue = NNUE(self.DEFAULT_NNUE_FILE)
        self.board = Position.startpos(nnue_instance=self.nnue)
        self.search = Search(nnue_instance=self.nnue)

        self.options = {
            "Hash": TranspositionTable.DEFAULT_SIZE_MB,
            "Threads": 1,
            "NNUE": True,
            "Aggression": 50,
            "Move Overhead": Search.DEFAULT_MOVE_OVERHEAD_MS,
            "Ponder": True,
        }
        self.search.tt.resize(self.options["Hash"])

        self._search_thread = None

    def think_async(self, limits, on_complete):
        def _run():
            self.search.stop = False
            best_move = self.search.find_best_move(self.board, limits)
            on_complete(best_move, self.search.last_ponder_move)

        self._search_thread = threading.Thread(target=_run, daemon=True)
        self._search_thread.start()

    def is_searching(self):
        return self._search_thread is not None and self._search_thread.is_alive()

    def ponder_hit(self):
        self.search.ponder_hit()

    def perft(self, depth):
        return perft(self.board, depth)

    def new_game(self):
        self.board = Position.startpos(nnue_instance=self.nnue)
        self.nnue.refresh_from_pos(self.board)
        self.search.tt.clear()

    def set_option(self, name, value):
        name = name.strip()
        if name == "Hash":
            self.options[name] = int(value)
            self.search.tt.resize(self.options[name])
        elif name == "Aggression":
            # 0 to 100 range
            self.options[name] = int(value)
            self.search.aggression = self.options[name]
        elif name == "Move Overhead":
            self.options[name] = int(value)
            self.search.move_overhead_ms = self.options[name]
        elif name in ("Threads",):
            self.options[name] = int(value)
        elif name in ("NNUE", "Ponder"):
            self.options[name] = (value.lower() == "true")

    def stop_search(self):
        self.search.stop = True
