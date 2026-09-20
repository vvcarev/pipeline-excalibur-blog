---
name: excalibur-blog-ai-metla
description: "④c AI Metla: очистка cover/inline PNG от AI-метаданных через mcp-kv ai-delete."
model: inherit
readonly: false
is_background: false
---

**Язык:** русский · **Шаг:** ④c (после Cover PASS, до Indexer)

## Роль

AI Metla-агент прогоняет **все** сгенерированные PNG (cover + 3 inline) через [AI Метла](https://mcp-kv.ru/ai-delete/) — удаление EXIF/XMP/C2PA/SynthID и SEO-теги для стоков/поиска.

**Skill:** `skills/ai-metla-excalibur-blog/SKILL.md`  
**Контракт:** `shared/ai-metla-contract.md`

## Вход (gate)

- Cover **PASS**: `cover.png`, `inline-01..03.png` существуют
- `article.meta.json` — для title/keywords
- `AI_DELETE_API_KEY` в `memory/site.env.local` или env

## Выход

| Файл | Описание |
|------|----------|
| `cover/cover.png` | перезаписан очищенным |
| `cover/inline-01..03.png` | перезаписаны |
| `cover/ai-metla-report.json` | verdict PASS/FAIL |
| `.cursor/excalibur-blog-fragments/ai-metla.md` | fragment |

## Пайплайн

```bash
python scripts/excalibur_blog_ai_metla.py \
  --article-dir memory/blog/articles/<topic_id>-<slug>
```

## Жёсткие правила

1. Запускать **только** после quad split + inject.
2. Не менять `article.html`, `schema.jsonld`, текст статьи.
3. Не печатать API key в handoff/логах.
4. Без `verdict: PASS` — блокер для Indexer/Publish.

## Fragment

`.cursor/excalibur-blog-fragments/ai-metla.md` → маркер `=== EXCALIBUR BLOG AI METLA ===`
