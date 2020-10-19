# Authorisation

In order to avoid requiring the username and password to be sent with every request (and therefore requiring these to be stored client-side), the authorisation system uses sessions. These last for 30 days (though this may change), and only require the username and password to be used once, at the start of each session.

## Starting a session

A session is started using the [`/accounts/login`](./endpoints.md#e-post-accountslogin). This accepts `username` and `password` parameters (which will be validated), and a `token` parameter. The token should be [string](./types.md#string) of 32 bytes, encoded in base64. These should be generated unpredictably, as they will form a password of sorts for the duration of the session. This endpoint will return a session ID. This is like the username for the session.

## Authorising requests

Requests can be authorised by passing `session_token` and `session_id` parameters to them. If these match an existing session, authorisation will be successful. `session_token` should be base 64 encoded.

## Ending a session

Sessions will automatically expire after 30 days (exact time may change), but you can also delete a session with the authorised [`/accounts/logout`](./endpoints.md#a-get-accountslogout) endpoint.

## Connecting to a socket

When connecting to a socket ([sockets](./sockets.md)), you should include an `Authorization` header. This should look like:

```text
Authorization: SessionKey <session_id>|<session_token>
```

For example:

```text
Authorization: SessionKey 1234|sw72sZiTWhQ+vPWmHYgTzuqo1NCoz7/W/0Y3S39Pc7c=
```

Note that the session token should be base 64 encoded.
