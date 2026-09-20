---
description: Excalibur BLOG — git commit + push develop (allowlist) после publish/plan/repair.
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

# Git sync Excalibur → GitHub

Плагин: `~/.cursor/plugins/local/excalibur/`  
Субагент: **`Task(excalibur-blog-git-sync)`**  
Skill: `skills/git-excalibur-blog/SKILL.md`

## Когда вызывать

- После publish статьи (автоматически — шаг ⑧ пайплайна)
- После обновления plan-90 / progress / editorial calendar
- «Закоммить и запушь excalibur»
- После category-guard / indexing artifacts

Директор **не** делает git сам — только Task git-sync.

## Пример промпта

```text
Ты excalibur-blog-git-sync.
trigger: publish. topic_id P90-059, article_dir из handoff.
Dry-run → stage allowlist → commit develop → push origin develop.
Блок === EXCALIBUR BLOG GIT SYNC ===. Не коммить site.env.local.
```

## Параметры

| Параметр | Пример |
|----------|--------|
| `trigger` | publish, plan, repair, manual |
| `topic_id` | P90-059 |
| `push` | yes (default) / no |
| `branch` | develop (default) |

## Не путать

| Агент | Роль |
|-------|------|
| `excalibur-blog-publish` | WP live |
| `excalibur-blog-git-sync` | **GitHub** develop |
