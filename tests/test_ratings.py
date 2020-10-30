"""Tests for the ELO rating system."""
from server import enums, ratings

from .utils import KasupelTest


class TestRatings(KasupelTest):
    """Tests for the ELO rating system."""

    def _test_match(
            self, host_elo: int, away_elo: int, winner: enums.Winner,
            expected_host: int, expected_away: int):
        """Test a match, and the reverse of it."""
        # As given:
        actual = ratings.calculate(host_elo, away_elo, winner, k_factor=32)
        self.assertEqual(actual, (expected_host, expected_away))
        # Reversed:
        if winner == enums.Winner.HOST:
            winner = enums.Winner.AWAY
        elif winner == enums.Winner.AWAY:
            winner = enums.Winner.HOST
        actual = ratings.calculate(away_elo, host_elo, winner, k_factor=32)
        self.assertEqual(actual, (expected_away, expected_host))

    def test_win_equal(self):
        """Test when the players start with equal ELO and the host wins."""
        self._test_match(1500, 1500, enums.Winner.HOST, 1516, 1484)

    def test_win_likely(self):
        """Test when a high ELO player beats a low ELO player."""
        self._test_match(2000, 1000, enums.Winner.HOST, 2000, 1000)

    def test_win_unlikely(self):
        """Test when a low ELO player beats a high ELO player."""
        self._test_match(1000, 2000, enums.Winner.HOST, 1032, 1968)

    def test_draw_equal(self):
        """Test when equal ELO players draw."""
        self._test_match(800, 800, enums.Winner.DRAW, 800, 800)

    def test_draw_disparity(self):
        """Test when a high and low ELO player draw."""
        self._test_match(1200, 1400, enums.Winner.DRAW, 1208, 1392)
