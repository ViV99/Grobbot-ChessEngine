from piece_list import PieceList
from move import Move
from collections import deque

import fen_utility

import board_representation
import piece
import zobrist


class Board:
    WHITE_INDEX = 0
    BLACK_INDEX = 1

    _WHITE_CASTLE_KING_SIDE_MASK = 0b1111111111111110
    _WHITE_CASTLE_QUEEN_SIDE_MASK = 0b1111111111111101
    _BLACK_CASTLE_KING_SIDE_MASK = 0b1111111111111011
    _BLACK_CASTLE_QUEEN_SIDE_MASK = 0b1111111111110111

    _WHITE_CASTLE_MASK = _WHITE_CASTLE_KING_SIDE_MASK & _WHITE_CASTLE_QUEEN_SIDE_MASK
    _BLACK_CASTLE_MASK = _BLACK_CASTLE_KING_SIDE_MASK & _BLACK_CASTLE_QUEEN_SIDE_MASK

    # Bits 0 - 3 store white and black king side / queen side castling legality
    # Bits 4 - 7 store file of ep square(starting at 1, so 0 = no ep square)
    # Bits 8 - 13 captured piece
    # Bits 14 - ... fifty move counter

    __slots__ = {'squares', 'white_to_move', 'colour_to_move', 'opponent_colour', 'colour_to_move_index',
                 '_game_state_history', 'current_game_state', 'ply_count', 'fifty_move_counter', 'zobrist_key',
                 'repetition_position_history', 'king_square', 'rooks', 'bishops', 'queens', 'knights', 'pawns',
                 'all_piece_lists'}

    def __init__(self):
        self.white_to_move = True
        self.colour_to_move = 0
        self.colour_to_move_index = 0
        self.opponent_colour = 0
        self.current_game_state = 0
        self._init()

    def _init(self) -> None:
        self.squares = [0] * 64  # Stores piece code for each square on the board
        self.king_square = [0] * 2  # Index of square of white and black king

        self._game_state_history = deque()
        self.repetition_position_history = deque()

        self.zobrist_key = 0
        self.ply_count = 0  # Total plies played in game
        self.fifty_move_counter = 0  # Num ply since last pawn move or capture

        self.knights = [PieceList(10), PieceList(10)]
        self.pawns = [PieceList(8), PieceList(8)]
        self.rooks = [PieceList(10), PieceList(10)]
        self.bishops = [PieceList(10), PieceList(10)]
        self.queens = [PieceList(9), PieceList(9)]
        empty_list = PieceList(0)
        self.all_piece_lists = [
            empty_list,
            empty_list,
            self.pawns[self.WHITE_INDEX],
            self.knights[self.WHITE_INDEX],
            empty_list,
            self.bishops[self.WHITE_INDEX],
            self.rooks[self.WHITE_INDEX],
            self.queens[self.WHITE_INDEX],
            empty_list,
            empty_list,
            self.pawns[self.BLACK_INDEX],
            self.knights[self.BLACK_INDEX],
            empty_list,
            self.bishops[self.BLACK_INDEX],
            self.rooks[self.BLACK_INDEX],
            self.queens[self.BLACK_INDEX]]

    def _get_piece_list(self, piece_type: int, colour_index: int) -> PieceList:
        return self.all_piece_lists[colour_index * 8 + piece_type]

    # The in_search parameter controls whether this move should be recorded in the game history
    # (for detecting three - fold repetition)
    def make_move(self, move: Move, in_search=False) -> None:
        old_en_passant_file = (self.current_game_state >> 4) & 15
        original_castle_state = self.current_game_state & 15
        new_castle_state = original_castle_state
        self.current_game_state = 0

        opponent_colour_index = 1 ^ self.colour_to_move_index
        move_from = move.start_square
        move_to = move.target_square

        captured_piece_type = piece.piece_type(self.squares[move_to])
        move_piece = self.squares[move_from]
        move_piece_type = piece.piece_type(move_piece)

        move_flag = move.move_flag
        is_promotion = move.is_promotion
        is_en_passant = move.is_en_passant

        # Handle captures
        self.current_game_state |= captured_piece_type << 8

        if captured_piece_type != 0 and not is_en_passant:
            self.zobrist_key ^= zobrist.pieces_array[captured_piece_type, opponent_colour_index, move_to]
            self._get_piece_list(captured_piece_type, opponent_colour_index).remove_piece_at_square(move_to)

        # Move pieces in piece lists
        if move_piece_type == piece.KING:
            self.king_square[self.colour_to_move_index] = move_to
            new_castle_state &= Board._WHITE_CASTLE_MASK if self.white_to_move else Board._BLACK_CASTLE_MASK
        else:
            self._get_piece_list(move_piece_type, self.colour_to_move_index).move_piece(move_from, move_to)

        piece_on_target_square = move_piece

        # Handle promotion
        if is_promotion:
            promote_type = 0

            if move_flag == Move.Flag.PROMOTE_TO_ROOK:
                promote_type = piece.ROOK
                self.rooks[self.colour_to_move_index].add_piece_at_square(move_to)
            elif move_flag == Move.Flag.PROMOTE_TO_QUEEN:
                promote_type = piece.QUEEN
                self.queens[self.colour_to_move_index].add_piece_at_square(move_to)
            elif move_flag == Move.Flag.PROMOTE_TO_BISHOP:
                promote_type = piece.BISHOP
                self.bishops[self.colour_to_move_index].add_piece_at_square(move_to)
            elif move_flag == Move.Flag.PROMOTE_TO_KNIGHT:
                promote_type = piece.KNIGHT
                self.knights[self.colour_to_move_index].add_piece_at_square(move_to)

            piece_on_target_square = promote_type | self.colour_to_move
            self.pawns[self.colour_to_move_index].remove_piece_at_square(move_to)
        else:
            # Handle en-passant an castling
            if move_flag == Move.Flag.CASTLING:
                king_side = move_to == board_representation.G1 or move_to == board_representation.G8
                castling_rook_from_index = move_to + 1 if king_side else move_to - 2
                castling_rook_to_index = move_to - 1 if king_side else move_to + 1

                self.squares[castling_rook_from_index] = piece.NONE
                self.squares[castling_rook_to_index] = piece.ROOK | self.colour_to_move
                self.rooks[self.colour_to_move_index].move_piece(castling_rook_from_index, castling_rook_to_index)
                self.zobrist_key ^= zobrist.pieces_array[piece.ROOK, self.colour_to_move_index, castling_rook_from_index]
                self.zobrist_key ^= zobrist.pieces_array[piece.ROOK, self.colour_to_move_index, castling_rook_to_index]
            elif move_flag == Move.Flag.EN_PASSANT_CAPTURE:
                ep_pawn_square = move_to + (-8 if self.colour_to_move == piece.WHITE else 8)
                self.current_game_state |= self.squares[ep_pawn_square] << 8  # Add pawn as capture type
                self.squares[ep_pawn_square] = 0  # Clear empty capture square
                self.pawns[opponent_colour_index].remove_piece_at_square(ep_pawn_square)
                self.zobrist_key ^= zobrist.pieces_array[piece.PAWN, opponent_colour_index, ep_pawn_square]

        # Update the board representation
        self.squares[move_to] = piece_on_target_square
        self.squares[move_from] = 0

        # Pawn has moved two forwards, mark file with en-passant flag
        if move_flag == Move.Flag.PAWN_TWO_FORWARD:
            file = board_representation.get_file_index(move_from) + 1
            self.current_game_state |= file << 4
            self.zobrist_key ^= zobrist.en_passant_file[file]

        # Piece moving to/from rook square removes castling right for that side
        if original_castle_state != 0:
            if move_to == board_representation.H1 or move_from == board_representation.H1:
                new_castle_state &= Board._WHITE_CASTLE_KING_SIDE_MASK
            elif move_to == board_representation.A1 or move_from == board_representation.A1:
                new_castle_state &= Board._WHITE_CASTLE_QUEEN_SIDE_MASK
            if move_to == board_representation.H8 or move_from == board_representation.H8:
                new_castle_state &= Board._BLACK_CASTLE_KING_SIDE_MASK
            elif move_to == board_representation.A8 or move_from == board_representation.A8:
                new_castle_state &= Board._BLACK_CASTLE_QUEEN_SIDE_MASK

        # Update zobrist key with new piece position and side to move
        self.zobrist_key ^= zobrist.side_to_move
        self.zobrist_key ^= zobrist.pieces_array[move_piece_type, self.colour_to_move_index, move_from]
        self.zobrist_key ^= zobrist.pieces_array[
            piece.piece_type(piece_on_target_square), self.colour_to_move_index, move_to]

        if old_en_passant_file != 0:
            self.zobrist_key ^= zobrist.en_passant_file[old_en_passant_file]

        if new_castle_state != original_castle_state:
            self.zobrist_key ^= zobrist.castling_rights[original_castle_state]  # remove old castling rights state
            self.zobrist_key ^= zobrist.castling_rights[new_castle_state]  # add new castling rights state

        self.current_game_state |= new_castle_state
        self.current_game_state |= self.fifty_move_counter << 14
        self._game_state_history.append(self.current_game_state)

        # Change side to move
        self.white_to_move = not self.white_to_move
        self.colour_to_move = piece.WHITE if self.white_to_move else piece.BLACK
        self.opponent_colour = piece.BLACK if self.white_to_move else piece.WHITE
        self.colour_to_move_index = 1 ^ self.colour_to_move_index
        self.ply_count += 1
        self.fifty_move_counter += 1

        if not in_search:
            if move_piece_type == piece.PAWN or captured_piece_type != piece.NONE:
                self.repetition_position_history.clear()
                self.fifty_move_counter = 0
            else:
                self.repetition_position_history.append(self.zobrist_key)

    # Undo a move previously made on the board
    def unmake_move(self, move: Move, in_search=False) -> None:
        # opponentColour = ColourToMove;
        opponent_colour_index = self.colour_to_move_index
        self.colour_to_move = self.opponent_colour  # side who made the move we are undoing
        self.opponent_colour = piece.BLACK if self.opponent_colour == piece.WHITE else piece.WHITE
        self.colour_to_move_index = 1 - self.colour_to_move_index
        self.white_to_move = not self.white_to_move

        original_castle_state = self.current_game_state & 0b1111

        captured_piece_type = (self.current_game_state >> 8) & 63
        captured_piece = 0 if captured_piece_type == 0 else captured_piece_type | self.opponent_colour

        is_en_passant = move.move_flag == Move.Flag.EN_PASSANT_CAPTURE

        to_square_piece_type = piece.piece_type(self.squares[move.target_square])
        moved_piece_type = piece.PAWN if move.is_promotion else to_square_piece_type

        # Update zobrist key with new piece position and side to move
        self.zobrist_key ^= zobrist.side_to_move
        self.zobrist_key ^= zobrist.pieces_array[moved_piece_type, self.colour_to_move_index, move.start_square]  # Add piece back to square it moved from
        self.zobrist_key ^= zobrist.pieces_array[to_square_piece_type, self.colour_to_move_index, move.target_square]  # Remove piece from square it moved to

        old_en_passant_file = (self.current_game_state >> 4) & 15
        if old_en_passant_file != 0:
            self.zobrist_key ^= zobrist.en_passant_file[old_en_passant_file]

        # Ignore ep captures, handled later
        if captured_piece_type != 0 and not is_en_passant:
            self.zobrist_key ^= zobrist.pieces_array[captured_piece_type, opponent_colour_index, move.target_square]
            self._get_piece_list(captured_piece_type, opponent_colour_index).add_piece_at_square(move.target_square)

        # Update king index
        if moved_piece_type == piece.KING:
            self.king_square[self.colour_to_move_index] = move.start_square
        elif not move.is_promotion:
            self._get_piece_list(moved_piece_type, self.colour_to_move_index).move_piece(move.target_square,
                                                                                        move.start_square)

        # Put back moved piece
        self.squares[move.start_square] = moved_piece_type | self.colour_to_move  # If move was a pawn promotion, this will put the promoted piece back instead of the pawn
        self.squares[move.target_square] = captured_piece  # Will be 0 if no piece was captured

        if move.is_promotion:
            self.pawns[self.colour_to_move_index].add_piece_at_square(move.start_square)
            if move.move_flag == Move.Flag.PROMOTE_TO_QUEEN:
                self.queens[self.colour_to_move_index].remove_piece_at_square(move.target_square)
            elif move.move_flag == Move.Flag.PROMOTE_TO_KNIGHT:
                self.knights[self.colour_to_move_index].remove_piece_at_square(move.target_square)
            elif move.move_flag == Move.Flag.PROMOTE_TO_BISHOP:
                self.bishops[self.colour_to_move_index].remove_piece_at_square(move.target_square)
            elif move.move_flag == Move.Flag.PROMOTE_TO_ROOK:
                self.rooks[self.colour_to_move_index].remove_piece_at_square(move.target_square)
        elif is_en_passant:  # Ep capture: put captured pawn back on right square
            ep_index = move.target_square + -8 if self.colour_to_move == piece.WHITE else 8
            self.squares[move.target_square] = 0
            self.squares[ep_index] = captured_piece
            self.pawns[opponent_colour_index].add_piece_at_square(ep_index)
            self.zobrist_key ^= zobrist.pieces_array[piece.PAWN, opponent_colour_index, ep_index]
        elif move.move_flag == Move.Flag.CASTLING:  # Castles: move rook back to starting square
            king_side = move.target_square == 6 or move.target_square == 62
            castling_rook_from_index = move.target_square + 1 if king_side else move.target_square - 2
            castling_rook_to_index = move.target_square - 1 if king_side else move.target_square + 1

            self.squares[castling_rook_to_index] = 0
            self.squares[castling_rook_from_index] = piece.ROOK | self.colour_to_move
            self.rooks[self.colour_to_move_index].move_piece(castling_rook_to_index, castling_rook_from_index)
            self.zobrist_key ^= zobrist.pieces_array[piece.ROOK, self.colour_to_move_index, castling_rook_from_index]
            self.zobrist_key ^= zobrist.pieces_array[piece.ROOK, self.colour_to_move_index, castling_rook_to_index]

        self._game_state_history.pop()  # Removes current state from history
        self.current_game_state = self._game_state_history[-1]  # Sets current state to previous state in history

        self.fifty_move_counter = (self.current_game_state & 4294950912) >> 14
        new_en_passant_file = (self.current_game_state >> 4) & 15
        if new_en_passant_file != 0:
            self.zobrist_key ^= zobrist.en_passant_file[new_en_passant_file]

        new_castle_state = self.current_game_state & 0b1111
        if new_castle_state != original_castle_state:
            self.zobrist_key ^= zobrist.castling_rights[original_castle_state]  # Remove old castling rights state
            self.zobrist_key ^= zobrist.castling_rights[new_castle_state]  # Add new castling rights state

        self.ply_count -= 1

        if not in_search and self.repetition_position_history:
            self.repetition_position_history.pop()

    def load_start_position(self) -> None:
        self.load_position(fen_utility.START_FEN)

    def load_position(self, fen: str) -> None:
        self._init()
        loaded_position = fen_utility.position_from_fen(fen)

        # Load pieces into board array and piece lists
        for square_index in range(64):
            current_piece = loaded_position.squares[square_index]
            self.squares[square_index] = current_piece

            if current_piece != piece.NONE:
                piece_type = piece.piece_type(current_piece)
                piece_colour_index = self.WHITE_INDEX if piece.is_colour(current_piece,
                                                                         piece.WHITE) else self.BLACK_INDEX
                if piece.is_sliding_piece(current_piece):
                    if piece_type == piece.QUEEN:
                        self.queens[piece_colour_index].add_piece_at_square(square_index)
                    elif piece_type == piece.ROOK:
                        self.rooks[piece_colour_index].add_piece_at_square(square_index)
                    elif piece_type == piece.BISHOP:
                        self.bishops[piece_colour_index].add_piece_at_square(square_index)
                elif piece_type == piece.KNIGHT:
                    self.knights[piece_colour_index].add_piece_at_square(square_index)
                elif piece_type == piece.PAWN:
                    self.pawns[piece_colour_index].add_piece_at_square(square_index)
                elif piece_type == piece.KING:
                    self.king_square[piece_colour_index] = square_index

        # Side to move
        self.white_to_move = loaded_position.white_to_move
        self.colour_to_move = piece.WHITE if self.white_to_move else piece.BLACK
        self.opponent_colour = piece.BLACK if self.white_to_move else piece.WHITE
        self.colour_to_move_index = 0 if self.white_to_move else 1

        # Create game state
        white_castle = (1 << 0 if loaded_position.white_castle_king_side else 0) \
                       | (1 << 1 if loaded_position.white_castle_queen_side else 0)
        black_castle = (1 << 2 if loaded_position.black_castle_king_side else 0) \
                       | (1 << 3 if loaded_position.black_castle_queen_side else 0)

        ep_state = loaded_position.ep_file << 4
        initial_game_state = (white_castle | black_castle | ep_state)
        self._game_state_history.append(initial_game_state)
        self.current_game_state = initial_game_state
        self.ply_count = loaded_position.ply_count

        # Initialize zobrist key
        self.zobrist_key = zobrist.calculate_zobrist_key(self)
