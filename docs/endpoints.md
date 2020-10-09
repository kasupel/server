# Endpoints

## Authorisation

Some endpoints require credentials, in the form of a session ID and session token (see [authorisation](./authorisation.md)). These should be passed through the `session_id` and `session_token` parameters. They are required on endpoints marked with `[A]` below, but will be accepted on any endpoints.

## Encryption

Some endpoints require that the payload be encrypted. These endpoints will all use methods with bodies (here, just `POST` and `PATCH`). The server's public key is available at `/rsa_key`. Encryption should be done using the RSA algorithm with OAEP padding (MGF1 mask generation and SHA256 hashing). Encryption is required for endpoints marked with `[E]` below, and will not be understood on any other endpoints.

## Pagination

Some endpoints return potentially long lists of objects. These endpoints accept an optional `page` parameter, which indicates which page of results to fetch (0 indexed, defaults to `0`). Successful responses from these endpoints will include a `pages` field, indicating how many pages of results are available. Pages will include up to `100` results, though this may change. Pagination is used for endpoints marked with `[P]` below.

## Email Verification

Some endpoints require that the logged in user's email be verified. These are marked with `[V]` below.

## Parameters

For body-less endpoints (here, just `GET` and `DELETE`), parameters should be sent as URL parameters, or in some cases as documented, as part of the URL path. Other endpoints (here, `POST` and `PATCH`), parameters should be sent as JSON in the body (or encrypted JSON, as described above).See [types](./types.md) for an explanation of the types, though mostly they are native JSON types.

## Responses

Responses will all be in JSON (with the exception of `/rsa_key`, not documented below). Return value names below refer to JSON fields. See [types](./types.md) for an explanation of the return value types.

## Endpoints

### `[E] POST /accounts/login`

Starts an authenticated session, see [authorisation](./authorisation.md) for more details.

Parameters:

- `username` (string)
- `password` (string)
- `token` (bytes)

The `token` should be a base64 encoded string of 32 bytes.

Returns:

- `session_id` (integer)

### `[A] GET /accounts/logout`

Ends the current authenticated session.

### `[E] POST /accounts/create`

Creates a new account.

Parameters:

- `username` (string, between 1 and 32 characters)
- `password` (string, between 10 and 32 characters, more than 6 unique characters, not in the [haveibeenpwned](https://haveibeenpwned.com) database)
- `email` (string)

### `[A] GET /accounts/resend_verification_email`

Resends a verification email to the logged in user.

### `GET /accounts/verify_email`

Verifies the email account associated with the logged in user. `token` is a 6 character token that has been emailed to the user.

Parameters:

- `username` (string)
- `token` (string)

### `[A][E] PATCH /accounts/me`

Updates the logged in user's account.

Parameters:

- `password` (optional string, see `/accounts/create` for security requirements)
- `avatar` (optional bytes)
- `email` (optional string)

### `[A] DELETE /accounts/me`

Deletes the logged in user's account.

### `[A] GET /accounts/me`

Get the current users account details.

Returns a `User` object, including email.

### `GET /accounts/account`

Get a user by ID.

Parameters:

- `id` (integer)

### `GET /users/<username>`

Get a user by username.

Parameters:

- `username` (string, in the URL path)

### `[P] GET /accounts/accounts`

Get a list of all users, sorted by descending ELO.

Returns:

- `users` (list of `User` objects, without emails)

### `[A][P] GET /games/invites`

Get a list of games the logged in user has been invited too.

Returns:

- `games` (list of `Game` objects, referencing users by ID)
- `users` (list of `User` objects referenced by the games)

### `[A][P] GET /games/searches`

Get a list of games where the logged in user is looking for an opponent. This includes invites they have sent and game searches they have initiated.

Returns:

- `games` (list of `Game` objects, referencing users by ID)
- `users` (list of `User` objects referenced by the games)

### `[A][P] GET /games/ongoing`

Get a list of games that are currently ongoing and include the logged in user.

Returns:

- `games` (list of `Game` objects, referencing users by ID)
- `users` (list of `User` objects referenced by the games)

### `[P] GET /games/completed`

Get a list of games that the specified user took part in that have now ended.

Parameters:

- `account` (string, a username)

Returns:

- `games` (list of `Game` objects, referencing users by ID)
- `users` (list of `User` objects referenced by the games)

### `[A][P] GET /games/common_completed`

Get a list of games that the specified user and the logged in user took part in that have now ended.

Parameters:

- `account` (string, a username)

Returns:

- `games` (list of `Game` objects, referencing users by ID)
- `users` (list of `User` objects referenced by the games)

### `GET /games/<game>`

Get a game by ID.

Parameters:

- `game` (integer, in the URL path)

Returns a `Game` object, with users included.

### `[A][V] POST /games/find`

Create or join an unstarted game.

Parameters:

- `main_thinking_time` (timedelta)
- `fixed_extra_time` (timedelta)
- `time_increment_per_turn` (timedelta)
- `mode` (`GameMode` enum)

Returns:

- `game_id` (integer, the ID of the found or joined game)

### `[A][V] POST /games/send_invitation`

Send an invitation to another user.

Parameters:

- `invitee` (string, the target user's username)
- `main_thinking_time` (timedelta)
- `fixed_extra_time` (timedelta)
- `time_increment_per_turn` (timedelta)
- `mode` (`GameMode` enum)

Returns:

- `game_id` (integer, the ID of the found or created game)

### `[A][V] POST /games/invites/<game>`

Accept an invitation you have been sent.

Parameters:

- `game` (integer, in the URL path)

### `[A] DELETE /games/invites/<game>`

Decline an invitation you have been sent.

Parameters:

- `game` (integer, in the URL path)
