import piece
import evaluation
from board import Board
from move import Move
from move_generator import MoveGenerator
from transposition_table import TranspositionTable


class MoveOrdering:

    _CONTROLLED_BY_OPPONENT_PAWN_PENALTY = 350
    _CAPTURED_PIECE_MULTIPLIER = 10

    def __init__(self, move_generator: MoveGenerator, tt: TranspositionTable):
        self._move_generator = move_generator
        self._tt = tt
        self._invalid_move = Move.get_invalid_move()

    def order_moves(self, board: Board, moves: list[Move], use_tt: bool) -> None:
        hash_move = self._invalid_move
        if use_tt:
            hash_move = self._tt.get_stored_move()

        moves_by_scores = []
        for i in range(len(moves)):
            score = 0
            move_piece_type = piece.piece_type(board.squares[moves[i].start_square])
            captured_piece_type = piece.piece_type(board.squares[moves[i].target_square])
            flag = moves[i].move_flag

            if captured_piece_type != piece.NONE:
                # Order moves to try capturing the most valuable opponent piece with least valuable of own pieces first
                # The _CAPTURED_PIECE_MULTIPLIER is used to make even 'bad' captures like QxP rank above non-captures
                score = MoveOrdering._CAPTURED_PIECE_MULTIPLIER * MoveOrdering._get_piece_value(captured_piece_type) \
                        - MoveOrdering._get_piece_value(move_piece_type)

            if move_piece_type == piece.PAWN:
                if flag == Move.Flag.PROMOTE_TO_QUEEN:
                    score += evaluation.QUEEN_VALUE
                elif flag == Move.Flag.PROMOTE_TO_KNIGHT:
                    score += evaluation.KNIGHT_VALUE
                elif flag == Move.Flag.PROMOTE_TO_ROOK:
                    score += evaluation.ROOK_VALUE
                elif flag == Move.Flag.PROMOTE_TO_BISHOP:
                    score += evaluation.BISHOP_VALUE
            else:
                # Punish moving piece to a square attacked by opponent pawn
                if MoveGenerator.contains_square(self._move_generator.opponent_pawn_attack_map, moves[i].target_square):
                    score -= MoveOrdering._CONTROLLED_BY_OPPONENT_PAWN_PENALTY

            if Move.is_same(moves[i], hash_move):
                score += 10000

            moves_by_scores.append((score, moves[i]))

        moves_by_scores = sorted(moves_by_scores, key=lambda x: x[0], reverse=True)
        for i in range(len(moves)):
            moves[i] = moves_by_scores[i][1]

    @staticmethod
    def _get_piece_value(piece_type: int) -> int:
        if piece_type == piece.QUEEN:
            return evaluation.QUEEN_VALUE
        elif piece_type == piece.ROOK:
            return evaluation.ROOK_VALUE
        elif piece_type == piece.BISHOP:
            return evaluation.BISHOP_VALUE
        elif piece_type == piece.KNIGHT:
            return evaluation.KNIGHT_VALUE
        elif piece_type == piece.PAWN:
            return evaluation.PAWN_VALUE
        else:
            return 0
