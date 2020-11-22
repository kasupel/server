"""Random utilities for the server."""
import json
import pathlib
import re
import typing

import peewee

from . import converters    # noqa: F401


errors_file = (
    pathlib.Path(__file__).parent.parent.absolute() / 'res' / 'errors.json'
)

with open(errors_file) as f:
    ERROR_CODES = json.load(f)


class RequestError(Exception):
    """A class for errors caused by a bad request."""

    def __init__(self, code: int):
        """Store the code and message to be handled."""
        self.code = code
        self.message = ERROR_CODES[str(code)]
        self.as_dict = {
            'error': code,
            'message': self.message
        }
        super().__init__(self.message)


def interpret_integrity_error(
        error: peewee.IntegrityError) -> tuple[str, str]:
    """Dissect an integrity error to see what went wrong.

    It seems like a bad way to do it but according to Peewee's author it's
    the only way: https://stackoverflow.com/a/53597548.
    """
    match = re.search(
        r'DETAIL:  Key \(([a-z_]+)\)=\((.+)\) already exists\.', str(error)
    )
    if match:
        return 'duplicate', match.group(1)
    else:
        raise ValueError('Unknown integrity error.') from error


def is_wrong_arguments(error: TypeError, fun: typing.Callable) -> bool:
    """Check if a type error is due to incorrect arguments.

    Only checks for keyword arguments for a specific function.
    """
    err = str(error).removeprefix(fun.__name__)
    return bool(re.match(
        r'\(\) (got an unexpected keyword|missing [0-9]+ required '
        r'(positional|keyword-only)) arguments?',
        err
    ))
