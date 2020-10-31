"""Test hashing utility functions."""
from server.utils import hashing

from .utils import KasupelTest


ALGORITHM = 'sha256'


class TestHashing(KasupelTest):
    """Test hashing utility functions."""

    def test_check_hash_correct(self):
        """Test that a correct hash is matched."""
        hashed = hashing.hash_password('Welcome123', algorithm=ALGORITHM)
        self.assertEqual(
            hashing.HashedPassword(hashed, algorithm=ALGORITHM),
            'Welcome123'
        )

    def test_check_hash_incorrect(self):
        """Test that an incorrect hash is not matched."""
        hashed = hashing.hash_password('Welcome123', algorithm=ALGORITHM)
        self.assertNotEqual(
            hashing.HashedPassword(hashed, algorithm=ALGORITHM),
            'Goodbye321'
        )
