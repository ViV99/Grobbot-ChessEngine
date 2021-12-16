from __future__ import annotations

from board import Board
from move import Move
import piece
import precomputed_move_data
import board_representation


class MoveGenerator:
    class PromotionMode:
        ALL = 0
        QUEEN_ONLY = 1
        QUEEN_AND_KNIGHT = 2

    __slots__ = {'_friendly_colour', '_white_to_move', '_friendly_king_square', '_opponent_colour', '_friendly_colour_index',
                 '_opponent_colour_index', '_moves', '_in_check', '_in_double_check', '_pins_exist',
                 '_check_ray_bitmask', '_pin_ray_bitmask', '_opponent_knight_attacks', '_opponent_attack_map_no_pawns',
                 'opponent_attack_map', 'opponent_pawn_attack_map', '_opponent_sliding_attack_map',  '_gen_quiets',
                 '_board', 'promotions_to_generate'}

    def __init__(self, promotions_to_generate: MoveGenerator.PromotionMode):
        self.promotions_to_generate = promotions_to_generate

    # Generates list of legal moves in current position
    # Quiet moves (non captures) can optionally be excluded
    def generate_moves(self, board: Board, include_quiet_moves=True) -> list[Move]:
        self._board = board
        self._gen_quiets = include_quiet_moves
        self._init()

        self._calculate_attack_data()
        self._generate_king_moves()

        # Only king moves are valid in a double check position, so can return early
        if self._in_double_check:
            return self._moves

        self._generate_sliding_moves()
        self._generate_knight_moves()
        self._generate_pawn_moves()

        return self._moves

    # Will only return correct value after generate_moves() has been called in the current position
    @property
    def in_check(self) -> bool:
        return self._in_check

    @property
    def _has_king_side_castle_right(self) -> bool:
        mask = 1 if self._board.white_to_move else 4
        return (self._board.current_game_state & mask) != 0

    @property
    def _has_queen_side_castle_right(self):
        mask = 2 if self._board.white_to_move else 8
        return (self._board.current_game_state & mask) != 0

    def _is_pinned(self, square: int) -> bool:
        return self._pins_exist and ((self._pin_ray_bitmask >> square) & 1) != 0

    def _square_is_attacked(self, square: int) -> bool:
        return MoveGenerator.contains_square(self.opponent_attack_map, square)

    def _square_is_in_check_ray(self, square: int) -> bool:
        return self._in_check and ((self._check_ray_bitmask >> square) & 1) != 0

    def _in_check_after_en_passant(self, start_square: int, target_square: int, ep_captured_pawn_square: int) -> bool:
        # Update board to reflect en-passant capture
        self._board.squares[target_square] = self._board.squares[start_square]
        self._board.squares[start_square] = piece.NONE
        self._board.squares[ep_captured_pawn_square] = piece.NONE

        in_check_after_ep_capture = False
        if self._is_square_attacked_after_ep_capture(ep_captured_pawn_square, start_square):
            in_check_after_ep_capture = True

        # Undo change to board
        self._board.squares[target_square] = piece.NONE
        self._board.squares[start_square] = piece.PAWN | self._friendly_colour
        self._board.squares[ep_captured_pawn_square] = piece.PAWN | self._opponent_colour
        return in_check_after_ep_capture

    def _is_square_attacked_after_ep_capture(self, ep_capture_square: int, capturing_pawn_start_square: int) -> bool:
        if self.contains_square(self._opponent_attack_map_no_pawns, self._friendly_king_square):
            return True

        # Loop through the horizontal direction towards ep capture to see if any enemy piece now attacks king
        dir_index = 2 if ep_capture_square < self._friendly_king_square else 3
        for i in range(precomputed_move_data.num_squares_to_edge[self._friendly_king_square][dir_index]):
            square_index = self._friendly_king_square + precomputed_move_data.direction_offsets[dir_index] * (i + 1)
            cur_piece = self._board.squares[square_index]
            if cur_piece != piece.NONE:
                # Friendly piece is blocking view of this square from the enemy.
                if piece.is_colour(cur_piece, self._friendly_colour):
                    break
                # This square contains an enemy piece
                else:
                    if piece.is_rook_or_queen(cur_piece):
                        return True
                    else:
                        # This piece is not able to move in the current direction, and is therefore blocking any checks along this line
                        break

        # Check if enemy pawn is controlling this square (can't use pawn attack bitboard, because pawn has been captured)
        for i in range(2):
            # Check if square exists diagonal to friendly king from which enemy pawn could be attacking it
            if precomputed_move_data.num_squares_to_edge[self._friendly_king_square][precomputed_move_data.pawn_attack_directions[self._friendly_colour_index][i]] > 0:
                # Move in direction friendly pawns attack to get square from which enemy pawn would attack
                cur_piece = self._board.squares[self._friendly_king_square
                                                + precomputed_move_data.direction_offsets[precomputed_move_data.pawn_attack_directions[self._friendly_colour_index][i]]]
                if cur_piece == (piece.PAWN | self._opponent_colour):  # Is enemy pawn
                    return True

        return False

    @staticmethod
    def _is_moving_along_ray(ray_dir: int, start_square: int, target_square: int):
        move_dir = precomputed_move_data.direction_lookup[target_square - start_square + 63]
        return ray_dir == move_dir or -ray_dir == move_dir

    @staticmethod
    def contains_square(bitboard: int, square: int) -> bool:
        return ((bitboard >> square) & 1) != 0

    def _init(self) -> None:
        self._moves = []
        self._in_check = False
        self._in_double_check = False
        self._pins_exist = False
        self._check_ray_bitmask = 0
        self._pin_ray_bitmask = 0
        self._white_to_move = self._board.colour_to_move == piece.WHITE
        self._friendly_colour = self._board.colour_to_move
        self._friendly_colour_index = Board.WHITE_INDEX if self._board.white_to_move else Board.BLACK_INDEX
        self._opponent_colour = self._board.opponent_colour
        self._friendly_king_square = self._board.king_square[self._friendly_colour_index]

        self._opponent_colour_index = 1 ^ self._friendly_colour_index

    def _generate_king_moves(self) -> None:
        for i in range(len(precomputed_move_data.king_moves[self._friendly_king_square])):
            target_square = precomputed_move_data.king_moves[self._friendly_king_square][i]
            piece_on_target_square = self._board.squares[target_square]

            # Skip squares occupied by friendly pieces
            if piece.is_colour(piece_on_target_square, self._friendly_colour):
                continue

            is_capture = piece.is_colour(piece_on_target_square, self._opponent_colour)
            if not is_capture:
                # King can't move to square marked as under enemy control, unless he is capturing that piece
                # Also skip if not generating quiet moves
                if not self._gen_quiets or self._square_is_in_check_ray(target_square):
                    continue

            # Safe for king to move to this square
            if not self._square_is_attacked(target_square):
                self._moves.append(Move(None, self._friendly_king_square, target_square))

                # Castling
                if not self._in_check and not is_capture:
                    # Castle king side
                    if (target_square == board_representation.F1 or target_square == board_representation.F8)\
                            and self._has_king_side_castle_right:
                        castle_king_side_square = target_square + 1
                        if self._board.squares[castle_king_side_square] == piece.NONE:
                            if not self._square_is_attacked(castle_king_side_square):
                                self._moves.append(Move(None, self._friendly_king_square, castle_king_side_square, Move.Flag.CASTLING))

                    # Castle queen side
                    elif (target_square == board_representation.D1 or target_square == board_representation.D8)\
                            and self._has_queen_side_castle_right:
                        castle_queen_side_square = target_square - 1
                        if (self._board.squares[castle_queen_side_square] == piece.NONE
                                and self._board.squares[castle_queen_side_square - 1] == piece.NONE):
                            if not self._square_is_attacked(castle_queen_side_square):
                                self._moves.append(Move(None, self._friendly_king_square, castle_queen_side_square, Move.Flag.CASTLING))

    def _generate_sliding_moves(self) -> None:
        rooks = self._board.rooks[self._friendly_colour_index]
        for i in range(rooks.count):
            self._generate_sliding_piece_moves(rooks[i], 0, 4)

        bishops = self._board.bishops[self._friendly_colour_index]
        for i in range(bishops.count):
            self._generate_sliding_piece_moves(bishops[i], 4, 8)

        queens = self._board.queens[self._friendly_colour_index]
        for i in range(queens.count):
            self._generate_sliding_piece_moves(queens[i], 0, 8)

    def _generate_sliding_piece_moves(self, start_square: int, start_dir_index: int, end_dir_index: int):
        is_pinned = self._is_pinned(start_square)

        # If this piece is pinned, and the king is in check, this piece cannot move
        if self._in_check and is_pinned:
            return

        for direction_index in range(start_dir_index, end_dir_index):
            current_dir_offset = precomputed_move_data.direction_offsets[direction_index]

            # If pinned, this piece can only move along the ray towards/away from the friendly king, so skip other directions
            if is_pinned and\
                    not MoveGenerator._is_moving_along_ray(current_dir_offset, self._friendly_king_square, start_square):
                continue

            for n in range(precomputed_move_data.num_squares_to_edge[start_square][direction_index]):
                target_square = start_square + current_dir_offset * (n + 1)
                target_square_piece = self._board.squares[target_square]

                # Blocked by friendly piece, so stop looking in this direction
                if piece.is_colour(target_square_piece, self._friendly_colour):
                    break

                is_capture = target_square_piece != piece.NONE

                move_prevents_check = self._square_is_in_check_ray(target_square)
                if move_prevents_check or not self._in_check:
                    if self._gen_quiets or is_capture:
                        self._moves.append(Move(None, start_square, target_square))

                # If square not empty, can't move any further in this direction
                # Also, if this move blocked a check, further moves won't block the check
                if is_capture or move_prevents_check:
                    break

    def _generate_knight_moves(self) -> None:
        knights = self._board.knights[self._friendly_colour_index]

        for i in range(knights.count):
            start_square = knights[i]

            # Knight cannot move if it is pinned
            if self._is_pinned(start_square):
                continue

            for knight_move_index in range(len(precomputed_move_data.knight_moves[start_square])):
                target_square = precomputed_move_data.knight_moves[start_square][knight_move_index]
                target_square_piece = self._board.squares[target_square]
                is_capture = piece.is_colour(target_square_piece, self._opponent_colour)
                if self._gen_quiets or is_capture:
                    # Skip if square contains friendly piece, or if in check and knight is not interposing/capturing checking piece
                    if piece.is_colour(target_square_piece, self._friendly_colour)\
                            or (self._in_check and not self._square_is_in_check_ray(target_square)):
                        continue
                    self._moves.append(Move(None, start_square, target_square))

    def _generate_pawn_moves(self) -> None:
        pawns = self._board.pawns[self._friendly_colour_index]
        pawn_offset = 8 if self._friendly_colour == piece.WHITE else -8
        start_rank = 1 if self._board.white_to_move else 6
        final_rank_before_promotion = 7 - start_rank

        en_passant_file = ((self._board.current_game_state >> 4) & 15) - 1
        en_passant_square = -1
        if en_passant_file != -1:
            en_passant_square = 8 * (5 if self._board.white_to_move else 2) + en_passant_file

        for i in range(pawns.count):
            start_square = pawns[i]
            rank = board_representation.get_rank_index(start_square)
            one_step_from_promotion = rank == final_rank_before_promotion

            if self._gen_quiets:
                square_one_forward = start_square + pawn_offset

                # Square ahead of pawn is empty: forward moves
                if self._board.squares[square_one_forward] == piece.NONE:
                    # Pawn not pinned, or is moving along line of pin
                    if not self._is_pinned(start_square) or self._is_moving_along_ray(pawn_offset, start_square, self._friendly_king_square):
                        # Not in check, or pawn is interposing checking piece
                        if not self._in_check or self._square_is_in_check_ray(square_one_forward):
                            if one_step_from_promotion:
                                self._make_promotion_moves(start_square, square_one_forward)
                            else:
                                self._moves.append(Move(None, start_square, square_one_forward))

                        # Is on starting square (so can move two forward if not blocked)
                        if rank == start_rank:
                            square_two_forward = square_one_forward + pawn_offset
                            if self._board.squares[square_two_forward] == piece.NONE:
                                # Not in check, or pawn is interposing checking piece
                                if not self._in_check or self._square_is_in_check_ray(square_two_forward):
                                    self._moves.append(Move(None, start_square, square_two_forward, Move.Flag.PAWN_TWO_FORWARD))

            # Pawn captures
            for j in range(2):
                # Check if square exists diagonal to pawn
                if precomputed_move_data.num_squares_to_edge[start_square][precomputed_move_data.pawn_attack_directions[self._friendly_colour_index][j]] > 0:
                    # move in direction friendly pawns attack to get square from which enemy pawn would attack
                    pawn_capture_dir = precomputed_move_data.direction_offsets[precomputed_move_data.pawn_attack_directions[self._friendly_colour_index][j]]
                    target_square = start_square + pawn_capture_dir
                    target_piece = self._board.squares[target_square]

                    # If piece is pinned, and the square it wants to move to is not on same line as the pin, then skip this direction
                    if self._is_pinned(start_square) and\
                            not self._is_moving_along_ray(pawn_capture_dir, self._friendly_king_square, start_square):
                        continue

                    # Regular capture
                    if piece.is_colour(target_piece, self._opponent_colour):
                        # If in check, and piece is not capturing/interposing the checking piece, then skip to next square
                        if self._in_check and not self._square_is_in_check_ray(target_square):
                            continue
                        if one_step_from_promotion:
                            self._make_promotion_moves(start_square, target_square)
                        else:
                            self._moves.append(Move(None, start_square, target_square))

                    # Capture en-passant
                    if target_square == en_passant_square:
                        ep_captured_pawn_square = target_square + (-8 if self._board.white_to_move else 8)
                        if not self._in_check_after_en_passant(start_square, target_square, ep_captured_pawn_square):
                            self._moves.append(Move(None, start_square, target_square, Move.Flag.EN_PASSANT_CAPTURE))

    def _make_promotion_moves(self, from_square: int, to_square: int) -> None:
        self._moves.append(Move(None, from_square, to_square, Move.Flag.PROMOTE_TO_QUEEN))
        if self.promotions_to_generate == self.PromotionMode.ALL:
            self._moves.append(Move(None, from_square, to_square, Move.Flag.PROMOTE_TO_KNIGHT))
            self._moves.append(Move(None, from_square, to_square, Move.Flag.PROMOTE_TO_ROOK))
            self._moves.append(Move(None, from_square, to_square, Move.Flag.PROMOTE_TO_BISHOP))
        elif self.promotions_to_generate == self.PromotionMode.QUEEN_AND_KNIGHT:
            self._moves.append(Move(None, from_square, to_square, Move.Flag.PROMOTE_TO_KNIGHT))

    def _gen_sliding_attack_map(self) -> None:
        self._opponent_sliding_attack_map = 0

        enemy_rooks = self._board.rooks[self._opponent_colour_index]
        for i in range(enemy_rooks.count):
            self._update_sliding_attack_piece(enemy_rooks[i], 0, 4)

        enemy_queens = self._board.queens[self._opponent_colour_index]
        for i in range(enemy_queens.count):
            self._update_sliding_attack_piece(enemy_queens[i], 0, 8)

        enemy_bishops = self._board.bishops[self._opponent_colour_index]
        for i in range(enemy_bishops.count):
            self._update_sliding_attack_piece(enemy_bishops[i], 4, 8)

    def _update_sliding_attack_piece(self, start_square: int, start_dir_index: int, end_dir_index: int) -> None:
        for direction_index in range(start_dir_index, end_dir_index):
            current_dir_offset = precomputed_move_data.direction_offsets[direction_index]
            for n in range(precomputed_move_data.num_squares_to_edge[start_square][direction_index]):
                target_square = start_square + current_dir_offset * (n + 1)
                target_square_piece = self._board.squares[target_square]
                self._opponent_sliding_attack_map |= (1 << target_square)
                if target_square != self._friendly_king_square:
                    if target_square_piece != piece.NONE:
                        break

    def _calculate_attack_data(self) -> None:
        self._gen_sliding_attack_map()
        # Search squares in all directions around friendly king for checks/pins by enemy sliding pieces (queen, rook, bishop)
        start_dir_index = 0
        end_dir_index = 8

        if self._board.queens[self._opponent_colour_index].count == 0:
            start_dir_index = 0 if self._board.rooks[self._opponent_colour_index].count > 0 else 4
            end_dir_index = 8 if self._board.bishops[self._opponent_colour_index].count > 0 else 4

        for direction_index in range(start_dir_index, end_dir_index):
            is_diagonal = direction_index > 3

            n = precomputed_move_data.num_squares_to_edge[self._friendly_king_square][direction_index]
            direction_offset = precomputed_move_data.direction_offsets[direction_index]
            is_friendly_piece_along_ray = False
            ray_mask = 0

            for i in range(n):
                square_index = self._friendly_king_square + direction_offset * (i + 1)
                ray_mask |= (1 << square_index)
                cur_piece = self._board.squares[square_index]

                # This square contains a piece
                if cur_piece != piece.NONE:
                    if piece.is_colour(cur_piece, self._friendly_colour):
                        # First friendly piece we have come across in this direction, so it might be pinned
                        if not is_friendly_piece_along_ray:
                            is_friendly_piece_along_ray = True
                        else:  # This is the second friendly piece we have found in this direction, therefore pin is not possible
                            break
                    else:  # This square contains an enemy piece
                        piece_type = piece.piece_type(cur_piece)

                        # Check if piece is in bitmask of pieces able to move in current direction
                        if is_diagonal and piece.is_bishop_or_queen(piece_type) or not is_diagonal and piece.is_rook_or_queen(piece_type):
                            # Friendly piece blocks the check, so this is a pin
                            if is_friendly_piece_along_ray:
                                self._pins_exist = True
                                self._pin_ray_bitmask |= ray_mask
                            else:  # No friendly piece blocking the attack, so this is a check
                                self._check_ray_bitmask |= ray_mask
                                self._in_double_check = self._in_check  # If already in check, then this is double check
                                self._in_check = True
                            break
                        else:
                            # This enemy piece is not able to move in the current direction, and so is blocking any checks/pins
                            break

            # Stop searching for pins if in double check, as the king is the only piece able to move in that case anyway
            if self._in_double_check:
                break

        # Knight attacks
        opponent_knights = self._board.knights[self._opponent_colour_index]
        self._opponent_knight_attacks = 0
        is_knight_check = False

        for knight_index in range(opponent_knights.count):
            start_square = opponent_knights[knight_index]
            self._opponent_knight_attacks |= precomputed_move_data.knight_attack_bitboards[start_square]

            if not is_knight_check and self.contains_square(self._opponent_knight_attacks, self._friendly_king_square):
                is_knight_check = True
                self._in_double_check = self._in_check  # If already in check, then this is double check
                self._in_check = True
                self._check_ray_bitmask |= (1 << start_square)

        # Pawn attacks
        opponent_pawns = self._board.pawns[self._opponent_colour_index]
        self.opponent_pawn_attack_map = 0
        is_pawn_check = False

        for pawn_index in range(opponent_pawns.count):
            pawn_square = opponent_pawns[pawn_index]
            pawn_attacks = precomputed_move_data.pawn_attack_bitboards[pawn_square][self._opponent_colour_index]
            self.opponent_pawn_attack_map |= pawn_attacks

            if not is_pawn_check and self.contains_square(pawn_attacks, self._friendly_king_square):
                is_pawn_check = True
                self._in_double_check = self._in_check  # If already in check, then this is double check
                self._in_check = True
                self._check_ray_bitmask |= (1 << pawn_square)

        enemy_king_square = self._board.king_square[self._opponent_colour_index]

        self._opponent_attack_map_no_pawns = self._opponent_sliding_attack_map \
                                             | self._opponent_knight_attacks \
                                             | precomputed_move_data.king_attack_bitboards[enemy_king_square]
        self.opponent_attack_map = self._opponent_attack_map_no_pawns | self.opponent_pawn_attack_map
