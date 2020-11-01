"""Utilities shared by the tests."""
import datetime
import typing
import unittest

from server import database, enums, models, utils


class KasupelTest(unittest.TestCase):
    """Test case with added utilities."""

    def assert_raises_request_error(self, fun: typing.Callable, code: int):
        """Assert that a function raises some request error."""
        try:
            fun()
        except utils.RequestError as e:
            self.assertEqual(e.code, code)
        else:
            self.assertTrue(False, 'RequestError was not raised.')


class ModelTest(KasupelTest):
    """Test case that resets the database afterward."""

    def tearDown(self):
        """Reset the database after tests."""
        database.db.drop_tables(models.MODELS)
        database.db.create_tables(models.MODELS)
        super().tearDown()


class GameTest(ModelTest):
    """Test case that generates a game object to use."""

    def setUp(self):
        """Create a game for testing."""
        super().setUp()
        self.user_1 = models.User.create(
            username='Test', password='password', _email='email'
        )
        self.user_2 = models.User.create(
            username='Test2', password='password', _email='email2'
        )
        self.game = models.Game.create(
            host=self.user_1, away=self.user_2, mode=enums.Mode.CHESS,
            main_thinking_time=datetime.timedelta(days=1),
            fixed_extra_time=datetime.timedelta(0),
            time_increment_per_turn=datetime.timedelta(minutes=1),
            started_at=datetime.datetime.now(),
            last_turn=datetime.datetime.now(),
            host_time=datetime.timedelta(minutes=10),
            away_time=datetime.timedelta(minutes=10)
        )
