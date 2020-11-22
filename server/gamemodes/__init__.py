"""Collate the gamemodes."""
from . import chess
from .gamemode import GameMode    # noqa: F401
from .. import enums


GAMEMODES = {
    enums.Mode.CHESS: chess.Chess
}
