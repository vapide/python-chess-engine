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