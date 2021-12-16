import piece
from move import Move
from move_generator import MoveGenerator
from board import Board
from ai_settings import AISettings
from search import Search
import time


def main():
    board = Board()
    # 8/4k3/2K5/8/3P4/8/8/8 w - - 0 1
    board.load_start_position()
    # settings = AISettings()
    # s = Search(board, settings)
    # s.start_search()
    # m = s.get_search_result()[0]
    # print(m.start_square, m.target_square)
    while True:
        print('Enter move:')
        start, end, t = input().split()
        mv = Move(None, int(start), int(end), int(t))
        board.make_move(mv, False)

        settings = AISettings()
        s = Search(board, settings)
        if board.ply_count < 10:
            settings.depth = 3

        s.start_search()
        mv_bot, ev = s.get_search_result()
        print(f'Engine move: {mv_bot.start_square} {mv_bot.target_square} {mv_bot.move_flag}')
        board.make_move(mv_bot, False)


if __name__ == "__main__":
    main()
