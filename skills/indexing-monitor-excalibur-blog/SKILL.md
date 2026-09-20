---
name: indexing-monitor-excalibur-blog
description: Excalibur BLOG — монитор индексации IndexNow + Link Indexing Bot по опубликованным заметкам (по запросу).
---

# Excalibur BLOG — Монитор индексации

**Task:** `excalibur-blog-indexing-monitor`  
**Когда:** пользователь спрашивает «индексируются ли статьи», «статус индексации», «проверь бота» — **вне** основного publish-пайплайна.

## Env

```bash
export EXCALIBUR_PROJECT_ROOT=<PROJECT_ROOT>/excalibur-blog-memory
```

Credentials (для `--check-api`): `memory/site.env.local` или `site.env.local`:

- `LINK_INDEXING_BOT_API_KEY`
- `LINK_INDEXING_BOT_USER_ID`

## Shell

Vendor script (canonical — плагин `/excalibur`):

```bash
python ~/.cursor/plugins/local/excalibur/scripts/excalibur_blog_indexing_status.py \
  --project-root "$EXCALIBUR_PROJECT_ROOT" \
  --check-api
```

### Фильтры

```bash
# одна тема
.../excalibur_blog_indexing_status.py --topic-id Z12 --check-api

# один slug
.../excalibur_blog_indexing_status.py --slug konversiya-sajta-b2b-normy --check-api

# один URL
.../excalibur_blog_indexing_status.py --url "https://etodigital.ru/zametki/konversiya-sajta-b2b-normy/" --check-api

# последние N из published-articles.md
.../excalibur_blog_indexing_status.py --recent 5 --check-api
```

### Только локальные артефакты (без API)

Убери `--check-api` — читаются:

- `<article_dir>/yandex-indexing-result.json`
- `<article_dir>/link-indexing-bot-result.json`

### Проверка одной task_id вручную

```bash
python ~/.cursor/plugins/local/excalibur/scripts/excalibur_blog_link_indexing_bot.py \
  --project-root "$EXCALIBUR_PROJECT_ROOT" \
  --check-task 1675889
```

## Выход

| Файл | Назначение |
|------|------------|
| `blog/indexing-status-report.json` | machine report |
| `blog/indexing-status-report.md` | human summary |

## Rollup statuses

| Код | Значение для пользователя |
|-----|---------------------------|
| `not_submitted` | ни IndexNow, ни бот |
| `indexnow_only` | только IndexNow |
| `submitted_pending` | бот принял, API не опрашивали |
| `bot_in_progress` | task `active` |
| `bot_complete` | task `complete` |
| `bot_failed` | task `failed` |
| `bot_submit_failed` | POST /tasks/new не прошёл |

## Ответ пользователю (шаблон)

Коротко, таблицей или списком:

1. Сколько статей проверено
2. По каждой: URL, IndexNow OK?, task_id + статус бота
3. Если `not_submitted` — напомнить про `submit-post-indexing.py` после publish
4. Явно: **отправка ≠ попадание в индекс ПС** — для этого GSC / Вебмастер / `site:`

## Handoff marker

`=== EXCALIBUR BLOG INDEXING MONITOR ===`

## Запрещено

- Отправлять URL на индексацию (это publish / `submit-post-indexing.py`)
- Путать с `excalibur-blog-indexer` (interlink + llms.txt)
