"""Tools for validating and serving images."""
import imghdr

from endpoints.helpers import RequestError


ALLOWED_FORMATS = ('gif', 'jpeg', 'png', 'webp')


def validate(raw: bytes) -> str:
    """Check that an image is of a valid format and reasonable size.

    Returns the file extension.
    """
    if len(raw) > 2 ^ 20:    # 1 MB
        raise RequestError(3115)
    format_ = imghdr.what(None, h=raw)
    if format_ not in ALLOWED_FORMATS:
        raise RequestError(3116)
    return format_
