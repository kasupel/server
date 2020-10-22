"""Various Peewee models."""
from __future__ import annotations

import base64
import datetime
import enum
import functools
import hashlib
import hmac
import json
import os
import pathlib
import random
import string
import typing

import peewee as pw

import playhouse.postgres_ext as pw_postgres

from . import config, events, images, timing
from .endpoints import converters, helpers


def hash_password(password: str) -> str:
    """Hash a password."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha3-256', password.encode(), salt, 100_000)
    return salt + key


def check_password(password: str, hashed: str) -> bool:
    """Check a password against a hash."""
    salt = hashed[:32]
    key = hashed[32:]
    attempt_key = hashlib.pbkdf2_hmac(
        'sha3-256', password.encode(), salt, 100_000
    )
    return hmac.compare_digest(key, attempt_key)


def generate_verification_token() -> str:
    """Generate a verification token.

    This will be 6 numbers or uppercase letters.
    """
    random.seed(os.urandom(32))
    return ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )


db = pw_postgres.PostgresqlExtDatabase(
    config.DB_NAME, user=config.DB_USER, password=config.DB_PASSWORD
)


class HashedPassword:
    """A class to check for equality against hashed passwords."""

    def __init__(self, hashed_password: str):
        """Store the hashed password."""
        self.hashed_password = hashed_password

    def __eq__(self, password: str) -> bool:
        """Check for equality against an unhashed password."""
        return check_password(password, self.hashed_password)


class TurnCounter:
    """A counter for the turn of a game."""

    def __init__(self, game: Game):
        """Store game."""
        self.game = game

    def __int__(self) -> int:
        """Get the turn number."""
        # _turn_number is internal, but this is the class that changes it
        return self.game._turn_number

    def __str__(self) -> str:
        """Get the turn number as a string."""
        return str(self.game._turn_number)

    def __iadd__(self, value: int):
        """Increment the turn."""
        if value != 1:
            raise ValueError(
                'Cannot increment the turn counter by more than one.'
            )
        self.game._turn_number += 1
        self.game.timer.turn_end(self.game.current_turn)
        self.game.current_turn = ~self.game.current_turn
        arrangement = self.game.game_mode.freeze_game()
        GameState.create(
            game=self.game, turn_number=self.game._turn_number,
            arrangement=arrangement
        )
        self.game.save()


class Mode(enum.Enum):
    """An enum for a gamemode."""

    CHESS = enum.auto()


class Winner(enum.Enum):
    """An enum for the winner of a game."""

    GAME_NOT_COMPLETE = enum.auto()
    HOME = enum.auto()
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
    """An enum for home/away."""

    HOME = enum.auto()
    AWAY = enum.auto()

    def __invert__(self) -> Side:
        """Get the other side."""
        if self == Side.HOME:
            return Side.AWAY
        return Side.HOME

    @property
    def forwards(self) -> int:
        """Return the direction that is forwards for this side."""
        if self == Side.HOME:
            return 1
        return -1


class EnumField(pw.SmallIntegerField):
    """A field where each value is an integer representing an option."""

    def __init__(
            self, options: enum.Enum, **kwargs: dict[str, typing.Any]):
        """Create a new enum field."""
        self.options = options
        super().__init__(**kwargs)

    def python_value(self, raw: typing.Any) -> enum.Enum:
        """Convert a raw number to an enum value."""
        if raw is None:
            return None
        number = super().python_value(raw)
        return self.options(number)

    def db_value(self, instance: enum.Enum) -> typing.Any:
        """Convert an enum value to a raw number."""
        if instance is None:
            return super().db_value(None)
        if not isinstance(instance, self.options):
            raise TypeError(f'Instance is not of enum class {self.options}.')
        number = instance.value
        return super().db_value(number)


class JsonField(pw.CharField):
    """A field to store JSON data."""

    def python_value(self, raw: typing.Any) -> dict[str, typing.Any]:
        """Convert a raw string to a python value."""
        return json.loads(super().python_value(raw))

    def db_value(self, instance: dict[str, typing.Any]) -> typing.Any:
        """Convert a python value to a raw string."""
        return super().db_value(json.dumps(instance))


class BaseModel(pw.Model):
    """A base model, that sets the DB."""

    class Meta:
        """Set the DB and use new table names."""

        database = db
        use_legacy_table_names = False

    def __repr__(self, indent: int = 1) -> str:
        """Represent the model as a string."""
        values = {}
        for field in type(self)._meta.sorted_field_names:
            values[field] = getattr(self, field)
        main = []
        for field in values:
            if isinstance(values[field], datetime.datetime):
                value = f"'{values[field]}'"
            elif isinstance(values[field], pw.Model):
                value = values[field].__str__(indent=indent + 1)
            elif isinstance(values[field], enum.Enum):
                value = values[field].name
            else:
                value = repr(values[field])
            main.append(f'{field}={value}')
        end_indent = '    ' * (indent - 1)
        indent = '\n' + '    ' * indent
        return (
            f'<{type(self).__name__}{indent}'
            + indent.join(main)
            + f'\n{end_indent}>'
        )

    @classmethod
    def converter(cls, value: typing.Union[int, str]) -> pw.Model:
        """Convert a parameter to an instance of the model."""
        field_name = getattr(cls.KasupelMeta, 'primary_parameter_key', 'id')
        field = getattr(cls, field_name)
        if isinstance(field, pw.AutoField):
            base_converter = converters.int_converter
        elif isinstance(field, pw.CharField):
            base_converter = lambda x: x    # noqa: E731
        else:
            raise RuntimeError(f'Converter needed for field {field!r}.')
        model_id = base_converter(value)
        try:
            return cls.get(field == model_id)
        except cls.DoesNotExist:
            raise helpers.RequestError(cls.KasupelMeta.not_found_error)


class User(BaseModel):
    """A model to represent a user."""

    username = pw.CharField(max_length=32, unique=True)
    password_hash = pw.BlobField()
    _email = pw.CharField(max_length=255, unique=True, column_name='email')
    email_verify_token = pw.CharField(max_length=6, null=True)
    elo = pw.SmallIntegerField(default=1000)
    created_at = pw.DateTimeField(default=datetime.datetime.now)

    _avatar = pw.BlobField(null=True, column_name='avatar')
    avatar_number = pw.SmallIntegerField(default=0)
    avatar_extension = pw.CharField(max_length=4, null=True)

    class KasupelMeta:
        """Set the "not found" error code and use username as key."""

        not_found_error = 1001
        primary_parameter_key = 'username'

    @classmethod
    def login(
            cls, username: str, password: str,
            token: bytes) -> typing.Optional[Session]:
        """Create a session if the credentials are correct."""
        try:
            user = cls.get(cls.username == username)
        except pw.DoesNotExist:
            raise helpers.RequestError(1001)
        if user.password != password:
            raise helpers.RequestError(1302)
        session = Session.create(user=user, token=token)
        return session

    @property
    def avatar(self) -> bytes:
        """Get the avatar as bytes."""
        return bytes(self.avatar) if self.avatar else None

    @avatar.setter
    def avatar(self, new: bytes):
        """Set the avatar and increment the avatar number."""
        ext = images.validate(new)
        self.avatar_extension = ext
        self.avatar_number += 1
        self._avatar = new

    @property
    def avatar_name(self) -> typing.Optional[str]:
        """Get a file name to represent the avatar."""
        if self.avatar:
            return f'{self.id}-{self.avatar_number}.{self.avatar_extension}'

    @property
    def password(self) -> HashedPassword:
        """Return an object that will use hashing in it's equality check."""
        return HashedPassword(self.password_hash)

    @password.setter
    def password(self, password: str):
        """Set the password to a hash of the provided password.

        Also clears all sessions.
        """
        self.password_hash = hash_password(password)
        if self.id:    # Will be None on initialisation.
            Session.delete().where(Session.user == self).execute()

    @property
    def email(self) -> str:
        """Get the user's email."""
        return self._email

    @email.setter
    def email(self, new_email: str):
        """Set the user's email and generate an email verification token."""
        self._email = new_email
        self.email_verify_token = generate_verification_token()

    @property
    def email_verified(self) -> bool:
        """Check if the user has a verified email."""
        return self._email and not self.email_verify_token

    @email_verified.setter
    def email_verified(self, verified: bool):
        """Mark the user's email as verified."""
        if not verified:
            self.email_verify_token = generate_verification_token()
        else:
            self.email_verify_token = None

    @property
    def socket_id(self) -> str:
        """Get the ID of a socket the user is connected to, if any."""
        game = Game.get_or_none(
            (
                Game.host == self & Game.host_socket_id != None    # noqa:E711
            ) | (
                Game.away == self & Game.away_socket_id != None    # noqa:E711
            )
        )
        if not game:
            return
        if game.host == self:
            return game.host_socket_id
        return game.away_socket_id

    def to_json(
            self, hide_email: bool = True) -> dict[str, typing.Any]:
        """Get a dict representation of this user."""
        response = {
            'id': self.id,
            'username': self.username,
            'elo': self.elo,
            'avatar_url': f'/media/avatar/{self.avatar_name}',
            'created_at': int(self.created_at.timestamp())
        }
        if not hide_email:
            response['email'] = self.email
        return response


