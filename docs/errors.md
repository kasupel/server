# Errors

Below is a list of error codes and their human readable explanations. Note that error codes ending in a `0` only indicate subgroups, and will not themselves be used.

## 1000 - Accounts error

- 1001 - Account not found.

### 1100 - Invalid account details

1110 - Invalid username

- 1111 - Username too long - may not be more than 32 characters.
- 1112 - Username empty.
- 1113 - Username already taken.

1120 - Invalid password

- 1121 - Password too short - must be at least 10 characters.
- 1122 - Password too long - may not be more than 32 characters.
- 1123 - Password too repetitive - must include at least 6 unique characters.
- 1124 - Password too common.

1130 - Invalid email address

- 1131 - Email address too long - may not be more than 255 characters.
- 1132 - Invalid email address - make sure you have typed it correctly.
- 1133 - Email address already used.

### 1200 - Email verification error

- 1201 - Email already verified.
- 1202 - Username or verification token not found.

### 1300 - Authentication failed

- 1301 - No credentials used.
- 1302 - Incorrect password.
- 1303 - Session ID AND request token must be passed.
- 1304 - Session ID not found.
- 1305 - Incorrect session token.
- 1306 - Session has expired.
- 1307 - Email address not verified.
- 1308 - Session token must be 32 bytes long
- 1309 - Invalid session ID.

### 1400 - Notifications error

- 1401 - Notification not found.

## 2000 - Games error

- 2001 - Game not found.

### 2100 - Invitations error

2110 - Accepting invitation failed

- 2111 - You were not invited to this game.

2120 - Sending invitation failed

- 2121 - You cannot invite yourself to a game.

### 2200 - Can't connect to game

- 2201 - Not a member of game.
- 2202 - Game has ended.

### 2300 - Bad game event received

2310 - Game event not allowed

- 2311 - This may only be done on games that are in progress.
- 2312 - You may not do this when it is not your turn.
- 2313 - Invalid move.
- 2314 - The current player has not run out of time.

2320 - Disallowed reason to claim a draw

- 2321 - Not a reason to claim a draw.
- 2322 - Draw reason is not available.

## 3000 - Malformed request

### 3100 - Parameter error

- 3101 - Value required.
- 3102 - Incorrect parameters passed.
- 3103 - Bad encrypted data.

3110 - Invalid data syntax

- 3111 - Invalid integer syntax.
- 3112 - Invalid base 64 string.
- 3113 - Invalid JSON object.
- 3114 - Unknown value for enum.
- 3115 - Image must be gif, jpeg, png or webp.
- 3116 - Image must be less than 1 MB.
- 3117 - Positive value required.

### 3200 - Pagination error

- 3201 - Page does not exist.

### 3300 - URL error

- 3301 - Unknown URL.

### 3400 - Socket connection error

3410 - Bad authorisation header

- 3411 - Empty or missing authorisation header.
- 3412 - Missing or incorrect authorisation type.
- 3413 - Badly formatted session key.

3420 - Bad game ID header

- 3421 - Empty or missing game ID header.

## 4000 - Internal error

- 4001 - Unknown internal error

### 4100 - Internal socket error

- 4101 - Socket session ID not known.

## 5000 - Media error

- 5001 - Resource not found.
