"""Run the server."""
from .endpoints.helpers import app
from .events import connections, games    # noqa: F401
from .events.helpers import socketio
from .timing import timer_loop


socketio.start_background_task(timer_loop)

socketio.run(app)
