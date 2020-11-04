"""Test the type hinted parameter converter utility."""
import datetime
import typing

from server import enums, models
from server.utils import converters

from .utils import KasupelTest, ModelTest


class TestConverters(KasupelTest):
    """Test the type hinted parameter converter utility."""

    def test_str_to_int(self):
        """Test converting a string to an integer."""
        @converters.wrap
        def inner_test(param: int):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, 42)
        inner_test(param='42')

    def test_int_to_int(self):
        """Test converting an integer to an integer."""
        @converters.wrap
        def inner_test(param: int):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, 15)
        inner_test(param=15)

    def test_text_to_int(self):
        """Test trying to convert random text to an integer."""
        @converters.wrap
        def inner_test(param: int):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(
            lambda: inner_test(param='foo'), 3111
        )

    def test_dict_to_int(self):
        """Test trying to convert a dict to an integer."""
        @converters.wrap
        def inner_test(param: int):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(
            lambda: inner_test(param={'foo': 123}), 3111
        )

    def test_base64_to_bytes(self):
        """Test converting base 64 to bytes."""
        @converters.wrap
        def inner_test(param: bytes):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, b'test')
        inner_test(param='dGVzdA==')

    def test_bytes_to_bytes(self):
        """Test converting bytes to bytes."""
        @converters.wrap
        def inner_test(param: bytes):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, b'Test bytes.')
        inner_test(param=b'Test bytes.')

    def test_invalid_base64_to_bytes(self):
        """Test trying to convert invalid base 64 to bytes."""
        @converters.wrap
        def inner_test(param: bytes):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(
            lambda: inner_test(param='foobar='), 3112
        )

    def test_str_to_str(self):
        """Test converting a string to a string."""
        @converters.wrap
        def inner_test(param: str):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, 'Test string.')
        inner_test(param='Test string.')

    def test_int_to_str(self):
        """Test converting an integer to a string."""
        @converters.wrap
        def inner_test(param: str):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, '256')
        inner_test(param=256)

    def test_dict_to_dict(self):
        """Test converting a dict to a dict."""
        @converters.wrap
        def inner_test(param: dict):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, {'foo': 1, 'bar': ['bat', 2]})
        inner_test(param={'foo': 1, 'bar': ['bat', 2]})

    def test_str_to_dict(self):
        """Test trying to convert a string to a dict."""
        @converters.wrap
        def inner_test(param: dict):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(
            lambda: inner_test(param='{"json": "Not allowed."}'), 3113
        )

    def test_int_to_timedelta(self):
        """Test converting an integer to a timedelta."""
        @converters.wrap
        def inner_test(param: datetime.timedelta):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, datetime.timedelta(
                days=3, hours=2, minutes=5, seconds=43
            ))
        inner_test(param=266743)

    def test_negative_timedelta(self):
        """Test trying to convert a negative number to a timedelta."""
        @converters.wrap
        def inner_test(param: datetime.timedelta):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(
            lambda: inner_test(param='-60'), 3117
        )

    def test_int_to_enum(self):
        """Test converting an integer to an enum."""
        @converters.wrap
        def inner_test(param: enums.Conclusion):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, enums.Conclusion.STALEMATE)
        inner_test(param=5)

    def test_enum_out_of_range(self):
        """Test converting an integer that is too big to an enum."""
        @converters.wrap
        def inner_test(param: enums.DisconnectReason):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(lambda: inner_test(param='4'), 3114)

    def test_null_required_argument(self):
        """Test passing None for a required argument."""
        @converters.wrap
        def inner_test(param: str):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(lambda: inner_test(param=None), 3101)

    def test_default_argument(self):
        """Test using a default argument."""
        @converters.wrap
        def inner_test(param: int = 5):
            """Make sure the default was used."""
            self.assertEqual(param, 5)
        inner_test()

    def test_default_argument_null(self):
        """Test explicitly passing null to a default argument."""
        @converters.wrap
        def inner_test(param: int = 14):
            """Make sure the default was used."""
            self.assertEqual(param, 14)
        inner_test(param=None)

    def test_self_argument(self):
        """Test using self as the first argument."""
        sentinel = object()
        actual_self = self

        @converters.wrap
        def inner_test(self: typing.Any):
            """Make sure the self parameter was not touched."""
            actual_self.assertEqual(self, sentinel)
        inner_test(sentinel)

    def test_user_argument_not_passed(self):
        """Test using user as the first argument but not passing it."""
        @converters.wrap
        def inner_test(user: models.User):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(inner_test, 1301)

    def test_cls_and_user(self):
        """Test passing both cls and user arguments."""
        sentinel_1 = object()
        sentinel_2 = object()

        @converters.wrap
        def inner_test(cls: typing.Any, user: models.User):
            """Make sure the self parameter was not touched."""
            self.assertEqual(cls, sentinel_1)
            self.assertEqual(user, sentinel_2)
        inner_test(sentinel_1, user=sentinel_2)

    def test_no_user_argument_but_passed(self):
        """Test passing user when it is not used as an argument."""
        @converters.wrap
        def inner_test():
            """If this runs without error, the test has passed."""
            pass
        inner_test(user=object())

    def test_extra_argument(self):
        """Test passing an extra argument to a converter wrapped function."""
        @converters.wrap
        def inner_test():
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(lambda: inner_test(param=3), 3102)

    def test_missing_argument(self):
        """Test not passing a required argument."""
        @converters.wrap
        def inner_test(param: int):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(inner_test, 3102)


class TestModelConverters(ModelTest):
    """Test converters for models."""

    def test_notification_converter(self):
        """Test converting an integer to a notification."""
        user = models.User.create(
            username='Test', password='password', _email='email'
        )
        notif = models.Notification.create(
            user=user, type_code='accounts.welcome'
        )

        @converters.wrap
        def inner_test(param: models.Notification):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, notif)
        inner_test(param=notif.id)

    def test_game_converter(self):
        """Test converting an integer represented as a string to a game."""
        host = models.User.create(
            username='Test', password='password', _email='email'
        )
        away = models.User.create(
            username='Test2', password='password', _email='email2'
        )
        game = models.Game.create(
            host=host, away=away, mode=enums.Mode.CHESS,
            main_thinking_time=datetime.timedelta(days=1),
            fixed_extra_time=datetime.timedelta(0),
            time_increment_per_turn=datetime.timedelta(minutes=1),
            started_at=datetime.datetime.now(),
            last_turn=datetime.datetime.now(),
            host_time=datetime.timedelta(minutes=10),
            away_time=datetime.timedelta(minutes=10)
        )

        @converters.wrap
        def inner_test(param: models.Game):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, game)
        inner_test(param=str(game.id))

    def test_game_not_found(self):
        """Test trying to convert to a game with a non-existant ID."""
        @converters.wrap
        def inner_test(param: models.Game):
            """This shouldn't be called, converting should fail."""
            pass
        self.assert_raises_request_error(lambda: inner_test(param=5), 2001)

    def test_user_converter(self):
        """Test converting a username to a user."""
        user = models.User.create(
            username='Test', password='password', _email='email'
        )

        @converters.wrap
        def inner_test(param: models.User):
            """Make sure the parameter was converted correctly."""
            self.assertEqual(param, user)
        inner_test(param='Test')
