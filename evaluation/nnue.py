import os
import struct

import numpy as np
from core import types
from core.bitboard import Bitboard

# architecture specifications for my nnue file format
INPUT_SIZE = 768 # 12 pieces * 64 squares
LAYER1_SIZE = 1024

SCALE = 400 # quantization divider scale factor

QA = 255
QB = 64
QAB = QA * QB

_DEFAULT_NNUE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nets", "bunnynator.nnue"
)

class NNUE:
    MAX_STACK_DEPTH = 256

    def __init__(self, model_path: str, l1_size: int = LAYER1_SIZE):
        self.input_size = 768
        self.l1_size = l1_size

        self.ft_weights = None
        self.ft_biases = None
        self.out_weights = None
        self.out_bias = None

        self.acc_white = np.zeros(self.l1_size, dtype=np.int32)
        self.acc_black = np.zeros(self.l1_size, dtype=np.int32)

        self._stack_white = np.zeros((self.MAX_STACK_DEPTH, self.l1_size), dtype=np.int32)
        self._stack_black = np.zeros((self.MAX_STACK_DEPTH, self.l1_size), dtype=np.int32)
        self._stack_ptr = 0

        if model_path is None:
            model_path = _DEFAULT_NNUE_PATH
        #else:
        #    print('error model path is none')
        #    print(model_path)
        if os.path.exists(model_path):
            self.load_binary_weights(model_path)

        self.out_weights_white = self.out_weights[:self.l1_size]
        self.out_weights_black = self.out_weights[self.l1_size:]

        

        #print(self.out_bias)
        #print(self.out_weights.shape)
        #print(self.ft_weights.shape)

    def push(self):
        if self._stack_ptr >= len(self._stack_white):
            self._grow_stack()
        self._stack_white[self._stack_ptr] = self.acc_white
        self._stack_black[self._stack_ptr] = self.acc_black
        self._stack_ptr += 1

    def pop(self):
        self._stack_ptr -= 1

        self.acc_white[:] = self._stack_white[self._stack_ptr]
        self.acc_black[:] = self._stack_black[self._stack_ptr]

    def _grow_stack(self):
        depth = len(self._stack_white) * 2
        self._stack_white = np.resize(self._stack_white, (depth, self.l1_size))
        self._stack_black = np.resize(self._stack_black, (depth, self.l1_size))

    def reset_stack(self):
        self._stack_ptr = 0

    def load_binary_weights(self, path: str):
        with open(path, "rb") as f:
            ft_w_elements = self.input_size * self.l1_size
            self.ft_weights = np.frombuffer(f.read(ft_w_elements * 2), dtype=np.int16).reshape(self.input_size, self.l1_size)
            self.ft_biases = np.frombuffer(f.read(self.l1_size * 2), dtype=np.int16)
            self.out_weights = np.frombuffer(f.read(self.l1_size * 2 * 2), dtype=np.int16)
            self.out_bias = np.frombuffer(f.read(2), dtype=np.int16)[0]

        #print(self.ft_weights.shape)
        #print(self.ft_biases.shape)
        #print(self.out_weights.shape)
        #print(self.out_bias)

    def update(self, removed, added):
        for piece, sq in removed:
            w = self.get_feature_index(piece, sq, types.WHITE)
            b = self.get_feature_index(piece, sq, types.BLACK)
            
            self.acc_white = self.acc_white - self.ft_weights[w]
            self.acc_black = self.acc_black - self.ft_weights[b]

        for piece, sq in added:
            w = self.get_feature_index(piece, sq, types.WHITE)
            b = self.get_feature_index(piece, sq, types.BLACK)
            
            self.acc_white = self.acc_white + self.ft_weights[w]
            self.acc_black = self.acc_black + self.ft_weights[b]

    def refresh_from_pos(self, pos):
        self.acc_white = self.ft_biases.astype(np.int32)
        self.acc_black = self.ft_biases.astype(np.int32)

        for piece_idx in range(12):
            bb = pos.pieces[piece_idx]
            while bb:
                sq, bb = Bitboard.pop_lsb(bb)

                w_idx = self.get_feature_index(piece_idx, sq, types.WHITE)
                b_idx = self.get_feature_index(piece_idx, sq, types.BLACK)

                #print("REFRESH", piece_idx, sq, self.get_feature_index(piece_idx, sq, types.WHITE), self.get_feature_index(piece_idx, sq, types.BLACK))
                self.acc_white += self.ft_weights[w_idx]
                self.acc_black += self.ft_weights[b_idx]
        return {
            "white": self.acc_white.copy(),
            "black": self.acc_black.copy()
        }

    def evaluate(self, pos):
        aw = np.clip(self.acc_white, 0, QA)
        ab = np.clip(self.acc_black, 0, QA)

        aw *= aw
        ab *= ab

        if pos.side_to_move == types.WHITE:
            raw = np.dot(aw, self.out_weights_white) + np.dot(ab, self.out_weights_black)
        else:
            raw = np.dot(ab, self.out_weights_white) + np.dot(aw, self.out_weights_black)

        raw //= QA
        score = int((raw + self.out_bias) * SCALE // QAB)

        return score if pos.side_to_move == types.WHITE else -score

    def get_feature_index(self, piece: int, square: int, perspective_color: int) -> int:
        if perspective_color == types.BLACK:
            square ^= 56
            if piece < 6:
                piece += 6
            else:
                piece -= 6

        return (piece * 64) + square
