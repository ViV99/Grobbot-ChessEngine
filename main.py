import piece
from move_generator import MoveGenerator
from board import Board


def main():
    board = Board()
    board.load_position('8/5k2/8/8/2n2b2/8/3K4/8 w - - 0 1')
    generator = MoveGenerator()
    moves = generator.generate_moves(board)
    for m in moves:
        print(m.start_square, m.target_square, m.is_promotion, m.is_en_passant, m.value)


if __name__ == "__main__":
    main()
