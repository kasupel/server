"""A collection of the game modes (currently only chess)."""
from __future__ import annotations

import typing

from .. import enums, models


class GameMode:
    """A base class for games, not intended to be used itself."""

    def __init__(self, game: models.Game):
        """Store the game we are interested in."""
        self.game = game

    def layout_board(self):
        """Put the pieces on the board."""
        raise NotImplementedError    # pragma: no cover

    def make_move(self, **move_data: dict[str, typing.Any]) -> bool:
        """Validate and apply a move."""
        raise NotImplementedError    # pragma: no cover

    def possible_moves(self, side: enums.Side) -> typing.Iterator[
            tuple[models.Piece, int, int]]:
        """Get all possible moves for a side."""
        raise NotImplementedError    # pragma: no cover

    def game_is_over(self) -> enums.Conclusion:
        """Check if the game has been won or tied.

        If the return value is checkmate, the player whose turn it currently
        is is in checkmate. This method must be called after the GameState
        for the current turn has been created.
        """
        raise NotImplementedError    # pragma: no cover

    def freeze_game(self) -> str:
        """Store a snapshot of a game as a string."""
        raise NotImplementedError    # pragma: no cover
