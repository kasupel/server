# Types

The API uses standard JSON almost exclusively, however in the documentation types may be referred to that are not standard JSON types. However, these values will all be expressed as standard JSON types, as explained below.

## Native JSON types

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

### `optional` (some other type)

A value which may either be `null` or some other specified type.

## Objects

### User

A JSON object representing a user account. These may or may not include an `email` field, see the endpoint-specific documentation to check.

Fields:

- `id` (integer)
- `username` (string)
- `elo` (integer)
- `avatar_url` (currently `null`, until media is implemented)
- `created_at` (date)
- `email` (string, may not be included)

### Game

A JSON object representing a game. These may either have:

- *Referenced* users, where the `host`, `away` and `invited` fields are integers referring to user IDs (or `null`).
- *Included* users, where the `host`, `away` and `invited` fields are `User` objects (not including emails), or `null`.

See the endpoint-specific documentation to check which.

Fields:

- `id` (integer)
- `mode` (optional `Gamemode` enum)
- `host` (optional `User` object or integer)
- `away` (optional `User` object or integer)
- `invited` (optional `User` object or integer)
- `current_turn` (`Side` enum)
- `turn_number` (integer)
- `main_thinking_time` (timedelta)
- `fixed_extra_time` (timedelta)
- `time_increment_per_turn` (timedelta)
- `home_time` (timedelta, the time left on the home clock)
- `away_time` (timedelta, the time left on the away clock)
- `home_offering_draw` (boolean)
- `away_offering_draw` (boolean)
- `winner` (`Winner` enum)
- `conclusion_type` (`Conclusion` enum)
- `opened_at` (date)
- `started_at` (optional date)
- `last_turn` (optional date)
- `ended_at` (optional date)

### Move

An object representing a move in a game.

The contents of this object depends on the game mode.

Chess:

- `start_rank` (integer, 0-7)
- `start_file` (integer, 0-7)
- `end_rank` (integer, 0-7)
- `end_file` (integer, 0-7)
- `promotion` (optional `Piece` enum)

### Board

An object representing the visual state of a board.

The attribute names in a board object will be of the form `<rank>,<file>`. The values will be lists containing two elements: the first, a `Piece` enum, the second a `Side` enum.

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

## Enums

Enums are expressed as integers, which may be any of a set specified below, and each have a specific meaning.

### GameMode

A game mode.

Values:

- `1`: Standard FIDE chess

### Winner

The winner of a game.

Values:

- `1`: Game not complete
- `2`: Home
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

- `1`: Home
- `2`: Away

### DisconnectReason

A reason for being disconnected from a socket.

Values:

- `1`: Invite declined
- `2`: New connection to the same game by the same account
- `3`: Game over

## Other

## date

An integer representing the number of seconds since the epoch, midnight on January 1 1970.

## timedelta

An integer representing a number of seconds.
