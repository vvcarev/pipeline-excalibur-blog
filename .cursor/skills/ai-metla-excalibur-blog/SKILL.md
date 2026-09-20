# Excalibur BLOG — AI Metla Agent

## Когда запускаться

Сразу после **④a Cover PASS** (quad split + inject). **До** ⑤ Indexer и Publish.

Schema (④b) может идти параллельно с Cover; Metla ждёт только Cover.

## Runbook

```bash
cd <plugin-or-vendor-root>
export EXCALIBUR_PROJECT_ROOT=<memory-root>

python scripts/excalibur_blog_ai_metla.py \
  --article-dir memory/blog/articles/<topic_id>-<slug>
```

Опционально canvas:

```bash
python scripts/excalibur_blog_ai_metla.py \
  --article-dir ... \
  --include-canvas
```

## SEO-поля

Скрипт читает `article.meta.json`:

- `title` ← H1
- `author` ← Виктор Прокопчук
- `copyright` ← © Eto Digital
- `software` ← Adobe Photoshop
- `keywords` ← primary_keyword + etodigital

## QA перед ✅

- [ ] `ai-metla-report.json` → `verdict: PASS`
- [ ] 4 файла в `files[]` со `status: PASS`
- [ ] PNG byte size > 0 после перезаписи
- [ ] fragment `ai-metla.md` записан

## Blockers

- нет `AI_DELETE_API_KEY`
- нет PNG после cover
- API timeout / clean-url error

## Fragment template

```markdown
=== EXCALIBUR BLOG AI METLA ===
topic_id:
status: PASS|FAIL
files_cleaned: 4
report: cover/ai-metla-report.json
```
