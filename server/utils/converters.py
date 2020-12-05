"""Detect and convert the parameters passed to endpoints."""
import base64
import datetime
import enum
import functools
import inspect
import types
import typing

import peewee

from .. import utils


def int_converter(value: typing.Union[str, int]) -> int:
    """Convert an integer parameter."""
    try:
        return int(value)
    except (ValueError, TypeError):
        raise utils.RequestError(3111)


def _bytes_converter(value: typing.Union[str, bytes]) -> bytes:
    """Convert a bytes parameter that may have been passed as base64."""
    if isinstance(value, bytes):
        return value
    try:
        return base64.b64decode(str(value))
    except ValueError:
        raise utils.RequestError(3112)


def _dict_converter(
        value: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """Convert a dict (JSON) parameter.

    Does no actual conversion, only validation.
    """
    if not isinstance(value, dict):
        raise utils.RequestError(3113)
    return value


def _timedelta_converter(value: typing.Union[str, int]) -> datetime.timedelta:
    """Convert a time delta parameter.

    This should be passed as an integer representing seconds.
    """
    value = int_converter(value)
    if value < 0:
        # Negative timedeltas are valid but we don't have a use for them in
        # this app.
        raise utils.RequestError(3117)
    return datetime.timedelta(seconds=value)


def _make_enum_converter(enum_class: enum.Enum) -> typing.Callable:
    """Create a converter for an enum class."""
    def enum_converter(value: typing.Union[str, int]) -> enum.Enum:
        """Convert a number to the relevant value in an enum."""
        value = int_converter(value)
        try:
            return enum_class(value)
        except ValueError:
            raise utils.RequestError(3114)
    return enum_converter


def _required_value(converter: typing.Callable) -> typing.Callable:
    """Wrap a converter and raise an error if no value is provided."""
    @functools.wraps(converter)
    def main(value: typing.Any) -> typing.Any:
        if value is not None:
            return converter(value)
        raise utils.RequestError(3101)
    return main


def _default_converter(
        default: typing.Any, converter: typing.Callable) -> typing.Callable:
    """Wrap a converter and provide a default value."""
    @functools.wraps(converter)
    def main(value: typing.Any) -> typing.Any:
        return converter(value) if value else default
    return main


def get_converters(
        endpoint: typing.Callable, user_arg_special: bool) -> tuple[
            bool, dict[str, typing.Callable]]:
    """Detect the type hints used and provide converters for them."""
    converters = {}
    authenticated = False
    params = list(inspect.signature(endpoint).parameters.items())
    could_be_self_or_cls = True
    could_be_user = user_arg_special
    for param in params:
        name, details = param
        if could_be_self_or_cls and name in ('self', 'cls'):
            # This won't work if there is a bound first parameter called
            # something else but it seems to be the best we can do.
            could_be_self_or_cls = False
            continue
        could_be_self_or_cls = False
        if could_be_user and name == 'user':
            authenticated = True
            could_be_user = False
            continue
        could_be_user = False
        type_hint = details.annotation
        if isinstance(type_hint, str):
            # If `from __future__ import annotations` is used, annotations
            # will be strings.
            type_hint = eval(type_hint, endpoint.__globals__)
        is_class = inspect.isclass(type_hint)
        is_generic = isinstance(type_hint, types.GenericAlias)
        if type_hint == str:
            converter = str
        elif type_hint == int:
            converter = int_converter
        elif type_hint == bytes:
            converter = _bytes_converter
        elif (
                (is_generic and typing.get_origin(type_hint) == dict)
                or type_hint == dict):
            converter = _dict_converter
        elif type_hint == datetime.timedelta:
            converter = _timedelta_converter
        elif is_class and issubclass(type_hint, peewee.Model):
            converter = type_hint.converter
        elif is_class and issubclass(type_hint, enum.Enum):
            converter = _make_enum_converter(type_hint)
        else:    # pragma: no cover
            type_hint_name = getattr(type_hint, '__name__', type_hint)
            raise RuntimeError(
                f'Converter needed for argument {name} ({type_hint_name}).'
            )
        if details.default != inspect._empty:
            converter = _default_converter(details.default, converter)
        else:
            converter = _required_value(converter)
        converters[name] = converter
    return authenticated, converters


def wrap(
        endpoint: typing.Callable,
        user_arg_special: bool = False,
        event_id_arg_special: bool = False) -> typing.Callable:
    """Wrap an endpoint to convert its arguments."""
    authenticated, converters = get_converters(endpoint, user_arg_special)

    @functools.wraps(endpoint)
    def wrapped(
            self_or_cls: typing.Any = None,
            **kwargs: dict[str, typing.Any]) -> typing.Any:
        """Convert arguments before calling the endpoint."""
        if authenticated and not kwargs.get('user'):
            raise utils.RequestError(1301)
        elif kwargs.get('user') and user_arg_special and not authenticated:
            del kwargs['user']
        converted = {}
        for kwarg in kwargs:
            if kwarg in converters:
                converted[kwarg] = converters[kwarg](kwargs[kwarg])
            elif kwarg == 'event_id' and event_id_arg_special:
                converted[kwarg] = int_converter(kwargs[kwarg])
            else:
                converted[kwarg] = kwargs[kwarg]
        try:
            args = (self_or_cls,) if self_or_cls else ()
            return endpoint(*args, **converted)
        except TypeError as e:
            if utils.is_wrong_arguments(e, endpoint):
                raise utils.RequestError(3102)
            else:    # pragma: no cover
                raise e

    return wrapped
