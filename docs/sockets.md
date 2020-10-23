# Sockets

[The Socket.IO protocol](https://socket.io/docs) is used for sockets, which is a layer over WebSockets, and also supports long polling if required. A single socket is associated with a specific game.

Note that though there is some overlap between client initiated events and server initiated events, the data included is generally different.

Types used below are as documented in [types](./types.md).

## Connecting

Connecting is done under the default namespace. As well as [the `Authorization` header](./authorisation.md#connecting-to-a-socket), the `Game-ID` header must be sent. This is the ID of the game to connect to. It must be a game that you are a part of that has not finished.

## Client initiated events

### `game_state` (client)

Request that the server send the current state of the game. The server should respond with a `game_state` event. This is only allowed if the game has started.

### `allowed_moves` (client)

Request that the server send a list of moves you are allowed to make. The server should respond with an `allowed_moves` event. This is only allowed if the game has started and it is your turn.

### `move` (client)

Make a move in the game. Data should be a [`Move` object](./types.md#move).

### `offer_draw`

Offer your opponent a draw.

### `claim_draw`

Claim a draw that has been offered or is otherwise valid.

Fields:

- `reason` ([`Conclusion` enum](./types.md#conclusion), the grounds on which you are claiming a draw)

Note that only the "Agreed draw", "threefold repetition" and "50 move rule" claims are valid.

### `resign`

Resign from the game.

### `timeout`

Assert that the player whose turn it currently is has timed out. If they have, the player whose turn it is not will on time. This will be periodically checked, and late moves will not be accepted, but clients should send this event when relevant regardless.

## Server initiated events

### `game_disconnect`

A warning that you are about to be disconnected.

Fields:

- `reason` ([`DisconnectReason` enum](./types.md#disconnectreason))

### `game_start`

The game has started.

### `game_end`

The game has ended.

Fields:

- `game_state` (as in the server initiated `game_state` event)
- `reason` ([`Conclusion` enum](./types.md#conclusion))

### `draw_offer`

Your opponent has offered a draw.

### `move` (server)

Your opponent has made a move, and it is now your turn.

Fields:

- `move` (as in the client initiated `move` event)
- `game_state` (as in the server initiated `game_state` event)
- `allowed_moves` (as in the server initiated `allowed_moves` event)

### `game_state` (server)

An event containing the current state of the game. This is sent on connect (if the game has started), as well as when requested.

Fields:

- `board` (a [`Board` object](./types.md#board))
- `host_time` ([timedelta](./types.md#timedelta), time remaining on home's clock at `last_turn`)
- `away_time` ([timedelta](./types.md#timedelta), time remaining on away's clock at `last_turn`)
- `last_turn` ([date](./types.md#date), the time the last turn was taken)
- `current_turn` ([`Side` enum](./types.md#side))
- `turn_number` ([integer](./types.md#integer))

### `allowed_moves` (server)

Fields:

- `moves` (a [list](./types.md#list-of-some-other-type) of [`Move` objects](./types.md#move))
- `draw_claim` ([optional](./types.md#optional-some-other-type) [`Conclusion` enum](./types.md#conclusion))

Note `draw_claim` will only be "Agreed draw", "threefold repetition" or "50 move rule" (or [`null`](./types.md#null)).

### `notification`

Fields are the same as [a `Notification` object](./types.md#notification).

Indicates that the user has received a new notification.
