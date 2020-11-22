"""Helpers for all endpoints."""
from __future__ import annotations

import base64
import functools
import io
import json
import math
import traceback
import typing

import flask

import peewee

from .. import database, endpoints, models, utils
from ..utils import encryption


def paginate(
        query: peewee.SelectQuery, page: int = 0,
        per_page: int = 100) -> tuple[peewee.SelectQuery, int]:
    """Paginate the results of a query.

    Returns results and number of pages.
    """
    total_results = query.count()
    pages = math.ceil(total_results / per_page)
    if pages and page >= pages:
        raise utils.RequestError(3201)
    page = query.offset(page * per_page).limit(per_page)
    return page, pages


def _decrypt_request(raw: bytes) -> dict[str, typing.Any]:
    """Decrypt a JSON object encrypted with our public key."""
    try:
        raw_json = encryption.decrypt_message(base64.b64decode(raw))
    except ValueError:
        raise utils.RequestError(3113)
    try:
        return json.loads(raw_json.decode())
    except json.JSONDecodeError:
        raise utils.RequestError(3113)
    except UnicodeDecodeError:
        raise utils.RequestError(3113)


def _process_request(
        request: flask.Request, method: str,
        encrypt_request: bool,
        require_verified_email: bool) -> dict[str, typing.Any]:
    """Handle authentication and encryption."""
    if method in ('GET', 'DELETE'):
        data = dict(request.args)
    elif method in ('POST', 'PATCH'):
        if encrypt_request:
            data = _decrypt_request(request.get_data())
        else:
            data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            raise utils.RequestError(3113)
    session_id = None
    session_token = None
    if 'session_id' in data:
        session_id = data.pop('session_id')
    if 'session_token' in data:
        session_token = data.pop('session_token')
    if bool(session_id) ^ bool(session_token):
        raise utils.RequestError(1303)
    if session_id and session_token:
        session = models.Session.validate_session_key(
            session_id, session_token
        )
        request.session = session
        user = session.user
        if require_verified_email and not user.email_verified:
            raise utils.RequestError(1307)
        data['user'] = user
    else:
        request.session = None
    return data


def endpoint(
        url: str, method: str,
        encrypt_request: bool = False,
        return_type: str = 'json',
        require_verified_email: bool = False,
        database_transaction: bool = True) -> typing.Callable:
    """Create a wrapper for an endpoint."""
    method = method.upper()
    if method not in ('GET', 'DELETE', 'POST', 'PATCH'):
        # pragma: no cover
        raise RuntimeError(f'Unhandled method "{method}".')
    if encrypt_request and method not in ('POST', 'PATCH'):
        # pragma: no cover
        raise RuntimeError('Cannot encrypt bodyless request.')
    if url.endswith('/'):    # pragma: no cover
        raise RuntimeError(f'Endpoint with trailing slash found ({url}).')

    def wrapper(main: typing.Callable) -> typing.Callable:
        """Wrap an endpoint."""
        if database_transaction:
            main = database.db.atomic()(main)
        converter_wrapped = utils.converters.wrap(main, user_arg_special=True)

        @functools.wraps(main)
        def return_wrapped(
                **kwargs: dict[str, typing.Any]) -> typing.Any:
            """Handle errors and convert the response to JSON."""
            try:
                data = _process_request(
                    flask.request, method, encrypt_request,
                    require_verified_email
                )
                data.update(kwargs)
                response = converter_wrapped(**data)
            except utils.RequestError as error:
                response = error.as_dict
                code = 400
            else:
                code = 200
            if response is None:
                code = 204
            if return_type == 'json' or code == 400:
                response = flask.jsonify(response or {})
                return response, code
            elif return_type == 'text':
                response = response or ''
                return flask.Response(
                    response, status=code, mimetype='text/plain'
                )
            elif return_type == 'image':
                filename, data = response
                return flask.send_file(
                    io.BytesIO(data), cache_timeout=31536000,
                    attachment_filename=filename
                )
            else:    # pragma: no cover
                raise RuntimeError(f'Unkown return type {return_type}.')

        flask_wrapped = endpoints.app.route(url, methods=[method])(
            return_wrapped
        )
        return flask_wrapped

    return wrapper


@endpoint(
    '/rsa_key', method='GET', return_type='text', database_transaction=False
)
def get_public_key() -> str:
    """Get our public RSA key."""
    return encryption.PUBLIC_KEY


@endpoints.app.errorhandler(404)
def not_found(_error: typing.Any) -> flask.Response:
    """Handle an unkown URL being used."""
    return flask.jsonify(utils.RequestError(3301).as_dict), 404


@endpoints.app.errorhandler(500)
def internal_error(error: Exception) -> flask.Response:
    """Handle an internal error."""
    traceback.print_tb(error.__traceback__)
    print(f'{type(error).__name__}: {error}')
    return flask.jsonify(utils.RequestError(4001).as_dict), 500
