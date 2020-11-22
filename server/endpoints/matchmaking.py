"""Respond to and send socket API calls related to matchmaking."""
import datetime

import peewee

from . import helpers
from .. import enums, events, models, utils


@helpers.endpoint('/games/find', method='POST', require_verified_email=True)
def find_game(
        user: models.User,
        main_thinking_time: datetime.timedelta,
        fixed_extra_time: datetime.timedelta,
        time_increment_per_turn: datetime.timedelta,
        mode: enums.Mode) -> dict[str, int]:
    """Find a game matching parameters, or create one if not found."""
    try:
        game = models.Game.get(
            models.Game.host != user,
            models.Game.started_at == None,    # noqa: E7111
            models.Game.main_thinking_time == main_thinking_time,
            models.Game.fixed_extra_time == fixed_extra_time,
            models.Game.time_increment_per_turn == time_increment_per_turn,
            models.Game.mode == mode
        )
    except peewee.DoesNotExist:
        game = models.Game.create(
            host=user, mode=mode, main_thinking_time=main_thinking_time,
            fixed_extra_time=fixed_extra_time,
            time_increment_per_turn=time_increment_per_turn
        )
    else:
        game.start_game(user)
        models.Notification.send(game.host, 'matchmaking.match_found', game)
        events.games.has_started(game)
    return {
        'game_id': game.id
    }


@helpers.endpoint(
    '/games/send_invitation', method='POST', require_verified_email=True
)
def send_invitation(
        user: models.User,
        invitee: models.User,
        main_thinking_time: datetime.timedelta,
        fixed_extra_time: datetime.timedelta,
        time_increment_per_turn: datetime.timedelta,
        mode: enums.Mode) -> dict[str, int]:
    """Create a game which only a specific person may join."""
    if user == invitee:
        raise utils.RequestError(2121)
    game = models.Game.create(
        host=user, invited=invitee, mode=mode,
        main_thinking_time=main_thinking_time,
        fixed_extra_time=fixed_extra_time,
        time_increment_per_turn=time_increment_per_turn
    )
    models.Notification.send(invitee, 'matchmaking.invite_received', game)
    return {
        'game_id': game.id
    }


@helpers.endpoint(
    '/games/invites/<game>', method='POST', require_verified_email=True
)
def accept_invitation(user: models.User, game: models.Game):
    """Accept a game you have been invited to."""
    if game.invited != user:
        raise utils.RequestError(2111)
    game.start_game(user)
    models.Notification.send(game.host, 'matchmaking.invite_accepted', game)
    events.games.has_started(game)


@helpers.endpoint('/games/invites/<game>', method='DELETE')
def decline_invitation(user: models.User, game: models.Game):
    """Decline a game you have been invited to."""
    if game.invited != user:
        raise utils.RequestError(2111)
    if game.host_socket_id:
        events.connections.disconnect(
            game.host_socket_id,
            reason=enums.DisconnectReason.INVITE_DECLINED
        )
    models.Notification.send(game.host, 'matchmaking.invite_declined', game)
    game.delete_instance()
