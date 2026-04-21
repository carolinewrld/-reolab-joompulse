from __future__ import annotations

from joompulse.storage import fingerprint as fp


def test_sha256_is_deterministic() -> None:
    data = b"hello-world"
    assert fp.sha256_bytes(data) == fp.sha256_bytes(data)
    assert fp.sha256_bytes(data) == fp.sha256_stream([b"hello-", b"world"])


def test_ext_mapping() -> None:
    assert fp.ext_from_content_type("image/jpeg") == "jpg"
    assert fp.ext_from_content_type("image/png; charset=utf-8") == "png"
    assert fp.ext_from_content_type("video/mp4") == "mp4"
    assert fp.ext_from_content_type(None) == "bin"
    assert fp.ext_from_content_type("application/x-strange") == "bin"


def test_asset_key_layout() -> None:
    key = fp.asset_key("a1b2c3" + "0" * 58, "image/png")
    assert key.startswith("assets/a1/")
    assert key.endswith(".png")
