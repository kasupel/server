"""A collection of enums used by the server."""
from __future__ import annotations

import enum


class Mode(enum.Enum):
    """An enum for a gamemode."""

    CHESS = enum.auto()


class Winner(enum.Enum):
    """An enum for the winner of a game."""

    GAME_NOT_COMPLETE = enum.auto()
    HOST = enum.auto()
    AWAY = enum.auto()
    DRAW = enum.auto()


class Conclusion(enum.Enum):
    """An enum for the way a game finished."""

    GAME_NOT_COMPLETE = enum.auto()
    CHECKMATE = enum.auto()
    RESIGN = enum.auto()
    TIME = enum.auto()
    STALEMATE = enum.auto()
    THREEFOLD_REPETITION = enum.auto()
    FIFTY_MOVE_RULE = enum.auto()
    AGREED_DRAW = enum.auto()


class PieceType(enum.Enum):
    """An enum for a chess piece type."""

    PAWN = enum.auto()
    ROOK = enum.auto()
    KNIGHT = enum.auto()
    BISHOP = enum.auto()
    QUEEN = enum.auto()
    KING = enum.auto()


class Side(enum.Enum):
    """An enum for host/away."""

    HOST = enum.auto()
    AWAY = enum.auto()

    def __invert__(self) -> Side:
        """Get the other side."""
        if self == Side.HOST:
            return Side.AWAY
        return Side.HOST

    @property
    def forwards(self) -> int:
        """Return the direction that is forwards for this side."""
        if self == Side.HOST:
            return 1
        return -1


class DisconnectReason(enum.Enum):
    """Enumeration for the reason of a socket disconnect."""

    INVITE_DECLINED = enum.auto()
    NEW_CONNECTION = enum.auto()
    GAME_OVER = enum.auto()
