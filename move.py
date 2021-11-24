from __future__ import annotations

import board_representation
import piece


# bit 0-5: from square (0 to 63)
# bit 6-11: to square (0 to 63)
# bit 12-15: flag


class Move:
    class Flag:
        NONE = 0
        EN_PASSANT_CAPTURE = 1
        CASTLING = 2
        PROMOTE_TO_QUEEN = 3
        PROMOTE_TO_KNIGHT = 4
        PROMOTE_TO_ROOK = 5
        PROMOTE_TO_BISHOP = 6
        PAWN_TWO_FORWARD = 7

    _START_SQUARE_MASK = 0b0000000000111111
    _TARGET_SQUARE_MASK = 0b0000111111000000
    _FLAG_MASK = 0b1111000000000000

    def __init__(self, move_value: int = None, start_square: int = None, target_square: int = None, flag: int = None):
        if start_square is None:
            self._move_value = move_value
        elif flag is None:
            self._move_value = start_square | target_square << 6
        else:
            self._move_value = start_square | target_square << 6 | flag << 12

    @property
    def value(self) -> int:
        return self._move_value

    @property
    def name(self) -> str:
        return board_representation.square_name_from_index(self.start_square) + "-" \
               + board_representation.square_name_from_index(self.target_square)

    @property
    def start_square(self) -> int:
        return self._move_value & self._START_SQUARE_MASK

    @property
    def target_square(self) -> int:
        return (self._move_value & self._TARGET_SQUARE_MASK) >> 6

    @property
    def move_flag(self) -> int:
        return self._move_value >> 12

    @property
    def is_promotion(self) -> bool:
        flag = self.move_flag
        return flag == self.Flag.PROMOTE_TO_QUEEN \
            or flag == self.Flag.PROMOTE_TO_ROOK \
            or flag == self.Flag.PROMOTE_TO_KNIGHT \
            or flag == self.Flag.PROMOTE_TO_BISHOP

    @property
    def is_en_passant(self) -> bool:
        return self.move_flag == self.Flag.EN_PASSANT_CAPTURE

    @property
    def is_invalid(self) -> bool:
        return self._move_value == 0

    @property
    def promotion_piece_type(self) -> int:
        flag = self.move_flag
        if flag == self.Flag.PROMOTE_TO_ROOK:
            return piece.ROOK
        if flag == self.Flag.PROMOTE_TO_KNIGHT:
            return piece.KNIGHT
        if flag == self.Flag.PROMOTE_TO_BISHOP:
            return piece.BISHOP
        if flag == self.Flag.PROMOTE_TO_QUEEN:
            return piece.QUEEN
        return piece.NONE

    @staticmethod
    def get_invalid_move() -> Move:
        return Move(0)

    @staticmethod
    def is_same(a: Move, b: Move) -> bool:
        return a._move_value == b._move_value

