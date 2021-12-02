import os
import random
from queue import Queue

SEED = 2361912
RANDOM_NUMBERS_FILE_NAME = "RandomNumbers.txt"

# piece type, colour, square index
pieces_array = [[[0] * 64] * 2] * 8

castling_rights = [0] * 16

# ep file (0 = no ep).
en_passant_file = [0] * 9  # no need for rank info as side to move is included in key
side_to_move = 0

_rnd = random.Random(SEED)

_WHITE_INDEX = 0
_BLACK_INDEX = 1


def init():
    global side_to_move

    random_numbers = _read_random_numbers()

    for square_index in range(64):
        for piece_index in range(8):
            pieces_array[piece_index][_WHITE_INDEX][square_index] = random_numbers.get()
            pieces_array[piece_index][_BLACK_INDEX][square_index] = random_numbers.get()

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
        random_number_string += str(_random_unsigned_64_bit_number())
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


def _random_unsigned_64_bit_number() -> int:
    return _rnd.getrandbits(64)


init()
