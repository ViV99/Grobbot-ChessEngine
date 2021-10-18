from coord import Coord


FILE_NAMES = 'abcdefgh'
RANK_NAMES = '12345678'

A1 = 0
B1 = 1
C1 = 2
D1 = 3
E1 = 4
F1 = 5
G1 = 6
H1 = 7

A8 = 56
B8 = 57
C8 = 58
D8 = 59
E8 = 60
F8 = 61
G8 = 62
H8 = 63


# Rank (0 to 7) of square
def get_rank_index(square_index: int) -> int:
    return square_index >> 3


# File (0 to 7) of square
def get_file_index(square_index: int) -> int:
    return square_index & 0b000111


def index_from_coord(file_index: int, rank_index: int) -> int:
    return rank_index * 8 + file_index


def index_from_coord(coord: Coord) -> int:
    return index_from_coord(coord.file_index, coord.rank_index)


def coord_from_index(square_index: int) -> Coord:
    return Coord(get_file_index(square_index), get_rank_index(square_index))


def is_light_square(file_index: int, rank_index: int) -> bool:
    return (file_index + rank_index) % 2 != 0


def square_name_from_coord(file_index: int, rank_index: int) -> str:
    return FILE_NAMES[file_index] + '' + str(rank_index + 1)


def square_name_from_coord(coord: Coord) -> str:
    return square_name_from_coord(coord.file_index, coord.rank_index)


def square_name_from_index(square_index: int) -> str:
    return square_name_from_coord(coord_from_index(square_index))
