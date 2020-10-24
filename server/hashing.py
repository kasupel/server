"""Utilities for hashing passwords."""
import hashlib
import hmac
import os


def hash_password(password: str) -> str:
    """Hash a password."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100_000)
    return salt + key


def check_password(password: str, hashed: str) -> bool:
    """Check a password against a hash."""
    salt = hashed[:32]
    key = hashed[32:]
    attempt_key = hashlib.pbkdf2_hmac(
        'sha256', password.encode(), salt, 100_000
    )
    return hmac.compare_digest(key, attempt_key)


class HashedPassword:
    """A class to check for equality against hashed passwords."""

    def __init__(self, hashed_password: str):
        """Store the hashed password."""
        self.hashed_password = hashed_password

    def __eq__(self, password: str) -> bool:
        """Check for equality against an unhashed password."""
        return check_password(password, self.hashed_password)
