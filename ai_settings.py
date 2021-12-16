from move_generator import MoveGenerator


class AISettings:

    def __init__(self):
        self.depth = 4
        self.use_iterative_deepening = False
        self.use_tt = True
        self.use_threading = False
        self.use_fixed_depth_search = False
        self.endless_search_mode = False
        self.search_time_ms = 1000
        self.clear_tt_each_move = False
        self.promotions_to_search = MoveGenerator.PromotionMode.QUEEN_ONLY

        # self.use_book = True
        # self.book =
        # self.max_book_ply = 10
