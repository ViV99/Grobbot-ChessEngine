import fen_utility
from move import Move
from move_generator import MoveGenerator
from os import system, name
from board import Board
from ai_settings import AISettings
from search import Search


import time
import sys
import piece
import os
import re
import multiprocessing as mp

CURRENT_VERSION = '0.1.0'


def to_not(index: int) -> str:
    arr = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    return arr[index % 8] + str(index // 8 + 1)


def from_not(square: str) -> int:
    if ord(square[0]) - 97 < 0:
        return 8 * (ord(square[1]) - 49) + ord(square[0]) - 65
    return 8 * (ord(square[1]) - 49) + ord(square[0]) - 97


def main():
    board = Board()
    # 8/4k3/2K5/8/3P4/8/8/8 w - - 0 1
    board.load_start_position()
    # settings = AISettings()
    # s = Search(board, settings)
    # s.start_search()
    # m = s.get_search_result()[0]
    # print(m.start_square, m.target_square)

    while True:
        try:
            print('Enter move:')
            start, end, t = input().split()
            mv = Move(None, from_not(start), from_not(end), int(t))
            board.make_move(mv, False)
        except:
            print('Error, try again')
            continue
        settings = AISettings()
        s = Search(board, settings)
        if board.ply_count < 66:
            settings.depth = 5

        s.start_search()
        mv_bot, ev = s.get_search_result()
        print(f'Engine move: {to_not(mv_bot.start_square)} {to_not(mv_bot.target_square)} {mv_bot.move_flag}')
        board.make_move(mv_bot, False)


is_ready = True


def translate_promote_from(letter: str) -> Move.Flag:
    promote_piece_map = {
        'q': Move.Flag.PROMOTE_TO_QUEEN,
        'n': Move.Flag.PROMOTE_TO_KNIGHT,
        'r': Move.Flag.PROMOTE_TO_ROOK,
        'b': Move.Flag.PROMOTE_TO_BISHOP
    }
    res = promote_piece_map.get(letter)
    return res if res is not None else Move.Flag.NONE


def translate_promote_to(flag: int) -> str:
    promote_piece_map = {
        Move.Flag.PROMOTE_TO_QUEEN: 'q',
        Move.Flag.PROMOTE_TO_KNIGHT: 'n',
        Move.Flag.PROMOTE_TO_ROOK: 'r',
        Move.Flag.PROMOTE_TO_BISHOP: 'b'
    }
    res = promote_piece_map.get(flag)
    return res if res is not None else ''


def make_moves(board: Board, moves: list[str]) -> None:
    match = re.compile(r'([a-h][1-8])([a-h][1-8])([qnrb])?')
    for move in moves:
        res = match.match(move)
        flag = Move.Flag.NONE
        if res.groups()[2] is not None:
            flag = translate_promote_from(res.groups()[2])
        board.make_move(Move(None, from_not(res.groups()[0]), from_not(res.groups()[1]), flag))


def genius_ai_decision(board: Board, wtime: int, btime: int, winc: int, binc: int) -> int:
    return 4


def process_go(command: list[str], settings: AISettings, board: Board, search: Search) -> str:
    wtime = btime = winc = binc = 0
    for i in range(0, len(command), 2):
        if command[i] == 'wtime':
            wtime = int(command[i + 1])
        elif command[i] == 'btime':
            btime = int(command[i + 1])
        elif command[i] == 'winc':
            winc = int(command[i + 1])
        elif command[i] == 'binc':
            binc = int(command[i + 1])
    settings.depth = genius_ai_decision(board, wtime, btime, winc, binc)
    global is_ready
    is_ready = False
    search.start_search()
    res = search.get_search_result()[0]
    is_ready = True
    return to_not(res.start_square) + to_not(res.target_square) + translate_promote_to(res.move_flag)


def engine_proc(output_queue: mp.Queue, engine_queue: mp.Queue) -> None:
    settings = AISettings()
    board = Board()
    search = Search(board, settings)
    while True:
        if engine_queue.empty():
            continue
        inp = engine_queue.get()
        command = inp.split()
        if command[0] == 'position':
            if command[1] == 'startpos':
                board.load_start_position()
            else:
                board.load_position(command[1])
            if command[2] == 'moves':
                make_moves(board, command[3:])
        elif command[0] == 'ucinewgame':
            settings = AISettings()
            board = Board()
            search = Search(board, settings)
        elif command[0] == 'go':
            output_queue.put(f'bestmove {process_go(command[1:], settings, board, search)}\n')


def reader_proc(output_queue: mp.Queue, engine_queue: mp.Queue, sys_queue: mp.Queue, fileno: int) -> None:
    sys.stdin = os.fdopen(fileno)
    is_waiting_for_engine = False
    while True:
        if is_waiting_for_engine and not is_ready:
            continue
        elif is_waiting_for_engine:
            output_queue.put('readyok\n')
            is_waiting_for_engine = False
        inp = sys.stdin.readline().strip()
        command = inp.split()
        if command[0] == 'uci':
            output_queue.put('id name GrobBot\n')
            output_queue.put('id author ViV99\n')
            output_queue.put('uciok\n')
        elif command[0] == 'isready':
            is_waiting_for_engine = True
        elif command[0] == 'ucinewgame':
            engine_queue.put('ucinewgame')
        elif command[0] == 'position' or command[0] == 'go':
            engine_queue.put(inp)
        elif command[0] == 'quit':
            sys_queue.put('quit')


# def parse_proc(input_queue: mp.Queue[str], output_queue: mp.Queue[str], engine_queue: mp.Queue[str]) -> None:
#     while True:
#         if input_queue.empty():
#             pass
#         command = input_queue.get().split()


def write_proc(output_queue: mp.Queue) -> None:
    while True:
        if output_queue.empty():
            continue
        sys.stdout.write(output_queue.get())


if __name__ == "__main__":
    engine_queue = mp.Queue()
    output_queue = mp.Queue()
    sys_queue = mp.Queue()

    engine_process = mp.Process(target=engine_proc, args=(output_queue, engine_queue))
    engine_process.daemon = True
    engine_process.start()

    f_in = sys.stdin.fileno()
    reader_process = mp.Process(target=reader_proc, args=(output_queue, engine_queue, sys_queue, f_in))
    reader_process.daemon = False
    reader_process.start()

    writer_process = mp.Process(target=write_proc, args=(output_queue,))
    writer_process.daemon = False
    writer_process.start()

    while True:
        if sys_queue.empty():
            continue
        command = sys_queue.get()
        if command == 'quit':
            engine_process.terminate()
            reader_process.terminate()
            writer_process.terminate()
            time.sleep(0.5)
            if not engine_process.is_alive() or not reader_process.is_alive() or not writer_process.is_alive():
                engine_process.join()
                reader_process.join()
                writer_process.join()
                print("Peace")
                sys.exit(0)
