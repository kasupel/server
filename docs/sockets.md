# Sockets

[The Socket.IO protocol](https://socket.io/docs) is used for sockets, which is a layer over WebSockets, and also supports long polling if required. A single socket is associated with a specific game.

Note that though there is some overlap between client initiated events and server initiated events, the data included is generally different.

Types used below are as documented in [types](./types.md).

## Connecting

Connecting is done under the default namespace. As well as the `Authorization` header documented in [authorisation](./authorisation.md), the `Game-ID` header must be sent. This is the ID of the game to connect to. It must be a game that you are a part of that has not finished.

## Client initiated events

### `game_state`

Request that the server send the current state of the game. The server should respond with a `game_state` event. This is only allowed if the game has started.

### `allowed_moves`

Request that the server send a list of moves you are allowed to make. The server should repsond with an `allowed_moves` event. This is only allowed if the game has started and it is your turn.

### `move`

Make a move in the game. Data should be a `Move` object.

### `offer_draw`

Offer your opponent a draw.

### `claim_draw`

Claim a draw that has been offered or is otherwise valid.

Fields:

- `reason` (`Conclusion` enum, the grounds on which you are claiming a draw)

Note that only the "Agreed draw", "threefold repetition" and "50 move rule" claims are valid.

### `resign`

Resign from the game.

## Server initiated events

### `game_disconnect`

A warning that you are about to be disconnected.

Fields:

- `reason` (`DisconnectReason` enum)

### `game_start`

The game has started.

### `game_end`

The game has ended.

Fields:

- `game_state` (as in the server initiated `game_state` event)
- `reason` (`Conclusion` enum)

### `draw_offer`

Your opponent has offered a draw.

### `move`

Your opponent has made a move, and it is now your turn.

Fields:

- `move` (as in the client initiated `move` event)
- `game_state` (as in the server initiated `game_state` event)
- `allowed_moves` (as in the server initiated `allowed_moves` event)

### `game_state`

An event containing the current state of the game. This is sent on connect (if the game has started), as well as when requested.

Fields:

- `board` (a `Board` object)
- `home_time` (timedelta, time remaining on home's clock at `last_turn`)
- `away_time` (timedelta, time remaining on away's clock at `last_turn`)
- `last_turn` (date, the time the last turn was taken)
- `current_turn` (`Side` enum)
- `turn_number` (integer)

### `allowed_moves`

Fields:

- `moves` (a list of `Move` objects)
- `draw_claim` (optional `Conclusion` enum)

Note `draw_claim` will only be "Agreed draw", "threefold repetition" or "50 move rule" (or `null`).
