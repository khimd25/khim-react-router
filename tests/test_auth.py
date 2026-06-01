from __future__ import annotations

import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from kalshi_agent.kalshi.auth import auth_headers, sign_request


def _make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class TestSignRequest:
    def test_returns_valid_base64(self):
        key = _make_key()
        sig = sign_request(key, 1700000000000, "GET", "/trade-api/v2/markets")
        raw = base64.b64decode(sig)
        assert len(raw) > 0

    def test_signature_verifies(self):
        key = _make_key()
        ts = 1700000000000
        method = "GET"
        path = "/trade-api/v2/markets"
        sig = sign_request(key, ts, method, path)
        message = f"{ts}{method}{path}".encode()
        key.public_key().verify(
            base64.b64decode(sig),
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )

    def test_different_methods_differ(self):
        key = _make_key()
        sig_get = sign_request(key, 1700000000000, "GET", "/path")
        sig_post = sign_request(key, 1700000000000, "POST", "/path")
        assert sig_get != sig_post


class TestAuthHeaders:
    def test_contains_required_keys(self):
        key = _make_key()
        headers = auth_headers(key, "my-key-id", "GET", "/trade-api/v2/markets")
        assert headers["KALSHI-ACCESS-KEY"] == "my-key-id"
        assert "KALSHI-ACCESS-TIMESTAMP" in headers
        assert "KALSHI-ACCESS-SIGNATURE" in headers

    def test_timestamp_is_recent(self):
        import time
        key = _make_key()
        headers = auth_headers(key, "k", "GET", "/p")
        ts = int(headers["KALSHI-ACCESS-TIMESTAMP"])
        now_ms = int(time.time() * 1000)
        assert abs(now_ms - ts) < 5000
