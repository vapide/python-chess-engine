from engine.uci import main

if __name__ == "__main__":
    main()

"""
run_perft(
    "kiwipete", 
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 
    expected={1: 48, 2: 2039, 3: 97862, 4: 4085603}, 
    depths=(1, 2, 3, 4)
)

run_perft(
    "position 5",
    "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8  ",
    expected={1: 44, 2: 1486, 3:62379, 4: 2103487},
    depths=(1, 2, 3, 4)
)

run_perft(
    "position 3", 
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 
    expected={1: 14, 2: 191, 3: 2812, 4: 43238, 5: 674624}, 
    depths=(1, 2, 3, 4, 5)
)


run_perft("start position", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", expected={4: 197281, 5: 4865609}, depths=(4, 5)) # short 258 on depth 5 which is the exact number of en passant captures for that depth
"""