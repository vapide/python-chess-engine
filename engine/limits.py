class SearchLimits:
    def __init__(self):
        self.depth = None
        self.movetime = None
        self.nodes = None

        self.wtime = None
        self.btime = None
        self.winc = 0
        self.binc = 0

        self.movestogo = None

        self.infinite = False
        self.mate = None

        self.ponder = False
        self.perft = None
        
        self.searchmoves = None