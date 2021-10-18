import piece


class Board:

    squares = [None] * 64
    directional_offsets = {8, -8, -1, 1, 7, -7, 9, -9}
    num_squares_to_edge = [[None] * 8] * 64

    colour_to_move = piece.WHITE

    def __init__(self):
        print(self.num_squares_to_edge)

    @staticmethod
    def contains_square(bitboard, square):
        return ((bitboard >> square) & 1) != 0

    def precompute_move_data(self):
        for file in range(8):
            for rank in range(8):
                num_north = 7 - rank
                num_south = rank
                num_west = file
                num_east = 7 - file

                index = rank * 8 + file

                self.num_squares_to_edge[index] = [num_north, num_south, num_west, num_east,
                                                   min(num_north, num_west), min(num_south, num_east),
                                                   min(num_north, num_east), min(num_south, num_west)]



def main():
    board = Board()
    board.load_position_from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    for i in range(len(board.squares)):
        print(board.squares[i], end=' ')
        if (i + 1) % 8 == 0:
            print()


if __name__ == "__main__":
    main()
