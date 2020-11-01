"""Test the timing module."""
from datetime import datetime, timedelta

from server import enums, timing

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

    def test_catch_no_extra_time(self):
        """Test timer_check catching a timeout with no extra time."""
        self.game.fixed_extra_time = timedelta(0)
        self.game.host_time = timedelta(minutes=10)
        self.game.last_turn = datetime(year=2050, month=10, day=5)
        self.game.save()
        timing.timer_check(current_time=datetime(
            year=2050, month=10, day=5, hour=1
        ))
        self.assertEqual(self.game.refresh().winner, enums.Winner.AWAY)

    def test_no_catch_extra_time(self):
        """Test not catching what would be a timeout if not for extra time."""
        self.game.fixed_extra_time = timedelta(hours=1, minutes=30)
        self.game.host_time = timedelta(days=1)
        self.game.last_turn = datetime(year=1999, month=6, day=14)
        self.game.save()
        timing.timer_check(current_time=datetime(
            year=1999, month=6, day=15, minute=30
        ))
        self.assertEqual(
            self.game.refresh().winner, enums.Winner.GAME_NOT_COMPLETE
        )

    def test_catch_extra_time(self):
        """Test timer_check catching a timeout with extra time."""
        self.game.fixed_extra_time = timedelta(seconds=10)
        self.game.away_time = timedelta(minutes=3, seconds=34)
        self.game.last_turn = datetime(
            year=2020, month=1, day=30, hour=13, minute=25, second=14
        )
        self.game.current_turn = enums.Side.AWAY
        self.game.save()
        timing.timer_check(current_time=datetime(
            year=2020, month=1, day=30, hour=13, minute=28, second=59
        ))
        self.assertEqual(
            self.game.refresh().winner, enums.Winner.HOST
        )

    def test_no_catch_no_extra_time(self):
        """Test timer_check not catching what is not a timeout."""
        self.game.fixed_extra_time = timedelta(0)
        self.game.away_time = timedelta(minutes=15)
        self.game.last_turn = datetime(year=2000, month=4, day=20)
        self.game.current_turn = enums.Side.AWAY
        self.game.save()
        timing.timer_check(current_time=datetime(
            year=2000, month=4, day=20, hour=0, minute=14, second=55
        ))
        self.assertEqual(
            self.game.refresh().winner, enums.Winner.GAME_NOT_COMPLETE
        )
