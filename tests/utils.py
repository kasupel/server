"""Utilities shared by the tests."""
import typing
import unittest

from server import database, models, utils


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
