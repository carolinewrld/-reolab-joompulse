"""Vision-based creative decomposition.

Pipeline (per creative):
  1. Load creative row + its primary asset from S3.
  2. If asset is a video, sample N frames via ffmpeg; otherwise use the
     image as-is. If no asset, fall back to text-only analysis (title+body).
  3. Build a Claude Vision request:
       • system = static behavioural prompt + *cached* taxonomy block
       • user  = images (if any) followed by decompose instructions and the
                 creative's textual copy
       • force tool_use(save_decomposition) so the response is structured
  4. Validate tool output against the active taxonomy vocabulary, then upsert
     a `creative_analysis` row.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from joompulse.ai import taxonomy as tax
from joompulse.ai.client import CachedSystem, call_with_tool, image_block, text_block
from joompulse.ai.prompts import decompose_prompt, system_prompt
from joompulse.ai.schema import DecompositionResult
from joompulse.ai.video import sample_frames_from_bytes
from joompulse.config import get_settings
from joompulse.db.models import Creative, CreativeAnalysis, CreativeAsset
from joompulse.db.models.enums import AssetKind
from joompulse.logging import get_logger
from joompulse.storage.s3 import get_object_bytes

log = get_logger(__name__)

TOOL: dict[str, Any] = {
    "name": "save_decomposition",
    "description": "Сохранить результат декомпозиции креатива в нормированном виде.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pain_codes": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "concept_codes": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "object_codes": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "cta_codes": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "other_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "dimension": {
                            "type": "string",
                            "enum": ["pain", "concept", "object", "cta"],
                        },
                        "code": {"type": "string"},
                        "label_ru": {"type": "string"},
                    },
                    "required": ["dimension", "code", "label_ru"],
                },
            },
            "rationale_md": {"type": "string"},
        },
        "required": [
            "pain_codes",
            "concept_codes",
            "object_codes",
            "cta_codes",
            "rationale_md",
        ],
    },
}


@dataclass(slots=True)
class DecomposeOutcome:
    creative_id: uuid.UUID
    analysis_id: uuid.UUID
    result: DecompositionResult


async def decompose_creative(
    session: AsyncSession,
    creative_id: uuid.UUID,
) -> DecomposeOutcome | None:
    settings = get_settings()

    creative = await session.scalar(select(Creative).where(Creative.id == creative_id))
    if creative is None:
        log.warning("decompose.creative_missing", creative_id=str(creative_id))
        return None

    asset = await session.scalar(
        select(CreativeAsset).where(CreativeAsset.creative_id == creative_id).limit(1)
    )

    images: list[bytes] = []
    asset_kind: AssetKind | None = asset.kind if asset else None

    if asset is not None:
        blob = await get_object_bytes(asset.s3_key)
        if asset.kind is AssetKind.VIDEO:
            frames = sample_frames_from_bytes(
                blob,
                fps=settings.video_sample_fps,
                max_frames=settings.video_frames_per_request,
            )
            images = [f.jpeg for f in frames]
        else:
            images = [blob]

    terms = await tax.load_from_db(session)
    if not terms:
        raise RuntimeError("taxonomy is empty; run `joompulse taxonomy sync` first")
    vocab = tax.build_vocab(terms)
    taxonomy_block = tax.format_for_prompt(terms)

    system = CachedSystem(static_block=system_prompt(), cached_block=taxonomy_block)

    user_content: list[dict[str, Any]] = []
    for img in images:
        user_content.append(image_block(img))
    user_content.append(
        text_block(
            decompose_prompt().replace(
                "{taxonomy_block}",
                "(см. system-сообщение — словарь закэширован там)",
            )
            + "\n\n---\n"
            + _format_creative_text(creative, asset_kind)
        )
    )

    message, raw = await call_with_tool(
        model=settings.claude_model_decompose,
        system=system,
        user_content=user_content,
        tool=TOOL,
        max_tokens=1024,
    )

    result = DecompositionResult.model_validate(raw).validate_against_vocab(vocab)

    analysis_id = uuid.uuid4()
    await session.execute(
        insert(CreativeAnalysis).values(
            id=analysis_id,
            creative_id=creative_id,
            pain_codes=result.pain_codes,
            concept_codes=result.concept_codes,
            object_codes=result.object_codes,
            cta_codes=result.cta_codes,
            other_suggestions=[s.code for s in result.other_suggestions],
            raw_json={"tool_input": raw, "stop_reason": message.stop_reason},
            embedding=None,
            model_version=settings.claude_model_decompose,
        )
    )
    await session.commit()

    log.info(
        "decompose.done",
        creative_id=str(creative_id),
        analysis_id=str(analysis_id),
        pain=result.pain_codes,
        concept=result.concept_codes,
        object=result.object_codes,
        cta=result.cta_codes,
        other=len(result.other_suggestions),
    )
    return DecomposeOutcome(creative_id=creative_id, analysis_id=analysis_id, result=result)


def _format_creative_text(creative: Creative, asset_kind: AssetKind | None) -> str:
    parts = [f"# Креатив `{creative.meta_creative_id}`"]
    if asset_kind is not None:
        parts.append(f"- Тип ассета: **{asset_kind.value}**")
    elif creative.cta_type is None and not (creative.title or creative.body):
        parts.append("- Ассет недоступен, анализ по текстовым полям.")
    if creative.title:
        parts.append(f"- Заголовок: {creative.title}")
    if creative.body:
        parts.append(f"- Текст: {creative.body}")
    if creative.cta_type:
        parts.append(f"- CTA (Meta): `{creative.cta_type}`")
    return "\n".join(parts)
