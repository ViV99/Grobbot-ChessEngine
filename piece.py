NONE = 0
KING = 1
PAWN = 2
KNIGHT = 3
BISHOP = 5
ROOK = 6
QUEEN = 7

WHITE = 8
BLACK = 16

_TYPE_MASK = 0b00111
_BLACK_MASK = 0b10000
_WHITE_MASK = 0b01000
_COLOUR_MASK = _WHITE_MASK | _BLACK_MASK


def is_colour(piece: int, colour: int) -> bool:
    return (piece & _COLOUR_MASK) == colour


def piece_colour(piece: int) -> int:
    return piece & _COLOUR_MASK


def piece_type(piece: int) -> int:
    return piece & _TYPE_MASK


def is_rook_or_queen(piece: int) -> bool:
    return (piece & 0b110) == 0b110


def is_bishop_or_queen(piece: int) -> bool:
    return (piece & 0b101) == 0b101


def is_sliding_piece(piece: int) -> bool:
    return (piece & 0b100) != 0

