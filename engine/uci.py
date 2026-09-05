import sys
from core.move import from_uci, to_uci
from core.position import Position
from engine.engine import Engine
from engine.limits import SearchLimits
from movegen.move_generator import MoveGenerator

class UCI:
    def __init__(self, input_stream=None, output_stream=None):
        self.input_stream = input_stream or sys.stdin
        self.output_stream = output_stream or sys.stdout
        self.engine = Engine()

    def loop(self):
        for raw_line in self.input_stream:
            if not self.handle_command(raw_line.strip()):
                break

    def handle_command(self, line):
        if not line:
            return True

        parts = line.split()
        command = parts[0]

        match command:
            case "uci":
                self._handle_uci()
            case "isready":
                self._write("readyok")
            case "ucinewgame":
                self.engine.new_game()
            case "position":
                self._handle_position(parts[1:])
            case "go":
                self._handle_go(parts[1:])
            case "setoption":
                self._handle_setoption(parts[1:])
            case "bench":
                #self._handle_bench()
                pass
            case "help":
                self._handle_help(parts[1:])
            case "stop":
                self.engine.stop_search()
            case "ponderhit":
                self.engine.ponder_hit()
            case "quit":
                self.engine.stop_search()
                return False
            case "d":
                self.engine.board.prettyPrint()
                self._write(self.engine.board.to_fen())

        return True

    def _handle_position(self, args):
        if not args:
            return

        move_index = None
        if "moves" in args:
            move_index = args.index("moves")
            position_args = args[:move_index]
            move_args = args[move_index + 1:]
        else:
            position_args = args
            move_args = []

        if position_args and position_args[0] == "startpos":
            board = Position.startpos(nnue_instance=self.engine.nnue)
            #print(self.engine.board.to_fen())
            #print(self.engine.board.zobrist.hash)
            #print(self.engine.board.side_to_move)
            #print(self.engine.board.castling_rights)
            #print(self.engine.board.ep_square)
            #print(self.engine.board.ply)
        elif position_args and position_args[0] == "fen":
            fen_parts = position_args[1:]
            if len(fen_parts) != 6:
                print('wrong fen size', flush=True)
                return
            board = Position.from_fen(" ".join(fen_parts), nnue_instance=self.engine.nnue)
        else:
            return
        for move_text in move_args:
            move = self._legal_move_from_uci(move_text, board)
            if move is None:
                print(f"info string Failed to parse or process move: {move_text}", flush=True)
                return
                self.engine.board = board
        self.engine.nnue.reset_stack()

    def _handle_go(self, args):
        limits = SearchLimits()
        i = 0
        while i < len(args):
            token = args[i]
            if token == "depth":
                if i + 1 < len(args):
                    try:
                        limits.depth = int(args[i + 1])
                    except ValueError:
                        pass
                    i += 1

            elif token == "movetime":
                if i + 1 < len(args):
                    try:
                        limits.movetime = int(args[i + 1])
                    except ValueError:
                        pass
                    i += 1
            elif token == "nodes":
                if i + 1 < len(args):
                    try:
                        limits.nodes = int(args[i + 1])
                    except ValueError:
                        pass
                    i += 1
            elif token == "wtime":
                if i + 1 < len(args):
                    limits.wtime = int(args[i + 1])
                    i += 1
            elif token == "btime":
                if i + 1 < len(args):
                    limits.btime = int(args[i + 1])
                    i += 1
            elif token == "winc":
                if i + 1 < len(args):
                    limits.winc = int(args[i + 1])
                    i += 1
            elif token == "binc":
                if i + 1 < len(args):
                    limits.binc = int(args[i + 1])
                    i += 1
            elif token == "movestogo":
                if i + 1 < len(args):
                    limits.movestogo = int(args[i + 1])
                    i += 1
            elif token == "mate":
                if i + 1 < len(args):
                    limits.mate = int(args[i + 1])
                    i += 1
            elif token == "infinite":
                limits.infinite = True
            elif token == "ponder":
                limits.ponder = True
            elif token == "perft":
                if i + 1 < len(args):
                    limits.perft = int(args[i+1])
                    i += 1
            elif token == "searchmoves":
                limits.searchmoves = []
                i += 1
                while i < len(args):
                    if args[i] in {
                        "depth",
                        "movetime",
                        "nodes",
                        "wtime",
                        "btime",
                        "mate",
                        "infinite",
                        "winc",
                        "binc",
                        "movestogo",
                        "searchmoves"
                    }:
                        i -= 1
                        break
                    limits.searchmoves.append(args[i])
                    i += 1
            i += 1

        if limits.perft:
            nodes = self.engine.perft(limits.perft)
            self._write(f"info nodes {nodes}")
            return

        if self.engine.is_searching():
            return

        def _on_complete(best_move, ponder_move):
            if best_move is None:
                self._write("bestmove 0000")
            elif ponder_move is not None:
                self._write(f"bestmove {to_uci(best_move)} ponder {to_uci(ponder_move)}")
            else:
                self._write(f"bestmove {to_uci(best_move)}")

        self.engine.think_async(limits, _on_complete)

    def _handle_setoption(self, args):
        if "name" not in args:
            return
        name_index = args.index("name")
        value_index = None
        if "value" in args:
            value_index = args.index("value")

        if value_index is not None:
            name = " ".join(args[name_index + 1:value_index])
            value = " ".join(args[value_index + 1:])
        else:
            name = " ".join(args[name_index + 1:])
            value = None

        self.engine.set_option(name, value)

    def _send_uci_options(self):
        from search.transposition import TranspositionTable
        self._write("option name Hash type spin default " + f"{TranspositionTable.DEFAULT_SIZE_MB} min 1 max 4096")
        self._write("option name Threads type spin default 1 min 1 max 64")
        self._write("option name NNUE type check default true")
        self._write("option name Aggression type spin default 50 min 0 max 100")
        self._write("option name Move Overhead type spin default 50 min 0 max 5000")
        self._write("option name Ponder type check default true")

    def _handle_uci(self):
        self._write("id name bunnynator6767")
        self._write("id author superbunnylover58 on insta")
        self._send_uci_options()
        self._write("uciok")

    def _legal_move_from_uci(self, move_text):
            try:
                parsed = from_uci(move_text)
                from_sq = parsed & 0x3F
                to_sq = (parsed >> 6) & 0x3F
                promotion = (parsed >> 16) & 0xF
            except ValueError:
                return None
            for move in MoveGenerator.generate_legal_moves(self.engine.board):
                if (
                    (move & 0x3F) == from_sq
                    and ((move >> 6) & 0x3F) == to_sq
                    and ((move >> 16) & 0xF) == promotion
                ):
                    return move
            return None

    def _handle_help(self, args):
        if not args:
            self._write("Available commands:")
            self._write("  uci")
            self._write("  isready")
            self._write("  ucinewgame")
            self._write("  position")
            self._write("  go")
            self._write("  stop")
            self._write("  ponderhit")
            self._write("  setoption")
            self._write("  bench")
            self._write("  perft")
            self._write("  d")
            self._write("  quit")
            self._write("")
            self._write("Type 'help <command>' for details.")
            return

        command = args[0]
        if command == "go":
            self._write("go options:")
            self._write("  depth <n>")
            self._write("  movetime <ms>")
            self._write("  nodes <n>")
            self._write("  wtime <ms>")
            self._write("  btime <ms>")
            self._write("  winc <ms>")
            self._write("  binc <ms>")
            self._write("  movestogo <n>")
            self._write("  mate <n>")
            self._write("  infinite")
            self._write("  ponder")
            self._write("  perft <depth>")
            self._write("  searchmoves <moves>")

        elif command == "setoption":
            self._write("setoption syntax:")
            self._write("  setoption name <option> value <value>")
            self._write("")
            self._write("Options:")
            self._write("  Hash")
            self._write("  Threads")
            self._write("  NNUE")
            self._write("  Aggression")
            self._write("  Move Overhead")
            self._write("  Ponder")

        elif command == "position":
            self._write("position syntax:")
            self._write("  position startpos")
            self._write("  position startpos moves e2e4 e7e5")
            self._write("  position fen <fen>")

        elif command == "perft":
            self._write("perft syntax:")
            self._write("  go perft <depth>")
            self._write("Example:")
            self._write("  go perft 5")

        elif command == "bench":
            self._write("bench runs a fixed search benchmark.")

        else:
            self._write(f"No help available for '{command}'")

    def _write(self, text):
        print(text, file=self.output_stream, flush=True)

def main():
    UCI().loop()

if __name__ == "__main__":
    main()
    
