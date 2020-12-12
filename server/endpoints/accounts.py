"""Respond to account related API calls.

This module does not handle encryption.
"""
import datetime
import hashlib
import re
import typing

import flask

import peewee

import requests

from . import helpers
from .. import enums, models, utils
from ..utils import emails


def _validate_username(username: str):
    """Validate a username.

    This does not enforce uniqueness.
    """
    if not username:
        raise utils.RequestError(1112)
    elif len(username) > 32:
        raise utils.RequestError(1111)


def _validate_password(password: str):
    """Validate that a password meets security requirements.

    Also checks against the haveibeenpwned.com database.
    """
    if len(password) < 10:
        raise utils.RequestError(1121)
    if len(password) > 32:
        raise utils.RequestError(1122)
    if len(set(password)) < 6:
        raise utils.RequestError(1123)
    sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
    hash_range = sha1_hash[:5]
    resp = requests.get(
        'https://api.pwnedpasswords.com/range/' + hash_range,
        headers={'Add-Padding': 'true'}
    )
    for line in resp.text.split('\n'):
        if line:
            hash_suffix, count = line.split(':')
            if int(count) and hash_range + hash_suffix == sha1_hash:
                raise utils.RequestError(1124)


def _validate_email(email: str):
    """Validate that an email is of a valid format.

    Does not validate that the address actually exists/is in use.
    Doesn't actually come close to validating that the email address, that is
    not very necessary though.
    """
    if len(email) > 255:
        raise utils.RequestError(1130)
    parts = email.split('@')
    if len(parts) < 2:
        raise utils.RequestError(1131)
    if len(parts) > 2:
        if not (parts[0].startswith('"') and parts[-2].endswith('"')):
            raise utils.RequestError(1131)


@helpers.endpoint('/accounts/login', method='POST', encrypt_request=True)
def login(
        username: str, password: str, token: bytes) -> dict[str, int]:
    """Create a new authentication session."""
    if len(token) != 32:
        raise utils.RequestError(1308)
    session = models.User.login(username, password, token)
    return {'session_id': session.id}


@helpers.endpoint('/accounts/logout', method='GET')
def logout(user: models.User):
    """Create a new authentication session."""
    flask.request.session.delete_instance()


@helpers.endpoint('/accounts/create', method='POST', encrypt_request=True)
def create_account(username: str, password: str, email: str):
    """Create a new user account."""
    _validate_username(username)
    _validate_password(password)
    _validate_email(email)
    try:
        user = models.User.create(
            username=username, password=password, email=email
        )
    except peewee.IntegrityError as e:
        type_, field = utils.interpret_integrity_error(e)
        if type_ == 'duplicate':
            if field == 'username':
                raise utils.RequestError(1113)
            elif field == 'email':
                raise utils.RequestError(1133)
        raise e
    send_verification_email(user=user)
    models.Notification.send(user, 'accounts.welcome')


@helpers.endpoint('/accounts/resend_verification_email', method='GET')
def send_verification_email(user: models.User):
    """Send a verification email to a user."""
    if user.email_verified:
        raise utils.RequestError(1201)
    message = (
        f'Here is the code to verify your email address: '
        f'{user.email_verify_token}.'
    )
    emails.send_email(user.email, message, 'Kasupel email verification')


@helpers.endpoint('/accounts/verify_email', method='GET')
def verify_email(user: models.User, token: str):
    """Verify an email address."""
    if user.email_verify_token == token:
        user.email_verified = True
        user.save()
    else:
        raise utils.RequestError(1202)


@helpers.endpoint('/accounts/me', method='PATCH', encrypt_request=True)
def update_account(
        user: models.User, password: str = None, email: str = None):
    """Update a user's account."""
    if password:
        _validate_password(password)
        user.password = password
    if email:
        _validate_email(email)
        user.email = email
    try:
        user.save()
    except peewee.IntegrityError as e:
        type_, field = utils.interpret_integrity_error(e)
        if type_ == 'duplicate' and field == 'email':
            raise utils.RequestError(1133)
        raise e
    else:
        if email:
            send_verification_email(user=user)


