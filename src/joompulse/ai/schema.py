"""Pydantic models used to validate LLM tool-use output."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

_DIMENSIONS = ("pain", "concept", "object", "cta")


class OtherSuggestion(BaseModel):
    dimension: str
    code: str
    label_ru: str

    @field_validator("dimension")
    @classmethod
    def _dim_allowed(cls, v: str) -> str:
        if v not in _DIMENSIONS:
            raise ValueError(f"dimension must be one of {_DIMENSIONS}, got {v!r}")
        return v


class DecompositionResult(BaseModel):
    pain_codes: list[str] = Field(default_factory=list)
    concept_codes: list[str] = Field(default_factory=list)
    object_codes: list[str] = Field(default_factory=list)
    cta_codes: list[str] = Field(default_factory=list)
    other_suggestions: list[OtherSuggestion] = Field(default_factory=list)
    rationale_md: str = ""

    def validate_against_vocab(
        self,
        vocab: dict[str, set[str]],
    ) -> "DecompositionResult":
        """Drop any code that is not in the supplied vocabulary (except 'other').

        Unknown codes survive only via `other_suggestions` so that decomposition
        still writes clean data while candidate terms queue up for review.
        """
        cleaned = self.model_copy(deep=True)
        for dim in _DIMENSIONS:
            field_name = f"{dim}_codes"
            allowed = vocab.get(dim, set()) | {"other"}
            current: list[str] = getattr(cleaned, field_name)
            setattr(cleaned, field_name, [c for c in current if c in allowed])
        return cleaned
