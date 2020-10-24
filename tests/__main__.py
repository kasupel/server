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
cov = coverage.Coverage(include='server/*')
cov.start()

# Import the tests (these import the server module so must be imported after
# we have added it to PATH and set up the coverage monitor).
from .test_ratings import TestRatings
from .test_images import TestImages

# Run the tests.
unittest.main(exit=False)

# Create and display the report.
cov.stop()
cov.html_report(directory='coverage_report')
webbrowser.open(str(pathlib.Path('coverage_report') / 'index.html'))
