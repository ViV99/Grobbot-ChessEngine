import piece
from move_generator import MoveGenerator
from board import Board


def main():
    board = Board()
    board.load_start_position()
    generator = MoveGenerator()
    moves = generator.generate_moves(board)
    for m in moves:
        print(m.start_square, m.target_square, m.is_promotion, m.is_en_passant, m.value)
    # board = Board()
    # board.load_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    # for i in range(len(board.squares)):
    #     print(board.squares[i], end=' ')
    #     if (i + 1) % 8 == 0:
    #         print()


if __name__ == "__main__":
    main()
