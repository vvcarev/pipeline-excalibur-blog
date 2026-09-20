# Excalibur BLOG — Git sync contract

Субагент: **`Task(excalibur-blog-git-sync)`** · skill `git-excalibur-blog`  
Когда: **⑧** после publish-пайплайна (category PASS + индексация) или **по запросу** (обновление plan-90, правки без live publish).

## Ветка

- Default: **`develop`**
- Push: `git push origin develop`
- PR в `main` — только если пользователь явно просит и установлен `gh`

## Коммитить (allowlist)

| Путь | Когда |
|------|--------|
| `excalibur-blog-memory/blog/articles/<topic_id>-<slug>/` | publish / repair статьи |
| `excalibur-blog-memory/blog/*.txt`, `blog/wp-publish-log.md` | llms, журнал |
| `excalibur-blog-memory/published-articles.md` | после publish |
| `excalibur-blog-memory/plan-90-*.json`, `plan-90-handoff.md` | progress plan-90 |
| `excalibur-blog-memory/EXCALIBUR-ARTICLES-90.json`, `EXCALIBUR-PLAN-90-FINAL.md` | реген plan |
| `excalibur-blog-memory/topics/blog-topics.md` | scout / правки тем |
| `research/semantic-core-runs/etodigital-zametki-*/` | plan builder, editorial calendar |
| `scripts/etodigital/excalibur*.py`, `assign-excalibur*.py`, `submit-post-indexing.py` | tooling |
| `.cursor/rules/excalibur-etodigital.mdc` | handoff rule |
| `shared/etodigital/wp-categories-excalibur.md` | category contract |
| `docs/roadmap.md` | только если менялись пункты Excalibur |

## Никогда не коммитить

- `**/site.env.local`, `**/.env*`, credentials
- `.playwright-mcp/`, `.cursor/excalibur-blog-handoff.md` (runtime)
- `excalibur-blog-memory/memory/` — дубликат symlink; канон `excalibur-blog-memory/blog/`
- Случайный untracked мусор (картинки в корне, theme ZIP, AURA drafts) — **не** `git add -A`

## Сообщения коммита

| trigger | Шаблон |
|---------|--------|
| `publish` | `feat(excalibur): publish {topic_id} — {slug}` |
| `plan` | `chore(excalibur): update plan-90 progress / EXCALIBUR-ARTICLES-90` |
| `category` | `fix(excalibur): category guard {topic_id} → {wp_category}` |
| `repair` | `fix(excalibur): repair {topic_id} — {кратко}` |
| `manual` | `chore(excalibur): {описание от пользователя}` |

Body (опционально): post_id, permalink, category, indexing task_ids.

## Артефакты

- `git-sync-report.json` — в `excalibur-blog-memory/blog/` или в `article_dir`
- Handoff: `=== EXCALIBUR BLOG GIT SYNC ===`

## Verdict

- **PASS** — commit + push на develop успешны, секретов в staged нет
- **SKIP** — нет изменений в allowlist
- **BLOCKER** — forbidden file в staged, не git repo, push fail, пользователь запретил push

## Mysite

Workspace root = корень репозитория `mysite`.  
Preflight: `python ~/.cursor/plugins/local/excalibur/scripts/excalibur_blog_git_sync.py --dry-run`
