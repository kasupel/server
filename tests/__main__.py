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
from server import database, models

database.db.drop_tables(models.MODELS)
database.db.create_tables(models.MODELS)

# Run the tests.
from .test_chess import TestChess
from .test_converters import TestConverters, TestModelConverters
from .test_encryption import TestEncryption
from .test_hashing import TestHashing
from .test_images import TestImages
from .test_ratings import TestRatings
from .test_timing import TestTiming

unittest.main(exit=False)

# Create and display the report.
cov.stop()
cov.html_report(directory='coverage_report')
webbrowser.open(str(pathlib.Path('coverage_report') / 'index.html'))
