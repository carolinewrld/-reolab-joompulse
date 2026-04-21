# Creative decomposition prompt

На вход: изображение (или набор кадров видео) + текст креатива (title, body).

## Таксономия

{taxonomy_block}

## Задача

Разложи креатив по измерениям: `pain`, `concept`, `object`, `cta`.

Правила:
- Каждое значение — строго `code` из словаря.
- Если чего-то нет в словаре — используй код `"other"` и заполни `other_suggestions` предложением нового термина (snake_case + русский лейбл).
- Для каждого измерения допускается от 0 до 3 значений.
- В `rationale_md` — 2–4 предложения на русском, почему выбрал эти теги.

## Формат ответа (строго JSON)

```json
{
  "pain_codes": ["..."],
  "concept_codes": ["..."],
  "object_codes": ["..."],
  "cta_codes": ["..."],
  "other_suggestions": [
    {"dimension": "pain", "code": "snake_case", "label_ru": "..."}
  ],
  "rationale_md": "..."
}
```
