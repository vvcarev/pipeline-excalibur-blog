---
name: dzen-excalibur-blog
description: |
  По запросу — нативная версия заметки для Яндекс Дзен: переписанный текст, картинки ≥700px, RSS item; опционально push в dzen-feed.xml.
---

# Dzen Adapter — Excalibur BLOG

**Язык:** русский. **Только по запросу** — не шаг пайплайна Writer/Publish.

## Роль

Субагент `excalibur-blog-dzen` готовит **отдельную** версию статьи с сайта для [Дзена](https://dzen.ru/help/ru/index.html):

1. Переписать текст под ленту (объём, крючок, абзацы, ссылки)
2. Собрать обложку + inline-картинки (≥700 px)
3. Провалидировать HTML по whitelist Дзена
4. **Только по явной просьбе:** RSS item / push в ленту

**Не меняет** канон `article.html` и не трогает WP.

## Обязательно прочитай

1. `agents/excalibur-blog-dzen.md`
2. `shared/dzen-adapter-contract.md`
3. `shared/dzen-writing-reference.md`
4. [Разметка RSS Дзена](https://dzen.ru/help/ru/website/rss-modify.html)
5. Исходники: `article.html`, `article.meta.json`, `research-notes.md`, `wp-publish-result.json`
6. `shared/excalibur-article-writing-contract.md` — только факты/тон, не копировать структуру

## Вход (от Директора / пользователя)

| Параметр | Пример |
|----------|--------|
| `topic_id` | Z09, P90-059 |
| `slug` | pochemu-marketing-est-a-zayavok-net |
| `mode` | `rewrite-only` (**default** — только текст+картинки), `rss-push` (**только если пользователь явно просил**) |
| `dzen_format` | `format-article` (default), `format-post` |

## Workflow

### 1. Resolve article_dir

```bash
export EXCALIBUR_PROJECT_ROOT=<PROJECT_ROOT>/excalibur-blog-memory
python3 scripts/excalibur_blog_dzen_adapter.py --topic-id Z09 --resolve-only
```

Или `--slug`, `--permalink`, `--article-dir`.

### 2. Прочитать канон

- `article.html` — **не копировать**; извлечь факты, H2-смысл, CTA
- `article.meta.json` — `title_ctr`, `description_ctr`, `primary_query`
- `wp-publish-result.json` — `permalink`, inline image URLs если есть
- `cover/cover.png`, `cover/inline-*.png`

### 3. Написать `dzen/dzen-article.html`

Правила — `shared/dzen-adapter-contract.md`:

- `<h1>` = заголовок для ленты (из `title_ctr` или новый)
- Лид 2-3 предложения, **только короткий дефис `-`**
- Один `<blockquote>` с TL;DR
- **7 секций `<h2>`** (все разрывы из канона) + короткие `<p>`
- 1-5 `<figure><img>…</figure>` (абсолютные HTTPS URL картинок)
- **Запрещены ссылки на сайт.** Одна ссылка в конце - личный Telegram из `memory/brief/conversion-map.md` (`https://t.me/vpmarketing`), нативно
- Объём: **5 000-5 500** знаков без HTML (FAIL если &lt;4800 или &gt;5600)
- `dzen-article.plain.md` = **полный** текст (не конспект), зеркало html без тегов

**URL картинок в HTML:** абсолютные HTTPS (из WP upload или будущие `dzen-images/` после prepare).

### 4. Plain fallback

`dzen/dzen-article.plain.md` — тот же текст без тегов (для ручной вставки в Студию).

### 5. Mechanical prepare + validate

```bash
python3 scripts/excalibur_blog_dzen_adapter.py \
  --article-dir memory/blog/articles/Z09-pochemu-marketing-est-a-zayavok-net \
  --prepare-images \
  --validate
```

Создаёт `dzen-images/`, `dzen-meta.json`, проверяет whitelist и ширину картинок.

### 6. Similarity check (анти-копипаст)

```bash
python3 scripts/excalibur_blog_dzen_adapter.py \
  --article-dir ... \
  --similarity-check
```

FAIL если >40% совпадения n-грамм с `article.html`.

### 7. QA markdown

`dzen/dzen-qa.md`:

- чеклист требований Дзена (объём, картинки, ссылки, запрещённый контент)
- similarity score
- verdict PASS / BLOCKED

### 8. QA markdown

`dzen/dzen-qa.md` — verdict PASS / BLOCKED.

### 9. RSS (⛔ только если пользователь явно просил rss-push)

```bash
python3 scripts/excalibur_blog_dzen_rss.py --topic-id Z09 --write-item
# merge-feed / push-ftp — только после явной просьбы
```

**Без явной просьбы шаги 9 не выполнять.**

### 10. Handoff

Блок `=== EXCALIBUR BLOG DZEN ===`:

- topic_id, slug, permalink
- `dzen-meta.json` summary
- verdict
- пути к `dzen-article.html`, `dzen-rss-item.xml`
- если push — `dzen-rss-push-result.json`

## Blockers

См. `shared/dzen-adapter-contract.md`. При BLOCKED — не делать `rss-push`.

## Запреты

- Не править `article.html`
- Не запускать вложенные Task
- Не пушить RSS и не создавать `dzen-rss-item.xml` без **явной** просьбы пользователя
- Не выдумывать факты вне research/fact-bank

## Fragment

Опционально: `.cursor/excalibur-blog-fragments/dzen.md` с маркером `=== EXCALIBUR BLOG DZEN ===`
