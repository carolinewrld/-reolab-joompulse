"""Symmetric encryption for secrets stored in the DB (Meta access tokens).

The key lives in env `ENCRYPTION_KEY` — a 32-byte urlsafe base64 blob, which is
what Fernet consumes. Generate with: `joompulse gen-key`.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from joompulse.config import get_settings


class EncryptionKeyMissing(RuntimeError):
    pass


class DecryptionFailed(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw = get_settings().encryption_key.get_secret_value().encode()
    if not raw:
        raise EncryptionKeyMissing(
            "ENCRYPTION_KEY is empty. Generate with `joompulse gen-key` and set in .env"
        )
    return Fernet(raw)


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    try:
        return _fernet().decrypt(ciphertext).decode()
    except InvalidToken as exc:
        raise DecryptionFailed("invalid ciphertext or wrong ENCRYPTION_KEY") from exc


def mask(secret: str, keep: int = 4) -> str:
    if len(secret) <= keep:
        return "*" * len(secret)
    return f"{'*' * (len(secret) - keep)}{secret[-keep:]}"
