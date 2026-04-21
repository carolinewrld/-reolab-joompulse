from __future__ import annotations

import pytest

from joompulse.security import crypto


def test_encrypt_decrypt_roundtrip() -> None:
    token = "EAABsbCS...longtoken...XYZ"
    blob = crypto.encrypt(token)
    assert isinstance(blob, bytes) and blob != token.encode()
    assert crypto.decrypt(blob) == token


def test_decrypt_fails_for_tampered_blob() -> None:
    blob = crypto.encrypt("hello")
    with pytest.raises(crypto.DecryptionFailed):
        crypto.decrypt(blob + b"tamper")


def test_mask() -> None:
    assert crypto.mask("supersecret").endswith("cret")
    assert "*" in crypto.mask("supersecret")
    assert crypto.mask("ab") == "**"
