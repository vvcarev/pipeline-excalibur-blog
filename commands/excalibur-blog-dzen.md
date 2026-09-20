---
description: Excalibur BLOG — нативная версия заметки для Яндекс Дзен (текст + картинки + опционально RSS).
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

# Дзен-адаптер заметки

Плагин: `~/.cursor/plugins/local/excalibur/`  
Субагент: **`Task(excalibur-blog-dzen)`**  
Skill: `skills/dzen-excalibur-blog/SKILL.md`  
Контракт: `shared/dzen-adapter-contract.md`

## Когда вызывать

- «Перепиши Z09 под Дзен с картинками» → **только** текст + `dzen-images/`
- «Отправь в Дзен по RSS» → **только тогда** `rss-push`

**Не** запускается автоматически после Publish.

## Пример промпта для Task

```text
Ты excalibur-blog-dzen.
topic_id: Z09
mode: rewrite-only
Прочитай agents/excalibur-blog-dzen.md + skills/dzen-excalibur-blog/SKILL.md + shared/dzen-adapter-contract.md.
Официальные правила: https://dzen.ru/help/ru/website/rss-modify.html
1) resolve article_dir
2) перепиши dzen/dzen-article.html (5000-5500 знаков, дефис `-`, без ссылок на сайт, 1x Telegram в конце)
3) excalibur_blog_dzen_adapter.py --prepare-images --validate --similarity-check
4) dzen-qa.md
5) Блок === EXCALIBUR BLOG DZEN === в handoff
# RSS (write-item / merge-feed) — ТОЛЬКО если пользователь явно просил rss-push
```

### С RSS-push

```text
mode: rss-push
DZEN_RSS_ENABLED=yes в site.env.local
После write-item: excalibur_blog_dzen_rss.py --merge-feed --push-ftp
```

## Preflight

```bash
export EXCALIBUR_PROJECT_ROOT=<PROJECT_ROOT>/excalibur-blog-memory
```

## Параметры

| Параметр | Пример |
|----------|--------|
| `topic_id` | Z09, P90-059 |
| `slug` | pochemu-marketing-est-a-zayavok-net |
| `permalink` | https://etodigital.ru/zametki/.../ |
| `mode` | `rewrite-only` (default), `draft`, `rss-push` |
| `dzen_format` | `format-article`, `format-post` |

## Выход

`excalibur-blog-memory/blog/articles/<topic>-<slug>/dzen/`

## Env (опционально RSS)

См. `site.env.local.example` — блок `DZEN_RSS_*`.

## Не путать

| Агент | Роль |
|-------|------|
| `excalibur-blog-writer` | SEO longread на сайт |
| `excalibur-blog-dzen` | **по запросу** — Дзен-версия + RSS |