class Notification(BaseModel):
    """Represents a notification to be delivered to the user."""

    _notification_type_file = (
        pathlib.Path(__file__).parent.absolute()
        / 'res' / 'notifications.json'
    )
    with open(_notification_type_file) as f:
        NOTIFICATION_TYPES = json.load(f)

    user = pw.ForeignKeyField(model=User, backref='notifications')
    sent_at = pw.DateTimeField(default=datetime.datetime.now)
    type_code = pw.SmallIntegerField()
    values = JsonField()
    read = pw.BooleanField(default=False)

    class KasupelMeta:
        """Set the "not found" error code and use username as key."""

        not_found_error = 1401

    @classmethod
    def send(
            cls, user: User, type_code: int, **values: dict[str, typing.Any]):
        """Create a new notification."""
        notif = cls.create(user=user, type_code=type_code, values=values)
        if user.socket_id:
            events.send_notification(user.socket_id, notif)

    def display(self) -> str:
        """Get the notification as it should be displayed to the user."""
        fmt = self.NOTIFICATION_TYPES[str(self.type_code)]
        return fmt.format(**self.values)

    def to_json(self) -> dict[str, typing.Any]:
        """Represent as a python dict."""
        return {
            'id': self.id,
            'sent_at': self.sent_at.to_timestamp(),
            'type_code': self.type_code,
            'values': self.values,
            'read': self.read
        }


