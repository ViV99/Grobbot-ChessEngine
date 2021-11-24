
# (N, S, W, E, NW, SE, NE, SW)
import math

import board_representation
from board import Board

direction_offsets = [8, -8, -1, 1, 7, -7, 9, -9]

# Stores number of moves available in each of the 8 directions for every square on the board
# Order of directions is: N, S, W, E, NW, SE, NE, SW
num_squares_to_edge = [[0] * 8] * 64

# Stores array of indices for each square a knight can go to from any square on the board
# knight_moves[0] is equal to {10, 17}, meaning a knight on a1 can jump to c2 and b3
knight_moves = [[0] * 8] * 64
king_moves = [[0] * 8] * 64

# Pawn attack directions for white and black (NW NE SW SE)
pawn_attack_directions = [[4, 6], [7, 5]]

direction_lookup = [0] * 127
pawn_attacks_white = [[0] * 8] * 64
pawn_attacks_black = [[0] * 8] * 64

king_attack_bitboards = [0] * 64
knight_attack_bitboards = [0] * 64
pawn_attack_bitboards = [[0] * 2] * 64

rook_moves = [0] * 64
bishop_moves = [0] * 64
queen_moves = [0] * 64

# Manhattan distance - how many moves for a rook to get from square to square
orthogonal_distance = [[0] * 64] * 64
# Chebyshev distance - how many moves for a king to get from square to square
king_distance = [[0] * 64] * 64
center_manhattan_distance = [0] * 64


def num_orthogonal_moves_to_square(start_square: int, target_square: int) -> int:
    return orthogonal_distance[start_square][target_square]


def num_king_moves_to_square(start_square: int, target_square: int) -> int:
    return king_distance[start_square][target_square]


def _precomputed_move_data() -> None:
    # Calculate knight jumps and available squares for each square on the board
    all_knight_jumps = [15, 17, -17, -15, 10, -6, 6, -10]

    for square_index in range(64):
        y = square_index >> 3
        x = square_index - (y << 3)

        north = 7 - y
        south = y
        west = x
        east = 7 - x

        num_squares_to_edge[square_index][0] = north
        num_squares_to_edge[square_index][1] = south
        num_squares_to_edge[square_index][2] = west
        num_squares_to_edge[square_index][3] = east
        num_squares_to_edge[square_index][4] = min(north, west)
        num_squares_to_edge[square_index][5] = min(south, east)
        num_squares_to_edge[square_index][6] = min(north, east)
        num_squares_to_edge[square_index][7] = min(south, west)

        # Calculate all squares knight can jump to from current square
        legal_knight_jumps = []
        knight_bitboard = 0
        for knight_jump_delta in all_knight_jumps:
            knight_jump_square = square_index + knight_jump_delta
            if 0 <= knight_jump_square < 64:
                knight_square_y = knight_jump_square >> 3
                knight_square_x = knight_jump_square - (knight_square_y << 3)
                # Ensure knight has moved max of 2 squares on x/y axis (to reject indices that have wrapped around side of board)
                max_coord_move_dst = max(abs(x - knight_square_x), abs(y - knight_square_y))
                if max_coord_move_dst == 2:
                    legal_knight_jumps.append(knight_jump_square)
                    knight_bitboard |= (1 << knight_jump_square)

        knight_moves[square_index] = legal_knight_jumps
        knight_attack_bitboards[square_index] = knight_bitboard

        # Calculate all squares king can move to from current square (not including castling)
        legal_king_moves = []
        for king_move_delta in direction_offsets:
            king_move_square = square_index + king_move_delta
            if 0 <= king_move_square < 64:
                king_square_y = king_move_square >> 3
                king_square_x = king_move_square - (king_square_y << 3)
                # Ensure king has moved max of 1 square on x/y axis (to reject indices that have wrapped around side of board)
                max_coord_move_dst = max(abs(x - king_square_x), abs(y - king_square_y))
                if max_coord_move_dst == 1:
                    legal_king_moves.append(king_move_square)
                    king_attack_bitboards[square_index] |= (1 << king_move_square)

        king_moves[square_index] = legal_king_moves

        # Calculate legal pawn captures for white and black
        pawn_captures_white = []
        pawn_captures_black = []
        pawn_attack_bitboards[square_index] = [0] * 2
        if x > 0:
            if y < 7:
                pawn_captures_white.append(square_index + 7)
                pawn_attack_bitboards[square_index][Board.WHITE_INDEX] |= (1 << (square_index + 7))
            if y > 0:
                pawn_captures_black.append(square_index - 9)
                pawn_attack_bitboards[square_index][Board.BLACK_INDEX] |= (1 << (square_index - 9))
        if x < 7:
            if y < 7:
                pawn_captures_white.append(square_index + 9)
                pawn_attack_bitboards[square_index][Board.WHITE_INDEX] |= (1 << (square_index + 9))
            if y > 0:
                pawn_captures_black.append(square_index - 7)
                pawn_attack_bitboards[square_index][Board.BLACK_INDEX] |= (1 << (square_index - 7))

        pawn_attacks_white[square_index] = pawn_captures_white
        pawn_attacks_black[square_index] = pawn_captures_black

        # Rook moves
        for direction_index in range(4):
            current_dir_offset = direction_offsets[direction_index]
            for i in range(num_squares_to_edge[square_index][direction_index]):
                target_square = square_index + current_dir_offset * (i + 1)
                rook_moves[square_index] |= (1 << target_square)

        # Bishop moves
        for direction_index in range(4, 8):
            current_dir_offset = direction_offsets[direction_index]
            for i in range(num_squares_to_edge[square_index][direction_index]):
                target_square = square_index + current_dir_offset * (i + 1)
                bishop_moves[square_index] |= (1 << target_square)

        queen_moves[square_index] = rook_moves[square_index] | bishop_moves[square_index]

    for i in range(127):
        offset = i - 63
        abs_offset = abs(offset)
        abs_dir = 1
        if abs_offset % 9 == 0:
            abs_dir = 9
        elif abs_offset % 8 == 0:
            abs_dir = 8
        elif abs_offset % 7 == 0:
            abs_dir = 7
        direction_lookup[i] = abs_dir * int(math.copysign(1, offset))

    # Distance lookup
    for square_a in range(64):
        coord_a = board_representation.coord_from_index(square_a)
        file_dst_from_center = max(3 - coord_a.file_index, coord_a.file_index - 4)
        rank_dst_from_center = max(3 - coord_a.rank_index, coord_a.rank_index - 4)
        center_manhattan_distance[square_a] = file_dst_from_center + rank_dst_from_center

        for square_b in range(64):
            coord_b = board_representation.coord_from_index(square_b)
            rank_distance = abs(coord_a.rank_index - coord_b.rank_index)
            file_distance = abs(coord_a.file_index - coord_b.file_index)
            orthogonal_distance[square_a][square_b] = file_distance + rank_distance
            king_distance[square_a][square_b] = max(file_distance, rank_distance)


_precomputed_move_data()
