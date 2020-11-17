"""Create the SocketIO server."""
import flask_socketio as sockets

from .. import endpoints


socketio = sockets.SocketIO(endpoints.app, always_connect=True)
