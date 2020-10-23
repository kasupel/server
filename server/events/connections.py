"""Handle connect and disconnect events."""
import flask

import flask_socketio as sockets

from . import games, helpers
from .. import enums, models
from ..endpoints import helpers as endpoint_helpers


def disconnect(socket_id: str, reason: enums.DisconnectReason):
    """Disconnect a user from a socket."""
    helpers.send_room('game_disconnect', {'reason': reason.value}, socket_id)
    sockets.disconnect(socket_id)


def parse_connect_headers() -> tuple[models.Session, models.Game]:
    """Parse the Authorization and Game-ID headers used when connecting."""
    # Parse the authorisation header.
    authorisation = flask.request.headers.get('Authorization')
    if not authorisation:
        raise helpers.RequestError(3411)
    try:
        auth_typ, auth_key = authorisation.split()
    except ValueError:
        raise helpers.RequestError(3412)
    if auth_typ.lower() != 'SessionKey':
        raise helpers.RequestError(3412)
    # The header is in <auth_type> <auth> format.
    try:
        session_id, session_token = auth_key.split('|')
    except ValueError:
        raise helpers.RequestError(3413)
    session = endpoint_helpers.validate_session_key(session_id, session_token)
    # Parse the game ID header.
    game_id = flask.request.headers.get('Game-ID')
    if not game_id:
        raise helpers.RequestError(3421)
    game = models.Game.converter(game_id)
    return session, game


@helpers.event('connect')
def connect():
    """Process a user connecting to a socket."""
    session, game = parse_connect_headers()
    # We have the game and session that is being used.
    if session.user not in (game.host, game.away):
        raise helpers.RequestError(2201)
    if game.ended_at:
        raise helpers.RequestError(2202)
    if game.host == session.user:
        old_socket = game.host_socket_id
        game.host_socket_id = flask.request.sid
    else:
        old_socket = game.away_socket_id
        game.away_socket_id = flask.request.sid
    if old_socket:
        # There is an existing connection for the same user.
        disconnect(old_socket, enums.DisconnectReason.NEW_CONNECTION)
    sockets.join_room(str(game.id))
    if game.started_at:
        helpers.send_user('game_state', games.get_game_state(game))
    is_currently_turn = (
        (game.host == session.user and game.current_turn == enums.Side.HOST)
        or (
            game.away == session.user
            and game.current_turn == enums.Side.AWAY
        )
    ) and game.started_at
    if is_currently_turn:
        helpers.send_user('allowed_moves', games.get_allowed_moves(game))
