"""Decomposer flow test — mocks Claude + S3, exercises the core orchestration
logic without touching the real DB (session is stubbed via a small recorder).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from joompulse.ai import decomposer
from joompulse.ai.schema import DecompositionResult
from joompulse.db.models.enums import AssetKind


@dataclass
class _FakeCreative:
    id: uuid.UUID
    meta_creative_id: str = "c1"
    title: str | None = "Купи кроссовки"
    body: str | None = "Скидка до 30 апреля"
    cta_type: str | None = "SHOP_NOW"


@dataclass
class _FakeAsset:
    kind: AssetKind
    s3_key: str
    creative_id: uuid.UUID


class _FakeResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one(self) -> Any:
        return self._value


class _FakeSession:
    """Minimal async-session stub: returns pre-seeded scalars and captures inserts."""

    def __init__(self, *, creative: _FakeCreative, asset: _FakeAsset | None, terms: list[Any]) -> None:
        self._creative = creative
        self._asset = asset
        self._terms = terms
        self._scalars_calls = 0
        self.executed: list[Any] = []
        self.committed = False

    async def scalar(self, stmt: Any) -> Any:
        # The decomposer calls session.scalar twice: first for Creative, then for CreativeAsset.
        self._scalars_calls += 1
        if self._scalars_calls == 1:
            return self._creative
        return self._asset

    async def execute(self, stmt: Any) -> Any:
        self.executed.append(stmt)
        # taxonomy.load_from_db issues a select on TaxonomyTerm — we emulate .scalars().all()
        class _ScalarsProxy:
            def __init__(self, terms: list[Any]) -> None:
                self._terms = terms

            def all(self) -> list[Any]:
                return self._terms

        class _Res:
            def __init__(self, terms: list[Any]) -> None:
                self._terms = terms

            def scalars(self) -> _ScalarsProxy:
                return _ScalarsProxy(self._terms)

        return _Res(self._terms)

    async def commit(self) -> None:
        self.committed = True


@dataclass
class _FakeTerm:
    dimension: str
    code: str
    label_ru: str
    label_en: str | None = None
    description: str | None = None


@pytest.fixture
def fake_terms() -> list[_FakeTerm]:
    return [
        _FakeTerm("pain", "high_price", "Дорого"),
        _FakeTerm("concept", "ugc_testimonial", "UGC-отзыв"),
        _FakeTerm("object", "person_using_product", "Человек использует продукт"),
        _FakeTerm("cta", "shop_now", "Купить сейчас"),
    ]


@pytest.fixture
def stub_anthropic(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    class _Block:
        type = "tool_use"
        name = "save_decomposition"
        input = {
            "pain_codes": ["high_price"],
            "concept_codes": ["ugc_testimonial"],
            "object_codes": ["person_using_product", "mystery"],  # mystery must be dropped
            "cta_codes": ["shop_now"],
            "other_suggestions": [],
            "rationale_md": "ok",
        }

    class _Msg:
        stop_reason = "tool_use"
        content = [_Block()]

    async def fake_call(**kwargs: Any):  # noqa: ANN401
        captured.update(kwargs)
        return _Msg(), _Block.input

    monkeypatch.setattr("joompulse.ai.decomposer.call_with_tool", fake_call)
    return captured


@pytest.fixture
def stub_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(key: str) -> bytes:
        return b"\x89PNG\r\n\x1a\n" + key.encode()

    monkeypatch.setattr("joompulse.ai.decomposer.get_object_bytes", fake_get)


async def test_decompose_image_creative(
    stub_anthropic: dict[str, Any],
    stub_s3: None,
    fake_terms: list[_FakeTerm],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    creative_id = uuid.uuid4()
    creative = _FakeCreative(id=creative_id)
    asset = _FakeAsset(kind=AssetKind.IMAGE, s3_key="assets/ab/abc.png", creative_id=creative_id)

    # taxonomy.load_from_db uses session.execute(...).scalars().all()
    session = _FakeSession(creative=creative, asset=asset, terms=fake_terms)

    outcome = await decomposer.decompose_creative(session, creative_id)

    assert outcome is not None
    assert outcome.creative_id == creative_id
    assert outcome.result.pain_codes == ["high_price"]
    # 'mystery' should have been stripped because it's not in vocab
    assert outcome.result.object_codes == ["person_using_product"]
    assert session.committed

    # System prompt must include the cached taxonomy block.
    system = stub_anthropic["system"]
    assert isinstance(system, decomposer.CachedSystem)
    assert "`high_price`" in system.cached_block
    cached_api = system.to_api()[1]
    assert cached_api["cache_control"] == {"type": "ephemeral"}


async def test_decompose_creative_returns_none_when_missing(
    fake_terms: list[_FakeTerm],
) -> None:
    class _EmptySession(_FakeSession):
        async def scalar(self, stmt: Any) -> Any:
            return None

    session = _EmptySession(
        creative=_FakeCreative(id=uuid.uuid4()), asset=None, terms=fake_terms
    )
    outcome = await decomposer.decompose_creative(session, uuid.uuid4())
    assert outcome is None


def test_tool_schema_matches_pydantic() -> None:
    """Tool definition and Pydantic validator must agree on required fields."""
    required = set(decomposer.TOOL["input_schema"]["required"])
    model_fields = set(DecompositionResult.model_fields)
    assert required.issubset(model_fields)
