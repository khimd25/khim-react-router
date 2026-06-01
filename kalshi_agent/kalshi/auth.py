"""Kalshi API key authentication.

Kalshi signs each request with an RSA-PSS (SHA-256) signature over the string
`timestamp_ms + HTTP_METHOD + request_path` (path WITHOUT the query string).
You generate an API key pair in the Kalshi web UI, download the private key PEM,
and point KALSHI_PRIVATE_KEY_PATH at it.

Three headers go on every authenticated request:
  KALSHI-ACCESS-KEY        -> your key ID
  KALSHI-ACCESS-TIMESTAMP  -> current unix time in MILLISECONDS
  KALSHI-ACCESS-SIGNATURE  -> base64(RSA-PSS-SHA256(message))
"""

from __future__ import annotations

import base64
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey


def load_private_key(path: str) -> RSAPrivateKey:
    """Load an RSA private key from a PEM file."""
    with open(path, "rb") as fh:
        key = serialization.load_pem_private_key(fh.read(), password=None)
    if not isinstance(key, RSAPrivateKey):
        raise TypeError("Kalshi API key must be an RSA private key")
    return key


def sign_request(private_key: RSAPrivateKey, timestamp_ms: int, method: str, path: str) -> str:
    """Return the base64-encoded RSA-PSS signature for one request.

    `path` is the path component only (e.g. "/trade-api/v2/markets") with no
    query string — strip "?..." before passing it in.
    """
    message = f"{timestamp_ms}{method.upper()}{path}".encode()
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def auth_headers(private_key: RSAPrivateKey, key_id: str, method: str, path: str) -> dict[str, str]:
    """Build the three Kalshi auth headers for a request."""
    timestamp_ms = int(time.time() * 1000)
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": str(timestamp_ms),
        "KALSHI-ACCESS-SIGNATURE": sign_request(private_key, timestamp_ms, method, path),
    }
