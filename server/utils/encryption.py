"""Utilities for encryption.

Mostly just wrappers around the cryptography library.
"""
import pathlib

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


key_file = pathlib.Path(__file__).parent.parent.absolute() / 'private_key.pem'


def get_private_key() -> rsa.RSAPrivateKey:
    """Load a private key from a PEM file, or create if not found."""
    try:
        with open(key_file, 'rb') as file:
            raw_key = file.read()
    except FileNotFoundError:
        # FIXME: Vulnerable to MITM attack - we need a certificate.
        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        raw_key = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(key_file, 'wb') as file:
            file.write(raw_key)
        return key
    else:
        return serialization.load_pem_private_key(raw_key, password=None)


def load_keys() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Load the private and public keys.

    This should only be called once in the lifetime of the app.
    """
    private_key = get_private_key()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return private_key, public_key


PRIVATE_KEY, PUBLIC_KEY = load_keys()


def decrypt_message(
        ciphertext: bytes,
        private_key: rsa.RSAPrivateKey = PRIVATE_KEY) -> bytes:
    """Decrypt some message encrypted with out public key."""
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
