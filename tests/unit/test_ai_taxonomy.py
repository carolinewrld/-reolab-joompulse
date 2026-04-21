from __future__ import annotations

from pathlib import Path

from joompulse.ai.taxonomy import (
    DIMENSIONS,
    build_vocab,
    format_for_prompt,
    load_all,
)


def test_format_for_prompt_is_stable() -> None:
    terms = load_all(Path("taxonomy"))
    block1 = format_for_prompt(terms)
    block2 = format_for_prompt(terms)
    assert block1 == block2  # byte-for-byte stability enables prompt caching

    for dim in DIMENSIONS:
        assert f"## {dim}" in block1


def test_build_vocab() -> None:
    terms = load_all(Path("taxonomy"))
    vocab = build_vocab(terms)
    assert set(vocab) == set(DIMENSIONS)
    assert "shop_now" in vocab["cta"]
    assert "ugc_testimonial" in vocab["concept"]
