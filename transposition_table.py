from __future__ import annotations

from board import Board
from move import Move
import math


class TranspositionTable:

    class Entry:
        def __init__(self, key: int, value: int, depth: int, node_type: int, move: Move):
            self.key = key
            self.value = value
            self.depth = depth  # Depth is how many ply were searched ahead from this position
            self.node_type = node_type
            self.move = move

        @staticmethod
        def get_empty() -> TranspositionTable.Entry:
            return TranspositionTable.Entry(0, 0, 0, 0, Move.get_invalid_move())

    _IMMEDIATE_MATE_SCORE = 100000
    LOOKUP_FAILED = -2147483648

    # The value for this position is the exact evaluation
    EXACT = 0
    # A move was found during the search that was too good, meaning the opponent will play a different move earlier on,
    # not allowing the position where this move was available to be reached. Because the search cuts off at
    # this point (beta cut-off), an even better move may exist. This means that the evaluation for the
    # position could be even higher, making the stored value the lower bound of the actual value.
    LOWER_BOUND = 1
    # No move during the search resulted in a position that was better than the current player could get from playing a
    # different move in an earlier position (i.e eval was <= alpha for all moves in the position).
    # Due to the way alpha-beta search works, the value we get here won't be the exact evaluation of the position,
    # but rather the upper bound of the evaluation. This means that the evaluation is, at most, equal to this value.
    UPPER_BOUND = 2

    def __init__(self, board: Board, size: int):
        self.enabled = True
        self._board = board
        self.size = size
        self.entries = [TranspositionTable.Entry.get_empty() for _ in range(size)]

    def clear(self) -> None:
        for i in range(len(self.entries)):
            self.entries[i] = TranspositionTable.Entry.get_empty()

    @property
    def index(self) -> int:
        return self._board.zobrist_key % self.size

    def get_stored_move(self) -> Move:
        return self.entries[self.index].move

    def lookup_evaluation(self, depth: int, ply_from_root: int, alpha: int, beta: int) -> int:
        if not self.enabled:
            return self.LOOKUP_FAILED

        entry = self.entries[self.index]
        # print(entry.depth, entry.move.start_square, entry.move.target_square)

        if entry.key == self._board.zobrist_key:
            # Only use stored evaluation if it has been searched to at least the same depth as would be searched now
            if entry.depth >= depth:
                corrected_score = self._correct_retrieved_mate_score(entry.value, ply_from_root)
                # We have stored the exact evaluation for this position, so return it
                if entry.node_type == self.EXACT:
                    return corrected_score

                # We have stored the upper bound of the eval for this position. If it's less than alpha then we don't need to
                # search the moves in this position as they won't interest us; otherwise we will have to search to find the exact value
                if entry.node_type == self.UPPER_BOUND and corrected_score <= alpha:
                    return corrected_score

                # We have stored the lower bound of the eval for this position. Only return if it causes a beta cut-off
                if entry.node_type == self.LOWER_BOUND and corrected_score >= beta:
                    return corrected_score

        return self.LOOKUP_FAILED

    def store_evaluation(self, depth: int, num_ply_searched: int, eval: int, eval_type: int, move: Move) -> None:
        if not self.enabled:
            return

        entry = TranspositionTable.Entry(self._board.zobrist_key,
                                         self._correct_mate_score_for_storage(eval, num_ply_searched),
                                         depth,
                                         eval_type,
                                         move)
        self.entries[self.index] = entry

    @staticmethod
    def _correct_mate_score_for_storage(score: int, num_ply_searched: int) -> int:
        if TranspositionTable.is_mate_score(score):
            sign = int(math.copysign(1, score))
            return (score * sign + num_ply_searched) * sign
        return score

    @staticmethod
    def _correct_retrieved_mate_score(score: int, num_ply_searched: int) -> int:
        if TranspositionTable.is_mate_score(score):
            sign = int(math.copysign(1, score))
            return (score * sign - num_ply_searched) * sign
        return score

    @staticmethod
    def is_mate_score(score: int) -> bool:
        max_mate_depth = 1000
        return abs(score) > TranspositionTable._IMMEDIATE_MATE_SCORE - max_mate_depth
