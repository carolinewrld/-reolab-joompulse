from __future__ import annotations

import pytest

from joompulse.ai.schema import DecompositionResult, OtherSuggestion


def test_parse_minimal() -> None:
    r = DecompositionResult.model_validate(
        {
            "pain_codes": ["high_price"],
            "concept_codes": ["ugc_testimonial"],
            "object_codes": ["person_using_product"],
            "cta_codes": ["shop_now"],
            "rationale_md": "ok",
        }
    )
    assert r.pain_codes == ["high_price"]
    assert r.other_suggestions == []


def test_other_suggestion_rejects_bad_dimension() -> None:
    with pytest.raises(Exception):
        OtherSuggestion.model_validate(
            {"dimension": "colour", "code": "x", "label_ru": "x"}
        )


def test_validate_against_vocab_drops_unknown_but_keeps_other() -> None:
    r = DecompositionResult.model_validate(
        {
            "pain_codes": ["high_price", "wat", "other"],
            "concept_codes": ["unknown"],
            "object_codes": ["person_face_closeup"],
            "cta_codes": [],
            "rationale_md": "",
        }
    )
    vocab = {
        "pain": {"high_price"},
        "concept": {"ugc_testimonial"},
        "object": {"person_face_closeup"},
        "cta": {"shop_now"},
    }
    cleaned = r.validate_against_vocab(vocab)
    assert cleaned.pain_codes == ["high_price", "other"]
    assert cleaned.concept_codes == []
    assert cleaned.object_codes == ["person_face_closeup"]
