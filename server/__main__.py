"""Run the server."""
from .endpoints import accounts, app, games, helpers, matchmaking    # noqa: F401,E501
from .events import connections, games, notifications, socketio    # noqa: F401,F811,E501
from .timing import timer_loop


socketio.start_background_task(timer_loop)

socketio.run(app)
