import piece
import board_representation


START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_piece_type_from_symbol = {'k': piece.KING, 'p': piece.PAWN, 'n': piece.KNIGHT,
                           'b': piece.BISHOP, 'r': piece.ROOK, 'q': piece.QUEEN}


class LoadedPositionInfo:
    __slots__ = {'squares', 'white_castle_king_side', 'white_castle_queen_side', 'black_castle_king_side',
                 'black_castle_queen_side', 'ep_file', 'white_to_move', 'ply_count'}

    def __init__(self):
        self.squares = [0] * 64
        self.white_castle_king_side = False
        self.white_castle_queen_side = False
        self.black_castle_king_side = False
        self.black_castle_queen_side = False
        self.ep_file = 0
        self.white_to_move = False
        self.ply_count = 0


def position_from_fen(fen: str) -> LoadedPositionInfo:
    loaded_position_info = LoadedPositionInfo()
    sections = fen.split(' ')

    file = 0
    rank = 7

    for symbol in sections[0]:
        if symbol == '/':
            file = 0
            rank -= 1
        else:
            if str.isdigit(symbol):
                file += int(symbol)
            else:
                piece_color = piece.WHITE if str.isupper(symbol) else piece.BLACK
                piece_type = _piece_type_from_symbol[symbol.lower()]
                loaded_position_info.squares[rank * 8 + file] = piece_type | piece_color
                file += 1

    loaded_position_info.white_to_move = (sections[1] == 'w')
    castling_rights = sections[2] if len(sections) > 2 else 'KQkq'
    loaded_position_info.white_castle_king_side = 'K' in castling_rights
    loaded_position_info.white_castle_queen_side = 'Q' in castling_rights
    loaded_position_info.black_castle_king_side = 'k' in castling_rights
    loaded_position_info.black_castle_king_side = 'q' in castling_rights

    if len(sections) > 3:
        en_passant_file_name = sections[3][0]  # string or char?????
        if en_passant_file_name in board_representation.FILE_NAMES:
            loaded_position_info.ep_file = board_representation.FILE_NAMES.find(en_passant_file_name) + 1

    # Half - move clock
    if len(sections) > 4:
        try:
            loaded_position_info.ply_count = str(sections[4])
        except ValueError:
            pass

    return loaded_position_info


def fen_from_position(board) -> str:
    fen = ''
    for rank in range(7, -1, -1):
        num_empty_files = 0
        for file in range(8):
            i = rank * 8 + file
            current_piece = board.squares[i]
            if current_piece != 0:
                if num_empty_files != 0:
                    fen += num_empty_files
                    num_empty_files = 0
                is_black = piece.is_colour(current_piece, piece.BLACK)
                piece_type = piece.piece_type(current_piece)
                piece_char = ' '
                if piece_type == piece.KING:
                    piece_char = 'K'
                elif piece_type == piece.QUEEN:
                    piece_char = 'Q'
                elif piece_type == piece.KNIGHT:
                    piece_char = 'N'
                elif piece_type == piece.BISHOP:
                    piece_char = 'B'
                elif piece_type == piece.ROOK:
                    piece_char = 'R'
                elif piece_type == piece.PAWN:
                    piece_char = 'P'

                fen += piece_char.lower() if is_black else piece_char
            else:
                num_empty_files += 1

        if num_empty_files != 0:
            fen += num_empty_files

        if rank != 0:
            fen += '/'

    # Side to move
    fen += ' '
    fen += 'w' if board.white_to_move else 'b'

    # Castling
    white_king_side = (board.current_game_state & 1) == 1
    white_queen_side = (board.current_game_state >> 1 & 1) == 1
    black_king_side = (board.current_game_state >> 2 & 1) == 1
    black_queen_side = (board.current_game_state >> 3 & 1) == 1
    fen += ' '
    fen += 'K' if white_king_side else ''
    fen += 'Q' if white_queen_side else ''
    fen += 'k' if black_king_side else ''
    fen += 'q' if black_queen_side else ''
    fen += '-' if (board.current_game_state & 15) == 0 else ''

    # En-passant
    fen += ' '
    ep_file = (board.current_game_state >> 4) & 15
    if ep_file == 0:
        fen += '-'
    else:
        file_name = board_representation.FILE_NAMES[ep_file - 1]
        ep_rank = 6 if board.white_to_move else 3
        fen += file_name + ep_rank

    # 50 move counter
    fen += ' '
    fen += board.fifty_move_counter

    # Full-move count (should be one at start, and increase after each move by black)
    fen += ' '
    fen += (board.ply_count // 2) + 1

    return fen
