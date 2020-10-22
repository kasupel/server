"""Events for sending notifications."""
from . import helpers
from .. import models


def send_notification(socket_id: str, notif: models.Notification):
    """Send a user a notification."""
    helpers.send_room('notification', notif.to_json(), socket_id)
