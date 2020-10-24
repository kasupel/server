"""Tests for image validation."""
import pathlib
import typing
import unittest

from server import images
from server.endpoints import helpers


class TestImages(unittest.TestCase):
    """Tests for image validation."""

    def assert_raises_request_error(self, fun: typing.Callable, code: int):
        """Assert that a function raises some request error."""
        try:
            fun()
        except helpers.RequestError as e:
            self.assertEqual(e.code, code)
        else:
            self.assertTrue(False, 'RequestError was not raised.')

    def _test_image(self, image_name: str) -> bytes:
        """Open an image from the res folder and validate it.

        Returns a callable which will call the validate function on the
        specified image.
        """
        path = pathlib.Path(__file__).parent.absolute() / 'res' / image_name
        with open(path, 'rb') as f:
            data = f.read()
        return lambda: images.validate(data)

    def test_big_image(self):
        """Test when the image is too big."""
        self.assert_raises_request_error(self._test_image('big.jpg'), 3116)

    def test_svg_image(self):
        """Test when the image is of an invalid format (svg)."""
        self.assert_raises_request_error(self._test_image('image.svg'), 3115)

    def test_gif_image(self):
        """Test when the image is a GIF."""
        self.assertEqual(self._test_image('image.gif')(), 'gif')

    def test_png_image(self):
        """Test when the image is a PNG."""
        self.assertEqual(self._test_image('image.png')(), 'png')

    def test_jpeg_image(self):
        """Test when the image is a JPEG."""
        self.assertEqual(self._test_image('image.jpg')(), 'jpeg')

    def test_webp_image(self):
        """Test when the image is a WEBP."""
        self.assertEqual(self._test_image('image.webp')(), 'webp')
