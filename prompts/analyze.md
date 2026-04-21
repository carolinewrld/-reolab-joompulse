# Performance verdict prompt

На вход:
- Абсолютные метрики креатива (impressions, clicks, spend, CTR, CPM, CPA, ROAS, conversions).
- Перцентили кабинета за скользящие 30 дней (p25, p50, p75) по тем же метрикам.
- Декомпозиция креатива (pain/concept/object/cta codes).

## Задача

1. Вычисли позицию креатива относительно бенчмарков.
2. Поставь вердикт: `best_performer` | `low_performer` | `neutral`.
3. Поставь численный `score` от -1.0 до 1.0 (−1 — худший, +1 — лучший).
4. В `rationale_md` — 3–5 предложений на русском: что делать маркетологу (выключать / масштабировать / A/B тестить).

## Формат ответа (строго JSON)

```json
{
  "verdict": "best_performer",
  "score": 0.73,
  "rationale_md": "..."
}
```
