from core.move import to_uci
from core.position import Position
from movegen.move_generator import MoveGenerator
import core.types

def perft(pos, depth):
    if depth == 0:
        return 1
    nodes = 0
    for move in MoveGenerator.generate_legal_moves(pos):
        pos.make_move(move)
        nodes += perft(pos, depth - 1)
        pos.unmake_move()
    return nodes


def perft_divide(pos, depth: int): # returns list of tuples for moves
    if depth < 0:
        raise ValueError(f"depth must be >= 0, got {depth}")
    if depth == 0:
        return []
    results = []
    for move in MoveGenerator.generate_pseudo_legal_moves(pos):
        us = pos.side_to_move
        pos.make_move(move)
        try:
            if not MoveGenerator.in_check(pos, us):
                nodes = perft(pos, depth - 1)
                results.append((move, nodes))
        finally:
            pos.unmake_move()
    return results


def run_perft(name: str, fen: str, expected: dict[int, int] | None = None, depths=(1, 2)):
    pos = Position.from_fen(fen)

    #print(f"\n{'='*40}")
    #print(f" TESTING: {name}")
    #print(f" FEN:     {pos.to_fen()}")

    for depth in depths:
        #print(f"\n--- Running Perft Depth {depth} ---")
        
        total_nodes = 0
        moves_checked = 0
        
        for move in MoveGenerator.generate_legal_moves(pos):
            flags = (move >> 12) & 0xF
            us = pos.side_to_move
            enemy = core.types.BLACK if us == core.types.WHITE else core.types.WHITE

            # CRITICAL: Replicate the perft castling safety constraints at the root
            if flags & (core.types.CASTLE | core.types.CASTLE): # Use your exact flag mask here
                if MoveGenerator.in_check(pos, us):
                    continue

                if flags & core.types.CASTLE: # Match your King vs Queen side logic
                    transit_sq = core.types.F1 if us == core.types.WHITE else core.types.F8
                else:
                    transit_sq = core.types.D1 if us == core.types.WHITE else core.types.D8
                    
                if MoveGenerator.is_square_attacked(pos, transit_sq, enemy):
                    continue

            pos.make_move(move)
            try:
                if not MoveGenerator.in_check(pos, us):
                    branch_nodes = perft(pos, depth - 1)
                    total_nodes += branch_nodes
                    moves_checked += 1
                    
                    # Print each root move outcome for debugging (Divide)
                    #print(f"{to_uci(move)}: {branch_nodes}") 
            finally:
                pos.unmake_move()

        # Output Summary Block
        line = f"Depth {depth} Total: {total_nodes} nodes (from {moves_checked} legal root moves)"
        if expected and depth in expected:
            line += f" | Expected: {expected[depth]}"
            print(line)
            assert total_nodes == expected[depth], (
                f"{name} depth {depth} failed: Got {total_nodes}, Expected {expected[depth]}"
            )
        else:
            print(line)

"""
def run_perft(name: str, fen: str, expected: dict[int, int] | None = None, depths=(3, 4)):
    pos = Position.from_fen(fen)

    print(f"\n{name}")
    print(pos.to_fen())

    for depth in depths:
        nodes = perft(pos, depth)
        line = f"depth {depth}: {nodes}"
        if expected and depth in expected:
            line += f"  expected {expected[depth]}"
            assert nodes == expected[depth], (
                f"{name} depth {depth}: got {nodes}, expected {expected[depth]}"
            )
        print(line)
"""