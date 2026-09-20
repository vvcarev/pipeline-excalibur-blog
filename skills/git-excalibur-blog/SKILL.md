---
name: git-excalibur-blog
description: Excalibur BLOG Git Sync — allowlist stage, commit develop, push GitHub после publish/plan/repair.
---

# Excalibur BLOG — Git Sync (⑧)

**Task:** `excalibur-blog-git-sync`  
**Команда:** `/excalibur-blog-git-sync`  
**Когда:** после publish-пайплайна (category PASS) или при изменениях plan-90 / правках Excalibur.

## Контракт

`shared/excalibur-git-sync-contract.md`

## Env

```bash
export EXCALIBUR_PROJECT_ROOT=<PROJECT_ROOT>/excalibur-blog-memory
export MYSITE_ROOT=<PROJECT_ROOT>   # git root, default workspace
```

## Preflight (обязательно)

```bash
cd "$MYSITE_ROOT"
git status
git branch --show-current   # expect develop

python ~/.cursor/plugins/local/excalibur/scripts/excalibur_blog_git_sync.py \
  --workspace-root "$MYSITE_ROOT" \
  --trigger publish \
  --topic-id P90-059 \
  --slug prodajushchij-sajt-chto-eto \
  --wp-category sajt \
  --article-dir excalibur-blog-memory/blog/articles/P90-059-prodajushchij-sajt-chto-eto \
  --dry-run
```

## Stage (только allowlist)

```bash
python ~/.cursor/plugins/local/excalibur/scripts/excalibur_blog_git_sync.py \
  --workspace-root "$MYSITE_ROOT" \
  --trigger publish \
  --topic-id P90-059 \
  --slug prodajushchij-sajt-chto-eto \
  --article-dir excalibur-blog-memory/blog/articles/P90-059-prodajushchij-sajt-chto-eto \
  --stage
```

Запрещено: `git add -A`, `git add .`, stage `site.env.local`.

## Commit

```bash
git commit -m "$(cat <<'EOF'
feat(excalibur): publish P90-059 — prodajushchij-sajt-chto-eto

post_id 3040, category sajt, IndexNow + Link Indexing Bot artifacts.
EOF
)"
```

Триггеры subject — см. contract.

## Push

```bash
git push origin develop
```

PR в `main` — только если пользователь явно просит и есть `gh`.

## Triggers

| trigger | Когда | Что stage |
|---------|--------|-----------|
| `publish` | после ⑥⑦ + индексация | article_dir, published-articles, plan-90-progress |
| `plan` | rebuild plan-90, calendar | research/semantic-core-runs, EXCALIBUR-ARTICLES-90.json |
| `category` | только category-guard | category-guard-result.json, meta wp_category |
| `repair` | QA/publish fix без новой темы | затронутые файлы в allowlist |
| `manual` | пользователь `/excalibur-blog-git-sync` | по dry-run |

## Выход

| Файл | Назначение |
|------|------------|
| `git-sync-report.json` | machine report |
| handoff | `=== EXCALIBUR BLOG GIT SYNC ===` |

## Handoff block

```text
=== EXCALIBUR BLOG GIT SYNC ===
trigger: publish
topic_id: P90-059
commit: <sha>
branch: develop
pushed: yes|no
files_staged: N
verdict: PASS|SKIP|BLOCKER
report: excalibur-blog-memory/blog/git-sync-report.json
```

## Verdict

- **PASS** — commit (+ push если не запрещено)
- **SKIP** — нет allowlisted changes
- **BLOCKER** — secrets, forbidden paths, push fail

## Запрещено

- Коммитить `site.env.local`, `.env`, credentials
- Force push, amend чужих коммитов
- Stage theme/vendor/plugin paths вне allowlist
- Пушить в `main` без запроса
