from ai_settings import AISettings
from board import Board
from move import Move
from move_generator import MoveGenerator
from move_ordering import MoveOrdering
from transposition_table import TranspositionTable
import evaluation
import math


class Search:

    _TRANSPOSITION_TABLE_SIZE = 64000
    _IMMEDIATE_MATE_SCORE = 100000
    _POS_INF = int(1e9)
    _NEG_INF = -_POS_INF

    # public event System.Action<Move> onSearchComplete;

    __slots__ = {'_best_move_on_iteration', '_best_eval_on_iteration', '_best_move', '_best_eval',
                 '_current_search_depth', '_abort_search', '_board', '_settings', '_move_generator', '_tt',
                 '_move_ordering', '_invalid_move', '_is_done'}

    _best_move_on_iteration: Move
    _best_move: Move

    # Diagnostics
    # public SearchDiagnostics search_diagnostics
    # int num_nodes
    # int num_q_nodes
    # int num_cutoffs
    # int num_transpositions
    # Stopwatch search_stopwatch

    @property
    def is_done(self):
        return self._is_done

    def __init__(self, board: Board, settings: AISettings):
        self._board = board
        self._settings = settings
        self._move_generator = MoveGenerator(settings.promotions_to_search)
        self._tt = TranspositionTable(board, Search._TRANSPOSITION_TABLE_SIZE)
        self._move_ordering = MoveOrdering(self._move_generator, self._tt)
        self._invalid_move = Move.get_invalid_move()
        self._best_eval_on_iteration = 0
        self._best_eval = 0
        self._current_search_depth = 0
        self._abort_search = False
        self._is_done = False

    def start_search(self) -> None:
        self._is_done = False
        # InitDebugInfo ();

        # Initialize search settings
        self._best_eval_on_iteration = self._best_eval = 0
        self._best_move_on_iteration = self._best_move = Move.get_invalid_move()
        self._tt.enabled = self._settings.use_tt

        if self._settings.clear_tt_each_move:
            self._tt.clear()

        self._move_generator.promotions_to_generate = self._settings.promotions_to_search
        self._current_search_depth = 0
        self._abort_search = False
        # searchDiagnostics = new SearchDiagnostics ();

        # Iterative deepening. This means doing a full search with a depth of 1, then with a depth of 2...
        # This allows the search to be aborted at any time, while still yielding a useful result from the last search
        if self._settings.use_iterative_deepening:
            target_depth = self._settings.depth if self._settings.use_fixed_depth_search else Search._POS_INF
            for search_depth in range(1, target_depth):
                self._search_moves(search_depth, 0, Search._NEG_INF, Search._POS_INF)
                if self._abort_search:
                    break
                else:
                    self._current_search_depth = search_depth
                    self._best_move = self._best_move_on_iteration
                    self._best_eval = self._best_eval_on_iteration

                    # Update diagnostics
                    # searchDiagnostics.lastCompletedDepth = searchDepth;
                    # searchDiagnostics.move = bestMove.Name;
                    # searchDiagnostics.eval = bestEval;
                    # searchDiagnostics.moveVal = Chess.PGNCreator.NotationFromMove (FenUtility.CurrentFen (board), bestMove);

                    # Exit search if found a mate
                    if TranspositionTable.is_mate_score(self._best_eval) and not self._settings.endless_search_mode:
                        break
        else:
            self._search_moves(self._settings.depth, 0, Search._NEG_INF, Search._POS_INF)
            self._best_move = self._best_move_on_iteration
            self._best_eval = self._best_eval_on_iteration
        self._is_done = True

        # onSearchComplete?.Invoke (bestMove)

        # if not self._settings.use_threading:
        #     LogDebugInfo ()
        pass

    def get_search_result(self) -> tuple[Move, int]:
        return self._best_move, self._best_eval

    def end_search(self):
        self._abort_search = True

    def _search_moves(self, depth: int, ply_from_root: int, alpha: int, beta: int) -> int:
        if self._abort_search:
            return 0

        if ply_from_root > 0:
            # Detect draw by repetition
            # Returns a draw score even if this position has only appeared once in the game history
            if self._board.zobrist_key in self._board.repetition_position_history:
                return 0

            # Skip this position if a mating sequence has already been found earlier in
            # the search, which would be shorter than any mate we could find from here
            # This is done by observing that alpha can't possibly be worse (and likewise
            # beta can't  possibly be better) than being mated in the current position
            alpha = max(alpha, -Search._IMMEDIATE_MATE_SCORE + ply_from_root)
            beta = min(beta, Search._IMMEDIATE_MATE_SCORE - ply_from_root)
            if alpha >= beta:
                return alpha

        # Try looking up the current position in the transposition table.
        # If the same position has already been searched to at least an equal depth
        # to the search we're doing now, we can just use the recorded evaluation
        tt_value = self._tt.lookup_evaluation(depth, ply_from_root, alpha, beta)

        if tt_value != TranspositionTable.LOOKUP_FAILED:
            # numTranspositions += 1
            if ply_from_root == 0:
                self._best_move_on_iteration = self._tt.get_stored_move()
                self._best_eval_on_iteration = self._tt.entries[self._tt.index].value
                # Debug.Log ("move retrieved " + bestMoveThisIteration.Name + " Node type: " + tt.entries[tt.Index].nodeType + " depth: " + tt.entries[tt.Index].depth);
            return tt_value

        if depth == 0:
            return self._quiescence_search(alpha, beta)

        moves = self._move_generator.generate_moves(self._board)
        self._move_ordering.order_moves(self._board, moves, self._settings.use_tt)
        # Detect checkmate and stalemate when no legal moves are available
        if len(moves) == 0:
            if self._move_generator.in_check:
                mate_score = Search._IMMEDIATE_MATE_SCORE - ply_from_root
                return -mate_score
            else:
                return 0

        eval_type = TranspositionTable.UPPER_BOUND
        best_move_in_position = Move.get_invalid_move()  # TODO

        for i in range(len(moves)):
            self._board.make_move(moves[i], True)
            eval = -self._search_moves(depth - 1, ply_from_root + 1, -beta, -alpha)

            self._board.unmake_move(moves[i], True)
            # numNodes += 1

            # Move was *too* good, so opponent won't allow this position to be reached
            # (by choosing a different move earlier on). Skip remaining moves
            if eval >= beta:
                self._tt.store_evaluation(depth, ply_from_root, beta, TranspositionTable.LOWER_BOUND, moves[i])
                # numCutoffs += 1
                return beta

            # Found a new best move in this position
            if eval > alpha:
                eval_type = TranspositionTable.EXACT
                best_move_in_position = moves[i]

                alpha = eval
                if ply_from_root == 0:
                    self._best_move_on_iteration = moves[i]
                    self._best_eval_on_iteration = eval

        self._tt.store_evaluation(depth, ply_from_root, alpha, eval_type, best_move_in_position)

        return alpha

    # Search capture moves until a 'quiet' position is reached.
    def _quiescence_search(self, alpha: int, beta: int) -> int:
        # A player isn't forced to make a capture (typically), so see what the evaluation is without capturing anything.
        # This prevents situations where a player ony has bad captures available from being evaluated as bad,
        # when the player might have good non-capture moves available.
        eval = evaluation.evaluate(self._board)
        # searchDiagnostics.numPositionsEvaluated += 1
        if eval >= beta:
            return beta
        if eval > alpha:
            alpha = eval

        moves = self._move_generator.generate_moves(self._board, False)
        self._move_ordering.order_moves(self._board, moves, False)
        for i in range(len(moves)):
            self._board.make_move(moves[i], True)
            eval = -self._quiescence_search(-beta, -alpha)
            self._board.unmake_move(moves[i], True)
            # numQNodes += 1

            if eval >= beta:
                # numCutoffs += 1
                return beta
            if eval > alpha:
                alpha = eval
        return alpha

    @staticmethod
    def num_ply_to_mate_from_score(score: int) -> int:
        return Search._IMMEDIATE_MATE_SCORE - abs(score)

    # void LogDebugInfo () {
    #     AnnounceMate ();
    #     Debug.Log ($"Best move: {bestMoveThisIteration.Name} Eval: {bestEvalThisIteration} Search time: {searchStopwatch.ElapsedMilliseconds} ms.");
    #     Debug.Log ($"Num nodes: {numNodes} num Qnodes: {numQNodes} num cutoffs: {numCutoffs} num TThits {numTranspositions}");
    # }

    # def _announce_mate(self) -> None:
    #     if Search.is_mate_score(self._best_eval_on_iteration):
    #         num_ply_to_mate = self.num_ply_to_mate_from_score(self._best_eval_on_iteration)
    #         # int numPlyToMateAfterThisMove = num_ply_to_mate - 1
    #
    #         num_moves_to_mate = int(math.ceil(num_ply_to_mate / 2))
    #
    #         # side_with_mate = 'Black' if self._best_eval_on_iteration * (1 if self._board.white_to_move else -1) < 0 else 'White'
    #         # Debug.Log ($"{sideWithMate} can mate in {numMovesToMate} move{((numMovesToMate>1)?"s":"")}");

    # def _init_debug_info(self):
    #     searchStopwatch = System.Diagnostics.Stopwatch.StartNew()
    #     numNodes = 0
    #     numQNodes = 0
    #     numCutoffs = 0
    #     numTranspositions = 0

    # class SearchDiagnostics:
    #     public int lastCompletedDepth
    #     public string moveVal
    #     public string move
    #     public int eval
    #     public bool isBook
    #     public int numPositionsEvaluated