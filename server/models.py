"""Various Peewee models."""
from __future__ import annotations

import base64
import datetime
import enum
import functools
import json
import os
import pathlib
import random
import string
import typing

import peewee as pw

import playhouse.postgres_ext as pw_postgres

from . import (
    config, database, enums, events, gamemodes, timing, utils
)
from .utils import hashing, images


def generate_verification_token() -> str:
    """Generate a verification token.

    This will be 6 numbers or uppercase letters.
    """
    random.seed(os.urandom(32))
    return ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )


class TurnCounter:
    """A counter for the turn of a game."""

    def __init__(self, game: Game):
        """Store game."""
        self.game = game

    def __int__(self) -> int:
        """Get the turn number."""
        # _turn_number is internal, but this is the class that changes it
        return self.game._turn_number

    def __iadd__(self, value: int):
        """Increment the turn."""
        if value != 1:    # pragma: no cover
            raise ValueError(
                'Cannot increment the turn counter by more than one.'
            )
        self.game._turn_number += 1
        self.game.timer.turn_end(self.game.current_turn)
        self.game.current_turn = ~self.game.current_turn
        self.game.host_offering_draw = False
        self.game.away_offering_draw = False
        arrangement = self.game.game_mode.freeze_game()
        GameState.create(
            game=self.game, turn_number=self.game._turn_number,
            arrangement=arrangement
        )
        self.game.save()
        if self.game.current_turn == enums.Side.HOST:
            on_move = self.game.host
        else:
            on_move = self.game.away
        Notification.send(on_move, 'games.ongoing.turn', self.game)


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


