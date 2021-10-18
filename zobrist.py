from queue import Queue
from board import Board

import random
import os

import piece


SEED = 2361912
RANDOM_NUMBERS_FILE_NAME = "RandomNumbers.txt"

# piece type, colour, square index
pieces_array = [[[0] * 8] * 2] * 64
castling_rights = [0] * 16

# ep file (0 = no ep).
en_passant_file = [0] * 9  # no need for rank info as side to move is included in key
side_to_move = 0

_rnd = random.Random(SEED)


def main():
    global side_to_move

    random_numbers = _read_random_numbers()

    for square_index in range(64):
        for piece_index in range(8):
            pieces_array[piece_index][Board.WHITE_INDEX][square_index] = random_numbers.get()
            pieces_array[piece_index][Board.BLACK_INDEX][square_index] = random_numbers.get()

    for i in range(16):
        castling_rights[i] = random_numbers.get()

    for i in range(len(en_passant_file)):
        en_passant_file[i] = random_numbers.get()

    side_to_move = random_numbers.get()


def _random_numbers_path() -> str:
    return os.path.join(os.getcwd(), RANDOM_NUMBERS_FILE_NAME)


def _write_random_numbers() -> None:
    _rnd.seed(SEED)
    random_number_string = ''
    num_random_numbers = 64 * 8 * 2 + len(castling_rights) + 9 + 1

    for i in range(num_random_numbers):
        random_number_string += _random_unsigned_64_bit_number()
        if i != num_random_numbers - 1:
            random_number_string += ','

    with open(_random_numbers_path(), 'w') as file:
        file.write(random_number_string)


def _read_random_numbers() -> Queue:
    if not os.path.exists(_random_numbers_path()):
        _write_random_numbers()
    random_numbers = Queue()
    with open(_random_numbers_path(), 'r') as file:
        data = file.read()
        number_strings = data.split(',')
        for i in number_strings:
            number = int(i)
            random_numbers.put(number)
        return random_numbers


# Calculate zobrist key from current board position. This should only be used after setting board from fen;
# during search the key should be updated incrementally
def calculate_zobrist_key(board: Board) -> int:
    zobrist_key = 0

    for square_index in range(64):
        if board.squares[square_index] != 0:
            piece_type = piece.piece_type(board.squares[square_index])
            piece_colour = piece.piece_colour(board.squares[square_index])

            zobrist_key ^= pieces_array[piece_type][board.WHITE_INDEX if piece_colour == piece.WHITE else board.BLACK_INDEX][square_index]

    ep_index = (board.current_game_state >> 4) & 15
    if ep_index != -1:
        zobrist_key ^= en_passant_file[ep_index]

    if board.colour_to_move == piece.BLACK:
        zobrist_key ^= side_to_move

    zobrist_key ^= castling_rights[board.current_game_state & 0b1111]

    return zobrist_key


def _random_unsigned_64_bit_number() -> int:
    return _rnd.getrandbits(64)


main()