class Session(BaseModel):
    """A model to represent an authentication session for a user."""

    MAX_AGE = datetime.timedelta(days=config.MAX_SESSION_AGE)

    user = pw.ForeignKeyField(model=User, backref='sessions')
    token = pw.BlobField()
    created_at = pw.DateTimeField(default=datetime.datetime.now)

    @property
    def expired(self) -> bool:
        """Check if the session has expired."""
        age = datetime.datetime.now() - self.created_at
        return age > Session.MAX_AGE

    def __str__(self) -> str:
        """Display as base 64."""
        return base64.b64encode(self.token).decode()


class Game(BaseModel):
    """A model to represent a game.

    The game may be in any of the following states:
      1. Open
          A player is looking for a game matching these specs, but a second
          player has yet to be found.
      2. In progress
          There are two players in this game, who are currently playing.
      3. Completed
          This game has ended - either there is a winner, or it was a draw.
    """

    host = pw.ForeignKeyField(model=User, backref='host_games', null=True)
    away = pw.ForeignKeyField(model=User, backref='away_games', null=True)
    invited = pw.ForeignKeyField(model=User, backref='invites', null=True)
    current_turn = EnumField(Side, default=Side.HOME)
    _turn_number = pw.SmallIntegerField(default=1, column_name='turn_number')
    mode = EnumField(Mode)
    last_kill_or_pawn_move = pw.SmallIntegerField(default=1)

    # initial timer value for each player
    main_thinking_time = pw_postgres.IntervalField()
    # time given to each player each turn before the main time is affected
    fixed_extra_time = pw_postgres.IntervalField()
    # amount timer is incremented after each turn
    time_increment_per_turn = pw_postgres.IntervalField()

    # timers at the start of the current turn, null means main_thinking_time
    home_time = pw_postgres.IntervalField(null=True)
    away_time = pw_postgres.IntervalField(null=True)

    home_offering_draw = pw.BooleanField(default=False)
    away_offering_draw = pw.BooleanField(default=False)
    other_valid_draw_claim = EnumField(Conclusion, null=True)

    winner = EnumField(Winner, default=Winner.GAME_NOT_COMPLETE)
    conclusion_type = EnumField(
        Conclusion, default=Conclusion.GAME_NOT_COMPLETE
    )
    opened_at = pw.DateTimeField(default=datetime.datetime.now)
    last_turn = pw.DateTimeField(null=True)
    started_at = pw.DateTimeField(null=True)
    ended_at = pw.DateTimeField(null=True)

    host_socket_id = pw.CharField(null=True)
    away_socket_id = pw.CharField(null=True)

    class KasupelMeta:
        """Set the "not found" error code."""

        not_found_error = 2001

    def __init__(
            self, *args: tuple[typing.Any],
            **kwargs: dict[str, typing.Any]):
        """Create a game."""
        super().__init__(*args, **kwargs)
        self.turn_number = TurnCounter(self)
        self.home_time = self.main_thinking_time
        self.away_time = self.main_thinking_time
        self.timer = timing.Timer(self)

    def start_game(self, away: User):
        """Start a game."""
        self.invited = None
        self.away = away
        self.started_at = datetime.datetime.now()
        self.last_turn = datetime.datetime.now()
        self.save()

    @functools.cached_property
    def game_mode(self) -> gamemodes.GameMode:
        """Get a game mode instance for this game.

        This is implemented as a cached property rather than set on
        initialisation as Peewee seems to set some properties after
        initialisation in some cases.
        """
        return gamemodes.GAMEMODES[self.mode - 1](self)

    def to_json(self) -> dict[str, typing.Any]:
        """Get a dict representation of this game."""
        return {
            'id': self.id,
            'mode': self.mode.value,
            'host': self.host.to_json() if self.host else None,
            'away': self.away.to_json() if self.away else None,
            'invited': self.invited.to_json() if self.invited else None,
            'current_turn': self.current_turn.value,
            'turn_number': int(self.turn_number),
            'main_thinking_time': self.main_thinking_time.total_seconds(),
            'fixed_extra_time': self.fixed_extra_time.total_seconds(),
            'time_increment_per_turn': (
                self.time_increment_per_turn.total_seconds()
            ),
            'home_time': (
                self.home_time or self.main_thinking_time
            ).total_seconds(),
            'away_time': (
                self.away_time or self.main_thinking_time
            ).total_seconds(),
            'home_offering_draw': self.home_offering_draw,
            'away_offering_draw': self.away_offering_draw,
            'winner': self.winner.value,
            'conclusion_type': self.conclusion_type.value,
            'opened_at': self.opened_at.timestamp(),
            'started_at': (
                self.started_at.timestamp() if self.started_at else None
            ),
            'last_turn': (
                self.last_turn.timestamp() if self.last_turn else None
            ),
            'ended_at': self.ended_at.timestamp() if self.ended_at else None
        }


class Piece(BaseModel):
    """A model to represent a piece in a game."""

    piece_type = EnumField(PieceType)
    rank = pw.SmallIntegerField()
    file = pw.SmallIntegerField()
    side = EnumField(Side)
    has_moved = pw.BooleanField(default=False)
    first_move_last_turn = pw.BooleanField(default=False)    # For en passant
    game = pw.ForeignKeyField(model=Game, backref='pieces')


class GameState(BaseModel):
    """A model to represent a snapshot of a game.

    Theoretically, this could replace Piece, but we leave Piece for the
    current turn for ease of use.
    """

    game = pw.ForeignKeyField(model=Game, backref='pieces')
    turn_number = pw.SmallIntegerField()
    arrangement = pw.CharField(max_length=128)


HostUser = User.alias()
AwayUser = User.alias()
InvitedUser = User.alias()

db.create_tables([User, Session, Game, Piece, GameState])


from . import gamemodes    # noqa: E402 - avoiding circular import
