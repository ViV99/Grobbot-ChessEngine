from __future__ import annotations


class Coord:
    def __init__(self, file_index: int, rank_index: int):
        self.file_index = file_index
        self.rank_index = rank_index

    def __ne__(self, other: Coord) -> bool:
        return self.file_index == other.file_index and self.rank_index == other.rank_index

    def is_light_square(self) -> bool:
        return (self.file_index + self.rank_index) % 2 != 0
