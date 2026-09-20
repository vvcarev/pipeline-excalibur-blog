---
name: category-excalibur-blog
description: Excalibur BLOG Category Guard — wp_category в meta, SSH assign, verify не «Без рубрики».
---

# Excalibur BLOG — Category Guard (⑦)

**Роль:** `Task(excalibur-blog-category)`  
**Когда:** сразу после ⑥ Publish, **до** индексации и `PIPELINE DONE`.

## Контракт

`shared/wp-categories-etodigital.md`

## Preconditions

- `wp-publish-result.json` → `verdict: pass`, `post_id` или parse из `raw_output`
- `article.meta.json` с `cluster` и/или `wp_category`
- `memory/site.env.local` — SSH + FTP_ROOT

## Алгоритм

### 1. Meta guard (Writer fallback)

```bash
python -c "
from pathlib import Path
from excalibur_blog_category import ensure_meta_has_category
print(ensure_meta_has_category(Path('memory/blog/articles/<dir>')))
"
```

Или из корня vendor/scripts:

```bash
cd scripts && python3 -c "from excalibur_blog_category import ensure_meta_has_category; ..."
```

Проще — assign-скрипт сам вызывает `ensure_meta_has_category`.

### 2. Assign + verify

```bash
python scripts/excalibur_blog_assign_category.py \
  --post-id <WP_POST_ID> \
  --article-dir memory/blog/articles/<topic_id>-<slug>
```

**mysite etodigital** (эквивалент):

```bash
python scripts/etodigital/assign-excalibur-post-category.py \
  --post-id <WP_POST_ID> \
  --article-dir excalibur-blog-memory/blog/articles/<topic_id>-<slug>
```

### 3. Verify-only (retry)

```bash
python scripts/excalibur_blog_assign_category.py \
  --post-id <ID> --article-dir <dir> --check-only
```

Gate: `categories` содержит ожидаемый slug, **нет** `bez-rubriki` / `uncategorized`.

### 4. Артефакты

- `category-guard-result.json` — `verdict: PASS|FAIL`
- Handoff: `=== EXCALIBUR BLOG CATEGORY ===`
- `published-articles.md` — колонка category (если ещё не заполнена)

### 5. Handoff block

```text
=== EXCALIBUR BLOG CATEGORY ===
topic_id:
post_id:
wp_category:
categories_live:
verdict: PASS|FAIL
category-guard-result: memory/blog/articles/.../category-guard-result.json
```

## Blockers

- `❌ CATEGORY BLOCKER` — assign fail, verify fail, forbidden slug
- Без PASS **не** закрывать `PIPELINE DONE` при `publish=yes`

## Не твоя зона

- Писать/редактировать article.html
- Publish с нуля (post уже есть)
- Cover, schema, indexer

## Связь с Writer

Writer **обязан** записать `wp_category` в `article.meta.json` (из `cluster` или plan JSON). Category guard — страховка и live verify.
