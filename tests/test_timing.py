"""Test the timing module."""
from datetime import datetime, timedelta

from server import enums

from .utils import GameTest


class TestTiming(GameTest):
    """Test the timing module."""

    def test_no_extra_time(self):
        """Test timing boundary and decrements with no extra time."""
        self.game.fixed_extra_time = timedelta(0)
        self.game.time_increment_per_turn = timedelta(0)
        self.game.host_time = timedelta(hours=1)
        self.game.last_turn = datetime(year=2000, month=1, day=1)
        self.assertEqual(
            self.game.timer.boundary,
            datetime(year=2000, month=1, day=1, hour=1)
        )
        self.game.timer.turn_end(
            enums.Side.HOST,
            current_time=datetime(year=2000, month=1, day=1, minute=30)
        )
        self.assertEqual(self.game.host_time, timedelta(minutes=30))

    def test_partially_used_fixed_extra_time(self):
        """Test when there is partially unused fixed extra time."""
        self.game.fixed_extra_time = timedelta(minutes=10)
        self.game.time_increment_per_turn = timedelta(0)
        self.game.away_time = timedelta(minutes=30)
        self.game.last_turn = datetime(year=2000, month=1, day=1)
        self.game.current_turn = enums.Side.AWAY
        self.assertEqual(
            self.game.timer.boundary,
            datetime(year=2000, month=1, day=1, minute=40)
        )
        self.game.timer.turn_end(
            enums.Side.AWAY,
            current_time=datetime(year=2000, month=1, day=1, minute=7)
        )
        self.assertEqual(self.game.away_time, timedelta(minutes=30))

    def test_used_fixed_extra_time(self):
        """Test when the fixed extra time is exceeded."""
        self.game.fixed_extra_time = timedelta(hours=1)
        self.game.time_increment_per_turn = timedelta(0)
        self.game.host_time = timedelta(seconds=5)
        self.game.last_turn = datetime(year=2000, month=1, day=1)
        self.assertEqual(
            self.game.timer.boundary,
            datetime(year=2000, month=1, day=1, hour=1, second=5)
        )
        self.game.timer.turn_end(
            enums.Side.HOST,
            current_time=datetime(
                year=2000, month=1, day=1, hour=1, second=4
            )
        )
        self.assertEqual(self.game.host_time, timedelta(seconds=1))

    def test_time_increment_per_turn(self):
        """Test when a time increment is given per turn."""
        self.game.fixed_extra_time = timedelta(0)
        self.game.time_increment_per_turn = timedelta(minutes=1, seconds=30)
        self.game.away_time = timedelta(days=1)
        self.game.last_turn = datetime(year=2000, month=1, day=1)
        self.game.current_turn = enums.Side.AWAY
        self.assertEqual(
            self.game.timer.boundary, datetime(year=2000, month=1, day=2)
        )
        self.game.timer.turn_end(
            enums.Side.AWAY,
            current_time=datetime(
                year=2000, month=1, day=1, hour=7
            )
        )
        self.assertEqual(self.game.away_time, timedelta(
            hours=17, minutes=1, seconds=30
        ))

    def test_increment_and_fixed_extra_time(self):
        """Test when there is a per-turn increment and fixed extra time."""
        self.game.fixed_extra_time = timedelta(hours=1)
        self.game.time_increment_per_turn = timedelta(minutes=10)
        self.game.host_time = timedelta(days=5)
        self.game.last_turn = datetime(year=2000, month=1, day=1)
        self.assertEqual(
            self.game.timer.boundary,
            datetime(year=2000, month=1, day=6, hour=1)
        )
        self.game.timer.turn_end(
            enums.Side.HOST,
            current_time=datetime(
                year=2000, month=1, day=1, hour=1, minute=5
            )
        )
        self.assertEqual(self.game.host_time, timedelta(days=5, minutes=5))
