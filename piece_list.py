
class PieceList:

    # Occupied_squares - indices of squares occupied by given piece type
    # (only elements up to Count are valid, the rest are unused/garbage)
    # Map - to go from index of a square, to the index in the occupied_squares array where that square is stored

    def __init__(self, max_piece_count=16):
        self.occupied_squares = [0] * max_piece_count
        self._map = [0] * 64
        self._num_pieces = 0

    def __getitem__(self, index: int) -> int:
        return self.occupied_squares[index]

    @property
    def count(self) -> int:
        return self._num_pieces

    def add_piece_at_square(self, square: int) -> None:
        self.occupied_squares[self._num_pieces] = square
        self._map[square] = self._num_pieces
        self._num_pieces += 1

    def remove_piece_at_square(self, square: int) -> None:
        piece_index = self._map[square]  # Get the index of this element in the occupied_squares array
        self.occupied_squares[piece_index] = self.occupied_squares[self._num_pieces - 1]  # Move last element in array to the place of the removed element
        self._map[self.occupied_squares[piece_index]] = piece_index  # Update map to point to the moved element's new location in the array
        self._num_pieces -= 1

    def move_piece(self, start_square: int, target_square: int):
        piece_index = self._map[start_square]
        self.occupied_squares[piece_index] = target_square
        self._map[target_square] = piece_index
