import re
from move import Move
from abc import ABC, abstractmethod


class Command:
    __slots__ = {'is_for_engine', '_name'}

    def __init__(self, is_for_engine: bool, name: str):
        self.is_for_engine = is_for_engine
        self._name = name


class UCI(Command):

    def __init__(self):
        super().__init__(True, 'uci')

class IsReady(Command):

    def __init__(self):
        super().__init__(True, 'isready')
