"""Utilities for controlling the timers."""
from __future__ import annotations

import datetime

from . import config, enums, events, models


def timer_check(current_time: datetime.datetime = None):
    """Check for games where the player on move has timed out."""
    current_time = current_time or datetime.datetime.now()
    games = models.Game.select().where(
        (
            (models.Game.current_turn == enums.Side.HOST)
            & ((
                models.Game.last_turn
                + models.Game.host_time
                + models.Game.fixed_extra_time
            ) > current_time)
        ) | (
            (models.Game.current_turn == enums.Side.AWAY)
            & ((
                models.Game.last_turn
                + models.Game.away_time
                + models.Game.fixed_extra_time
            ) > current_time)
        )
    )
    for game in games:
        events.end_game(game)


def timer_loop():    # pragma: no cover
    """Loop timer_check forever."""
    if not config.TIMER_CHECK_INTERVAL:
        # The loop is disabled, we will rely on client reports.
        return
    while True:
        timer_check()
        events.socketio.sleep(config.TIMER_CHECK_INTERVAL)


class Timer:
    """A timer for a game.

    It retains no state other than a references to a game in the database.
    Therefore, each time it is needed, a new instance can be created or an
    existing one can be used - it makes no difference.
    """

    def __init__(self, game: models.Game):
        """Store the game we are interested in."""
        self.game = game

    def turn_end(
            self, side: enums.Side, current_time: datetime.datetime = None):
        """Increment timers for the end of a turn."""
        last_turn = self.game.last_turn
        current_time = current_time or datetime.datetime.now()
        turn_length = current_time - last_turn
        if turn_length > self.game.fixed_extra_time:
            main_time_used = turn_length - self.game.fixed_extra_time
        else:
            main_time_used = datetime.timedelta(0)
        timer_delta = self.game.time_increment_per_turn - main_time_used
        if side == enums.Side.HOST:
            self.game.host_time += timer_delta
        else:
            self.game.away_time += timer_delta
        self.game.last_turn = current_time

    @property
    def boundary(self) -> datetime.datetime:
        """Return the time the current player will run out of time."""
        current_timer = (
            self.game.host_time
            if self.game.current_turn == enums.Side.HOST
            else self.game.away_time
        )
        return (
            self.game.last_turn
            + current_timer
            + self.game.fixed_extra_time
        )
