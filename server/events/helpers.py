"""Helpers for all events, and setting up the server."""
from __future__ import annotations

import functools
import json
import typing

import flask

import flask_socketio as sockets

from .. import enums, events, models, utils


class EventContext:
    """Information to be stored during handling of an event."""

    def __init__(self):
        """Store the initial data."""
        sid = flask.request.sid
        game = models.Game.get_or_none(models.Game.host_socket_id == sid)
        if game:
            side = enums.Side.HOST
            user = game.host
            opponent = game.away
        else:
            game = models.Game.get_or_none(
                models.Game.away_socket_id == sid
            )
            if not game:
                raise utils.RequestError(4101)
            side = enums.Side.AWAY
            user = game.away
            opponent = game.host
        self.game = game
        self.side = side
        self.user = user
        self.opponent = opponent


def send_room(name: str, data: dict[str, typing.Any], room: str):
    """Send an event to a specified room.

    Doesn't do much wrapping of socketio.emit, mainly exists in case we want
    to add more wrapping later.
    """
    events.socketio.emit(name, data, room=room)


def send_user(name: str, data: dict[str, typing.Any]):
    """Send an event to the currently connected user."""
    send_room(name, data, flask.request.sid)


def send_game(
        name: str, data: dict[str, typing.Any], game: models.Game = None):
    """Send an event to both members of a game.

    Defaults to the currently connected game.
    """
    game = game or flask.request.context.game
    send_room(name, data, str(game.id))


def send_opponent(name: str, data: dict[str, typing.Any]):
    """Send an event to the opponent of the currently connected user."""
    if flask.request.context.side == enums.Side.HOST:
        socket = flask.request.context.game.away_socket_id
    else:
        socket = flask.request.context.game.host_socket_id
    send_room(name, data, socket)


def send_opponent_notification(notification_code: str):
    """Send a notification to the opponent in the current game."""
    models.Notification.send(
        flask.request.context.opponent, notification_code
    )


def event(name: str) -> typing.Callable:
    """Create a wrapper for a socket.io event listener."""

    def wrapper(main: typing.Callable) -> typing.Callable:
        """Wrap an endpoint."""
        converter_wrapped = utils.converters.wrap(main)

        @functools.wraps(main)
        def return_wrapped(
                **kwargs: dict[str, typing.Any]) -> typing.Any:
            """Handle errors and convert the response to JSON."""
            try:
                flask.request.context = EventContext()
                converter_wrapped(**kwargs)
            except utils.RequestError as error:
                if name == 'connect':
                    # Don't accept connection if there is an error on connect.
                    raise sockets.ConnectionRefusedError(
                        json.dumps(error.as_dict)
                    )
                else:
                    events.socketio.emit(
                        'bad_request', error.as_dict, room=flask.request.sid
                    )

        flask_wrapped = events.socketio.on(name)(return_wrapped)
        return flask_wrapped

    return wrapper
