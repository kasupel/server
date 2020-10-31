"""Test runner."""
import pathlib
import sys
import unittest
import webbrowser

import coverage


# Add the server module we are testing to the PATH so we can import it.
module_path = pathlib.Path(__file__).parent.parent.absolute() / 'server'
sys.path.append(module_path)

# Set up the coverage monitor.
cov = coverage.Coverage(source_pkgs=(
    'server', 'server.endpoints', 'server.events', 'server.gamemodes'
), branch=True)

cov.start()

# Wipe the database ready for tests.
from server import database, models    # noqa: E402

database.db.drop_tables(models.MODELS)
database.db.create_tables(models.MODELS)

# Run the tests.
from .test_chess import TestChess    # noqa: F401,E402
from .test_images import TestImages    # noqa: F401,E402
from .test_ratings import TestRatings    # noqa: F401,E402

unittest.main(exit=False)

# Create and display the report.
cov.stop()
cov.html_report(directory='coverage_report')
webbrowser.open(str(pathlib.Path('coverage_report') / 'index.html'))
