# Types

The API uses standard JSON almost exclusively, however in the documentation types may be referred to that are not standard JSON types. However, these values will all be expressed as standard JSON types, as explained below.

## Native JSON types

### `object`

Refers to the JSON dict type, usually with reference to the type of data included.

### `string`

Refers to the JSON string type.

### `integer`

Refers to the JSON integer type.

### `list` (of some other type)

Refers to the JSON list type, usually with reference to the type of data included in that list.

### `null`

Refers to the JSON singleton `null`.

### `boolean`

Refers to the JSON boolean type, either `true` or `false`.

## Objects

### User

A JSON object representing a user account. These may or may not include an `email` field, see the endpoint-specific documentation to check.

Fields:

- `id` ([integer](#integer))
- `username` ([string](#string))
- `elo` ([integer](#integer))
- `avatar_url` ([optional](#optional-some-other-type) [string](#string))
- `created_at` ([date](#date))
- `email` ([string](#string), may not be included)

The avatar URL will be relative to the top level of the API (for example, if you got a user object from `https://example.com/api/v1/accounts/account` and the `avatar_url` was `/media/avatar/813-3.png`, the full URL would be `https://example.com/api/v1/media/avatar/813-3.png`).

### Game

A JSON object representing a game. These may either have:

- *Referenced* users, where the `host`, `away` and `invited` fields are [integers](#integer) referring to user IDs (or [`null`](#null)).
- *Included* users, where the `host`, `away` and `invited` fields are [`User` objects](#user) (not including emails), or [`null`](#null).

See the endpoint-specific documentation to check which.

Fields:

- `id` ([integer](#integer))
- `mode` ([optional](#optional-some-other-type) [`Gamemode` enum](#gamemode))
- `host` ([optional](#optional-some-other-type) [`User` object](#user) or [integer](#integer))
- `away` ([optional](#optional-some-other-type) [`User` object](#user) or [integer](#integer))
- `invited` ([optional](#optional-some-other-type) [`User` object](#user) or [integer](#integer))
- `current_turn` ([`Side` enum](#side))
- `turn_number` ([integer](#integer))
- `main_thinking_time` ([timedelta](#timedelta))
- `fixed_extra_time` ([timedelta](#timedelta))
- `time_increment_per_turn` ([timedelta](#timedelta))
- `host_time` ([timedelta](#timedelta), the time left on the home clock)
- `away_time` ([timedelta](#timedelta), the time left on the away clock)
- `host_offering_draw` ([boolean](#boolean))
- `away_offering_draw` ([boolean](#boolean))
- `winner` ([`Winner` enum](#winner))
- `conclusion_type` ([`Conclusion` enum](#conclusion))
- `opened_at` ([date](#date))
- `started_at` ([optional](#optional-some-other-type) [date](#date))
- `last_turn` ([optional](#optional-some-other-type) [date](#date))
- `ended_at` ([optional](#optional-some-other-type) [date](#date))

### Move

An object representing a move in a game.

The contents of this object depends on the game mode.

Chess:

- `start_rank` ([integer](#integer), 0-7)
- `start_file` ([integer](#integer), 0-7)
- `end_rank` ([integer](#integer), 0-7)
- `end_file` ([integer](#integer), 0-7)
- `promotion` ([optional](#optional-some-other-type) [`Piece` enum](#piece))

### Board

An object representing the visual state of a board.

The attribute names in a board object will be of the form `<rank>,<file>`. The values will be [lists](#list-of-some-other-type) containing two elements: the first, a [`Piece` enum](#piece), the second a [`Side` enum](#side).

Example:

```json
{
    "0,0": [2, 1],
    "0,1": [3, 1],
    "0,2": [4, 1],
    "1,0": [1, 1],
    "1,1": [1, 1],
    "1,2": [1, 1],
    ...
}
```

Squares with no piece on them will not be included.

### Notification

An object representing a notification to be displayed to the user.

Fields:

- `id` ([integer](#integer))
- `sent_at` ([date](#date))
- `type_code` ([string](#string))
- `game` ([optional](#optional-some-other-type) [Game object](#game))
- `message` ([string](#string))
- `read` ([boolean](#boolean))

Note that the `message` is just an example (English) message that could be displayed to the user. Implementations are encouraged to provide their own messages, which may be localised.

## Enums

Enums are expressed as [integers](#integer), which may be any of a set specified below, and each have a specific meaning.

### GameMode

A game mode.

Values:

- `1`: Standard FIDE chess

### Winner

The winner of a game.

Values:

- `1`: Game not complete
- `2`: Host
- `3`: Away
- `4`: Draw

### Conclusion

The way a game ended.

Values:

- `1`: Game not complete
- `2`: Checkmate
- `3`: Resignation
- `4`: Out of time
- `5`: Stalemate
- `6`: Threefold repetition
- `7`: 50 move rule
- `8`: Agreed draw

### Piece

The type of a piece on the board.

Values:

- `1`: A pawn
- `2`: A rook
- `3`: A knight
- `4`: A bishop
- `5`: A queen
- `6`: A king

### Side

One of the sides of a game.

Values:

- `1`: Host
- `2`: Away

### DisconnectReason

A reason for being disconnected from a socket.

Values:

- `1`: Invite declined
- `2`: New connection to the same game by the same account
- `3`: Game over

## Other

## date

An [integer](#integer) representing the number of seconds since the epoch, midnight on January 1 1970.

## timedelta

An [integer](#integer) representing a number of seconds.

## bytes

A base 64 encoded [string](#string) representing some bytes.

### optional (some other type)

A value which may either be [`null`](#null) or some other specified type.
