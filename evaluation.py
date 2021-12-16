from board import Board
from piece_list import PieceList
import precomputed_move_data
import piece_square_table

PAWN_VALUE = 100
KNIGHT_VALUE = 300
BISHOP_VALUE = 320
ROOK_VALUE = 500
QUEEN_VALUE = 900

_ENDGAME_MATERIAL_START = ROOK_VALUE * 2 + BISHOP_VALUE + KNIGHT_VALUE


# Performs static evaluation of the current position
# The position is assumed to be 'quiet' -> no captures are available that could substantially affect the evaluation
# The score that's returned is given from the perspective of whoever's turn it is to move
# So a positive score means the player who's turn it is to move has an advantage, while a negative score indicates a disadvantage
def evaluate(board: Board) -> int:
    white_eval = 0
    black_eval = 0

    white_material = _count_material(board, Board.WHITE_INDEX)
    black_material = _count_material(board, Board.BLACK_INDEX)

    white_material_no_pawns = white_material - board.pawns[Board.WHITE_INDEX].count * PAWN_VALUE
    black_material_no_pawns = black_material - board.pawns[Board.BLACK_INDEX].count * PAWN_VALUE
    white_endgame_weight = _endgame_weight(white_material_no_pawns)
    black_endgame_weight = _endgame_weight(black_material_no_pawns)

    white_eval += white_material
    black_eval += black_material
    white_eval += _mop_up_eval(board, Board.WHITE_INDEX, Board.BLACK_INDEX, white_material, black_material, black_endgame_weight)
    black_eval += _mop_up_eval(board, Board.BLACK_INDEX, Board.WHITE_INDEX, black_material, white_material, white_endgame_weight)

    white_eval += _evaluate_piece_square_tables(board, Board.WHITE_INDEX, black_endgame_weight)
    black_eval += _evaluate_piece_square_tables(board, Board.BLACK_INDEX, white_endgame_weight)

    eval = white_eval - black_eval

    perspective = 1 if board.white_to_move else -1
    return eval * perspective


def _endgame_weight(material_count_no_pawns: int) -> float:
    return 1 - min(float(1), material_count_no_pawns / _ENDGAME_MATERIAL_START)


def _mop_up_eval(board: Board, friendly_index: int, opponent_index: int, my_material: int, opponent_material: int,
                 endgame_weight: float) -> int:
    mop_up_score = 0
    if my_material > opponent_material + PAWN_VALUE * 2 and endgame_weight > 0:
        mop_up_score += precomputed_move_data.center_manhattan_distance[board.king_square[opponent_index]] * 10
        # Use orthogonal distance to promote direct opposition
        mop_up_score += (14 - precomputed_move_data.num_orthogonal_moves_to_square(board.king_square[friendly_index],
                                                                                   board.king_square[opponent_index])) * 4
        return int(mop_up_score * endgame_weight)
    return 0


def _count_material(board: Board, colour_index: int) -> int:
    material = 0
    material += board.pawns[colour_index].count * PAWN_VALUE
    material += board.knights[colour_index].count * KNIGHT_VALUE
    material += board.bishops[colour_index].count * BISHOP_VALUE
    material += board.rooks[colour_index].count * ROOK_VALUE
    material += board.queens[colour_index].count * QUEEN_VALUE

    return material


def _evaluate_piece_square_tables(board: Board, colour_index: int, endgame_weight: float) -> int:
    value = 0
    is_white = colour_index == Board.WHITE_INDEX
    value += _evaluate_piece_square_table(piece_square_table.pawns, board.pawns[colour_index], is_white)
    value += _evaluate_piece_square_table(piece_square_table.rooks, board.rooks[colour_index], is_white)
    value += _evaluate_piece_square_table(piece_square_table.knights, board.knights[colour_index], is_white)
    value += _evaluate_piece_square_table(piece_square_table.bishops, board.bishops[colour_index], is_white)
    value += _evaluate_piece_square_table(piece_square_table.queens, board.queens[colour_index], is_white)
    king_early_phase = piece_square_table.read(piece_square_table.king_middle, board.king_square[colour_index], is_white)
    value += int(king_early_phase * (1 - endgame_weight))
    # value += piece_square_table.read(piece_square_table.kingMiddle, self._board.KingSquare[colour_index], isWhite);

    return value


def _evaluate_piece_square_table(table: tuple[int], piece_list: PieceList, is_white: bool) -> int:
    value = 0
    for i in range(piece_list.count):
        value += piece_square_table.read(table, piece_list[i], is_white)
    return value