@helpers.endpoint('/accounts/me/avatar', method='PATCH')
def update_avatar(user: models.User, avatar: bytes):
    """Update a user's avatar.

    This is separate from update_account because the avatar does not need to
    be encrypted and in fact since it is a large amount of data, attempting to
    encrypt it can cause problems.
    """
    user.avatar = avatar
    user.save()


@helpers.endpoint('/accounts/me', method='GET')
def get_own_account(user: models.User) -> dict[str, typing.Any]:
    """Get the user's own account."""
    data = user.to_json(hide_email=False)
    return data


@helpers.endpoint('/users/<account>', method='GET')
def get_account(account: models.User) -> dict[str, typing.Any]:
    """Get a user account."""
    return account.to_json()


@helpers.endpoint('/accounts/account', method='GET')
def get_account_by_id(id: int) -> dict[str, typing.Any]:
    """Get a user account by ID."""
    try:
        account = models.User.get_by_id(id)
    except peewee.DoesNotExist:
        raise utils.RequestError(1001)
    return account.to_json()


@helpers.endpoint('/accounts/all', method='GET')
def get_accounts(page: int = 0) -> dict[str, typing.Any]:
    """Get a paginated list of accounts."""
    users, pages = helpers.paginate(
        models.User.select().order_by(models.User.elo.desc()), page
    )
    return {
        'users': [user.to_json() for user in users],
        'pages': pages
    }


@helpers.endpoint('/accounts/me', method='DELETE')
def delete_account(user: models.User):
    """Delete a user's account."""
    models.Game.delete().where((
        (models.Game.host == user) & (models.Game.away == None)
        | (models.Game.host == None) & (models.Game.away == user)
    ))    # noqa: E711
    models.Game.update(
        winner=enums.Winner.AWAY, conclusion_type=enums.Conclusion.RESIGN,
        ended_at=datetime.datetime.now()
    ).where(models.Game.host == user)
    models.Game.update(
        winner=enums.Winner.HOST, conclusion_type=enums.Conclusion.RESIGN,
        ended_at=datetime.datetime.now()
    ).where(models.Game.away == user)
    user.delete_instance()


@helpers.endpoint('/accounts/notifications', method='GET')
def get_notifications(
        user: models.User, page: int = 0) -> dict[str, typing.Any]:
    """Get a paginated list of notifications for the user."""
    query, pages = helpers.paginate(user.notifications, page)
    unread = models.Notification.select().where(
        models.Notification.user == user,
        models.Notification.read == False    # noqa:E712
    ).count()
    return {
        'notifications': [notif.to_json() for notif in query],
        'unread_count': unread,
        'pages': pages
    }


@helpers.endpoint('/accounts/notifications/unread_count', method='GET')
def unread_notification_count(
        user: models.User, page: int = 0) -> dict[str, typing.Any]:
    """Check how many unread notifications the user has."""
    count = models.Notification.select().where(
        models.Notification.user == user,
        models.Notification.read == False    # noqa:E712
    ).count()
    return {'count': count}


@helpers.endpoint('/accounts/notifications/ack', method='POST')
def acknowledge_notification(
        user: models.User, notification: models.Notification):
    """Mark a notification as read."""
    notification.read = True
    notification.save()


@helpers.endpoint(
    '/media/avatar/<avatar_name>', method='GET', return_type='image'
)
def get_avatar(avatar_name: str) -> bytes:
    """Get a user's avatar."""
    m = re.match(r'(\d+)-(\d+)\.(gif|jpeg|png|webp)$', avatar_name)
    if not m:
        raise utils.RequestError(5001)
    user_id, avatar_id, ext = m.groups()
    user_id = int(user_id)
    avatar_id = int(avatar_id)
    user = models.User.get_or_none(
        models.User.id == user_id,
        models.User.avatar_number == avatar_id,
        models.User.avatar_extension == ext
    )
    if not user:
        raise utils.RequestError(5001)
    return avatar_name, user.avatar
