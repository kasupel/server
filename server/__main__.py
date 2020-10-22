"""Run the server."""
from .endpoints.helpers import app
from .events.helpers import socketio
from .timing import timer_loop


socketio.start_background_task(timer_loop)

socketio.run(app)
