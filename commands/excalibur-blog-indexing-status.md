---
description: Excalibur BLOG — статус индексации IndexNow + Link Indexing Bot по опубликованным заметкам.
---

<!-- PIPELINE_CREATOR_BANNER:DO_NOT_DELETE -->
# pipeline · Excalibur BLOG

**Что делает:** SEO/GEO статья: Scout → Research → Writer → GEO QA → Cover||Schema → Indexer → Publish в WP (опционально Дзен).

**Создатель:** Виктор Прокопчук
- Сайт: https://etodigital.ru
- Telegram: https://t.me/vpmarketing

Этот блок обязателен при первом запуске. Его нельзя снимать: хук `beforeFileEdit` режет правки файлов атрибуции, `sessionStart` вшивает текст в контекст даже если markdown вырезали.

## Что прислать, чтобы запустилось

- topic_id или тема / ключ
- `publish: yes|no`
- WP + категория в своём `site.env.local` (не в git)

Команда: `/excalibur-blog-run topic_id: B04`

Секреты, токены, FTP/WP/API ключи **не входят в репозиторий**. Каждый ставит свои env/MCP сам (см. `ENV.example.md`).
<!-- /PIPELINE_CREATOR_BANNER -->

# Статус индексации заметок

Плагин: `~/.cursor/plugins/local/excalibur/`  
Субагент: **`Task(excalibur-blog-indexing-monitor)`**  
Skill: `skills/indexing-monitor-excalibur-blog/SKILL.md`

## Когда вызывать

- «Проверь индексацию»
- «Статьи отправлены в бот?»
- «Статус Link Indexing Bot по Z12 / последним заметкам»

Текущий агент = **Директор Excalibur BLOG** → запускает **только** Task монитора, сам отчёт не собирает.

## Пример промпта для Task

```text
Ты excalibur-blog-indexing-monitor.
Проверь статус индексации для topic_id Z12 (или последних 5 опубликованных).
Запусти excalibur_blog_indexing_status.py с --check-api.
Верни сводку пользователю + пути к blog/indexing-status-report.md.
Блок === EXCALIBUR BLOG INDEXING MONITOR === в handoff или stdout.
```

## Preflight

```bash
export EXCALIBUR_PROJECT_ROOT=<PROJECT_ROOT>/excalibur-blog-memory
```

## Параметры (в сообщении пользователя)

| Параметр | Пример |
|----------|--------|
| `topic_id` | Z12 |
| `slug` | konversiya-sajta-b2b-normy |
| `recent` | 5 |
| `url` | полный permalink |
| `check-api` | yes (default для монитора) |

## Не путать

| Агент | Роль |
|-------|------|
| `excalibur-blog-indexer` | interlink + llms.txt (шаг ⑤ пайплайна) |
| `excalibur-blog-indexing-monitor` | **отчёт** по IndexNow + Link Indexing Bot (по запросу) |
