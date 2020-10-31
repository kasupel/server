"""Test cryptography utility functions."""
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from server.utils import encryption

from .utils import KasupelTest


class TestEncryption(KasupelTest):
    """Test cryptography utility functions."""

    def setUp(self):
        """Ensure that no keys are saved before the test."""
        try:
            os.remove(encryption.key_file)
        except FileNotFoundError:
            pass
        super().setUp()

    def test_generate_and_use_key(self):
        """Test generating and decrypting with a private key."""
        private, raw_public = encryption.load_keys()
        public = serialization.load_pem_public_key(raw_public.encode())
        ciphertext = public.encrypt(
            b'Test message.',
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        plaintext = encryption.decrypt_message(ciphertext, private)
        self.assertEqual(b'Test message.', plaintext)

    def test_key_serialisation(self):
        """Test saving and loading a key from a file."""
        _private, old_public = encryption.load_keys()
        _private, new_public = encryption.load_keys()
        self.assertEqual(old_public, new_public)
