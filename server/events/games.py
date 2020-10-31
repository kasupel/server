"""Socket event handlers and emitters."""
from __future__ import annotations

import datetime
import typing

import flask

from . import connections, helpers
from .. import enums, models, utils


def has_started(game: models.Game):
    """Inform all connected users that a game has started."""
    helpers.send_room('game_start', {}, str(game.id))


def assert_game_in_progress():
    """Assert that the game an event was sent for is in progress.

    Raises a request error if not.
    """
    game = flask.request.context.game
    if game.ended_at or not game.started_at:
        raise utils.RequestError(2311)


def get_game_state(game: models.Game) -> dict[str, typing.Any]:
    """Send the game state for an ongoing game."""
    pieces = models.Piece.select().where(models.Piece.game == game)
    board = {}
    for piece in pieces:
        board[f'{piece.rank},{piece.file}'] = (
            piece.piece_type.value, piece.side.value
        )
    last_turn = game.last_turn or game.started_at
    return {
        'board': board,
        'host_time': game.host_time.total_seconds(),
        'away_time': game.away_time.total_seconds(),
        'last_turn': last_turn.timestamp(),
        'current_turn': game.current_turn.value,
        'turn_number': int(game.turn_number)
    }


def get_allowed_moves(game: models.Game) -> dict[str, typing.Any]:
    """Get allowed moves for the user whose turn it is."""
    moves = list(game.game_mode.possible_moves(game.current_turn))
    if game.other_valid_draw_claim:
        draw = game.other_valid_draw_claim.value
    else:
        draw = None
    return {
        'moves': moves,
        'draw_claim': draw
    }


def end_game(
        game: models.Game, reason: enums.Conclusion,
        winner_on_move: typing.Optional[bool] = True):
    """Process the end of a game.

    Winner defaults to the player on move.
    """
    if reason in (
            enums.Conclusion.CHECKMATE, enums.Conclusion.TIME,
            enums.Conclusion.RESIGN):
        if winner_on_move ^ (game.current_turn == enums.Side.HOST):
            game.winner = enums.Winner.AWAY
        else:
            game.winner = enums.Winner.HOST
    else:
        game.winner = enums.Winner.DRAW
    game.host.elo, game.away.elo = utils.ratings.calculate(
        game.host.elo, game.away.elo, game.winner
    )
    game.conclusion_type = reason
    game.ended_at = datetime.datetime.now()
    game.save()
    game.host.save()
    game.away.save()
    helpers.send_game('game_end', {
        'game_state': get_game_state(game),
        'reason': reason.value
    })
    for socket in (game.host_socket_id, game.away_socket_id):
        if socket:
            connections.disconnect(
                socket, enums.DisconnectReason.GAME_OVER
            )


@helpers.event('game_state')
def game_state():
    """Send the client the entire game state.

    This only includes displayable information, use allowed_moves for working
    out what moves are allowed.
    """
    assert_game_in_progress()
    helpers.send_user(
        'game_state', get_game_state(flask.request.context.game)
    )


@helpers.event('allowed_moves')
def allowed_moves():
    """Send a list of allowed moves.

    Only allowed if it is your turn.
    """
    assert_game_in_progress()
    game = flask.request.context.game
    if flask.request.context.side != game.current_turn:
        raise utils.RequestError(2312)
    helpers.send_user('allowed_moves', get_allowed_moves(game))


@helpers.event('move')
def move(move_data: dict[str, typing.Any]):
    """Handle a move being made."""
    assert_game_in_progress()
    game = flask.request.context.game
    if datetime.datetime.now() >= game.timer.boundary:
        end_game(game, enums.Conclusion.TIME)
        return
    if flask.request.context.side != game.current_turn:
        raise utils.RequestError(2312)
    if not game.game_mode.make_move(**move_data):
        raise utils.RequestError(2313)
    game.turn_number += 1
    end = game.game_state.game_is_over()
    if end in (
            enums.Conclusion.THREEFOLD_REPETITION,
            enums.Conclusions.FIFTY_MOVE_RULE):
        game.other_valid_draw_claim = end
    else:
        game.other_valid_draw_claim = None
    game.save()
    if end == enums.Conclusion.STALEMATE:
        helpers.send_opponent_notification('games.draw.stalemate')
        end_game(game, end)
    elif end == enums.Conclusion.CHECKMATE:
        helpers.send_opponent_notification('games.draw.checkmate')
        end_game(game, end)
    else:
        helpers.send_opponent('move', {
            'move': move_data,
            'game_state': get_game_state(game),
            'allowed_moves': get_allowed_moves(game)
        })


@helpers.event('offer_draw')
def offer_draw():
    """Handle a user offering a draw."""
    assert_game_in_progress()
    if flask.request.context.side == enums.Side.HOST:
        flask.request.context.game.host_offering_draw = True
    else:
        flask.request.context.game.away_offering_draw = True
    flask.request.context.game.save()
    helpers.send_opponent('draw_offer', {})
    helpers.send_opponent_notification('games.ongoing.draw_offer')


@helpers.event('claim_draw')
def claim_draw(reason: enums.Conclusion):
    """Handle a user claiming a draw."""
    ctx = flask.request.context
    if reason == enums.Conclusion.AGREED_DRAW:
        if (ctx.side == enums.Side.HOST) and not ctx.game.away_offering_draw:
            raise utils.RequestError(2322)
        if (ctx.side == enums.Side.AWAY) and not ctx.game.host_offering_draw:
            raise utils.RequestError(2322)
        helpers.send_opponent_notification('games.draw.agreed')
    elif reason == enums.Conclusion.THREEFOLD_REPETITION:
        if reason != ctx.game.other_valid_draw_claim:
            raise utils.RequestError(2322)
        helpers.send_opponent_notification('games.draw.threefold_repetition')
    elif reason == enums.Conclusion.FIFTY_MOVE_RULE:
        if reason != ctx.game.other_valid_draw_claim:
            raise utils.RequestError(2322)
        helpers.send_opponent_notification('games.draw.fifty_move_rule')
    else:
        raise utils.RequestError(2321)
    end_game(ctx.game, reason)


@helpers.event('timeout')
def timeout():
    """Handle a claim that the player on move has timed out."""
    assert_game_in_progress()
    if datetime.datetime.now() < flask.request.context.game.timer.boundary:
        raise utils.RequestError(2314)
    if flask.request.context.side == flask.request.context.game.current_turn:
        helpers.send_opponent_notification('games.win.time')
    else:
        helpers.send_opponent_notification('games.loss.time')
    end_game(
        flask.request.context.game, enums.Conclusion.TIME,
        winner_on_move=False
    )


@helpers.event('resign')
def resign():
    """Handle a user resigning from the game."""
    assert_game_in_progress()
    end_game(
        flask.request.context.game, enums.Conclusion.RESIGN,
        winner_on_move=False
    )
    helpers.send_opponent_notification('games.win.resign')