class User(database.BaseModel):
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
            raise utils.RequestError(1001)
        if user.password != password:
            raise utils.RequestError(1302)
        session = Session.create(user=user, token=token)
        return session

    @property
    def avatar(self) -> bytes:
        """Get the avatar as bytes."""
        return bytes(self._avatar) if self._avatar else None

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
    def password(self) -> hashing.HashedPassword:
        """Return an object that will use hashing in it's equality check."""
        return hashing.HashedPassword(self.password_hash)

    @password.setter
    def password(self, password: str):
        """Set the password to a hash of the provided password.

        Also clears all sessions.
        """
        self.password_hash = hashing.hash_password(password)
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
                (Game.host == self) & (Game.host_socket_id != None)    # noqa:E711
            ) | (
                (Game.away == self) & (Game.away_socket_id != None)    # noqa:E711
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


class Session(database.BaseModel):
    """A model to represent an authentication session for a user."""

    MAX_AGE = datetime.timedelta(days=config.MAX_SESSION_AGE)

    user = pw.ForeignKeyField(model=User, backref='sessions')
    token = pw.BlobField()
    created_at = pw.DateTimeField(default=datetime.datetime.now)

    @classmethod
    def validate_session_key(
            cls, session_id: typing.Union[int, str],
            session_token: str) -> typing.Optional[Session]:
        """Get a session for a session ID and token."""
        if isinstance(session_id, str):
            try:
                session_id = int(session_id)
            except ValueError:
                raise utils.RequestError(1309)
        try:
            session_token = base64.b64decode(session_token)
        except ValueError:
            raise utils.RequestError(3112)
        try:
            session = Session.get_by_id(session_id)
        except pw.DoesNotExist:
            raise utils.RequestError(1304)
        if session_token != bytes(session.token):
            raise utils.RequestError(1305)
        if session.expired:
            session.delete_instance()
            raise utils.RequestError(1306)
        return session

    @property
    def expired(self) -> bool:
        """Check if the session has expired."""
        age = datetime.datetime.now() - self.created_at
        return age > Session.MAX_AGE

    def __str__(self) -> str:
        """Display as base 64."""
        return base64.b64encode(self.token).decode()


class Game(database.BaseModel):
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
    current_turn = EnumField(enums.Side, default=enums.Side.HOST)
    _turn_number = pw.SmallIntegerField(default=1, column_name='turn_number')
    mode = EnumField(enums.Mode)
    last_kill_or_pawn_move = pw.SmallIntegerField(default=1)

    # initial timer value for each player
    main_thinking_time = pw_postgres.IntervalField()
    # time given to each player each turn before the main time is affected
    fixed_extra_time = pw_postgres.IntervalField()
    # amount timer is incremented after each turn
    time_increment_per_turn = pw_postgres.IntervalField()

    # timers at the start of the current turn, null means main_thinking_time
    host_time = pw_postgres.IntervalField(null=True)
    away_time = pw_postgres.IntervalField(null=True)

    host_offering_draw = pw.BooleanField(default=False)
    away_offering_draw = pw.BooleanField(default=False)
    other_valid_draw_claim = EnumField(enums.Conclusion, null=True)

    winner = EnumField(enums.Winner, default=enums.Winner.GAME_NOT_COMPLETE)
    conclusion_type = EnumField(
        enums.Conclusion, default=enums.Conclusion.GAME_NOT_COMPLETE
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
        self.timer = timing.Timer(self)

    def start_game(self, away: User):
        """Start a game."""
        self.invited = None
        self.away = away
        self.started_at = self.last_turn = datetime.datetime.now()
        self.host_time = self.main_thinking_time
        self.away_time = self.main_thinking_time
        self.save()

    @functools.cached_property
    def game_mode(self) -> gamemodes.GameMode:
        """Get a game mode instance for this game.

        This is implemented as a cached property rather than set on
        initialisation as Peewee seems to set some properties after
        initialisation in some cases.
        """
        return gamemodes.GAMEMODES[self.mode](self)

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
            'host_time': (
                self.host_time or self.main_thinking_time
            ).total_seconds(),
            'away_time': (
                self.away_time or self.main_thinking_time
            ).total_seconds(),
            'host_offering_draw': self.host_offering_draw,
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


class Notification(database.BaseModel):
    """Represents a notification to be delivered to the user."""

    _notification_type_file = (
        pathlib.Path(__file__).parent.absolute()
        / 'res' / 'notifications.json'
    )
    with open(_notification_type_file) as f:
        NOTIFICATION_TYPES = json.load(f)

    user = pw.ForeignKeyField(model=User, backref='notifications')
    sent_at = pw.DateTimeField(default=datetime.datetime.now)
    type_code = pw.CharField()
    game = pw.ForeignKeyField(model=Game, null=True)
    read = pw.BooleanField(default=False)

    class KasupelMeta:
        """Set the "not found" error code."""

        not_found_error = 1401

    @classmethod
    def send(
            cls, user: User, type_code: str, game: Game = None):
        """Create a new notification."""
        if game and user.socket_id in (
                game.host_socket_id, game.away_socket_id):
            # They are already connected to this game, so need to send them a
            # notification.
            return
        notif = cls.create(user=user, type_code=type_code, game=game)
        if user.socket_id:
            events.notifications.send_notification(user.socket_id, notif)

    def display(self) -> str:
        """Get the notification as it should be displayed to the user."""
        fmt = self.NOTIFICATION_TYPES[self.type_code]
        details = {}
        if self.game:
            if self.user == self.game.host:
                details['opponent'] = self.game.away
            else:
                details['opponent'] = self.game.host
        return fmt.format(**details)

    def to_json(self) -> dict[str, typing.Any]:
        """Represent as a python dict."""
        return {
            'id': self.id,
            'sent_at': int(self.sent_at.timestamp()),
            'type_code': self.type_code,
            'game': self.game.to_json() if self.game else None,
            'message': self.display(),
            'read': self.read
        }


class Piece(database.BaseModel):
    """A model to represent a piece in a game."""

    piece_type = EnumField(enums.PieceType)
    rank = pw.SmallIntegerField()
    file = pw.SmallIntegerField()
    side = EnumField(enums.Side)
    has_moved = pw.BooleanField(default=False)
    first_move_last_turn = pw.BooleanField(default=False)    # For en passant
    game = pw.ForeignKeyField(model=Game, backref='pieces')


class GameState(database.BaseModel):
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


MODELS = [User, Session, Game, Piece, GameState, Notification]

database.db.create_tables(MODELS)
