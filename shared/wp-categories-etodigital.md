# Excalibur BLOG — рубрики WordPress (etodigital.ru)

## Правило

**Пост без рубрики на live недопустим.** «Без рубрики» / `bez-rubriki` / `uncategorized` = **CATEGORY BLOCKER**.

## Допустимые slug

| slug | Название | Когда |
|------|----------|-------|
| `sajt` | Сайт | конверсия, сайт под ключ, заявки с сайта |
| `marketing` | Маркетинг | SEO, GEO, Директ, контент, аудит, B2B-ниша (default) |
| `lidy` | Лиды | лидогенерация, CRM, воронка |
| `oshibki` | Ошибки | ошибки маркетинга |
| `smm` | SMM | мессенджеры, соцсети |
| `depjoy` | Деплой | редко, тех/деплой темы |

Маппинг cluster → slug: `scripts/excalibur_blog_category.py` (`CLUSTER_TO_CATEGORY`).

## Контракт артефактов

1. **Writer** пишет в `article.meta.json`:
   - `cluster` (из plan)
   - `wp_category` (resolved slug, обязательно до publish)

2. **Publish** передаёт `category_slug` в bootstrap PHP (`excalibur_blog_wp_publish.py`).

3. **Category guard (⑦)** после publish:
   ```bash
   python scripts/excalibur_blog_assign_category.py \
     --post-id <wp_post_id> \
     --article-dir memory/blog/articles/<topic_id>-<slug>
   ```
   Выход: `category-guard-result.json` с `verdict: PASS|FAIL`.

4. **mysite (etodigital):** тонкая обёртка `scripts/etodigital/assign-excalibur-post-category.py` — тот же контракт.

## Пайплайн

```text
⑥ publish → ⑦ excalibur-blog-category → indexing (в publish или отдельно)
```

Handoff маркер: `=== EXCALIBUR BLOG CATEGORY ===`

## Blockers

| Статус | Причина |
|--------|---------|
| `❌ CATEGORY BLOCKER` | нет post_id, SSH fail, slug пустой или bez-rubriki после assign |
| `❌ CATEGORY META BLOCKER` | Writer не записал wp_category и cluster не в маппинге |
