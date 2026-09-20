# Dzen Adapter — контракт (Excalibur BLOG)

**Роль:** по **запросу** готовить нативную версию заметки для [Яндекс Дзен](https://dzen.ru/help/ru/index.html): **переписанный текст + картинки**.

**По умолчанию — только текст и картинки.** RSS, `dzen-feed.xml`, FTP и любая отправка в Дзен — **только если пользователь явно написал** `rss-push` / «отправь в Дзен по RSS» / «запушь ленту». Без такой фразы шаги RSS **запрещены**.

**Не входит в основной пайплайн** Research → Writer → … → Publish. Директор вызывает `Task(excalibur-blog-dzen)` только когда пользователь явно просит Дзен.

## Официальные источники (обязательны к чтению агентом)

| Документ | URL |
|----------|-----|
| Справка Дзена | https://dzen.ru/help/ru/index.html |
| RSS: разметка и подключение | https://dzen.ru/help/ru/website/rss-modify.html |
| Требования к содержанию (новости/партнёры) | https://dzen.ru/help/ru/requirements/content.html |

Внешние reference (не заменяют официальные): `shared/dzen-writing-reference.md`.

## Вход

Один из:

- `topic_id` (например `Z09`, `P90-059`)
- `slug` (например `pochemu-marketing-est-a-zayavok-net`)
- `article_dir` — `memory/blog/articles/<topic_id>-<slug>/`
- `permalink` — live URL на etodigital.ru

Обязательные файлы в `article_dir`:

- `article.html` — канон с сайта (SEO longread)
- `article.meta.json`
- `cover/cover.png` (или пути из `wp-publish-result.json`)
- Желательно: `wp-publish-result.json` с `permalink` и URL inline-картинок

Опционально из запроса пользователя (**только при явной просьбе**):

- `mode`: `rewrite-only` (**default**) | `rss-push`
- `rss_category`: `native-draft` (только для rss-push)
- `dzen_format`: `format-article` (default) | `format-post`

Если пользователь не просил RSS — **не** создавай `dzen-rss-item.xml`, **не** вызывай `excalibur_blog_dzen_rss.py`.

## Выход (`article_dir/dzen/`)

```text
dzen/
  dzen-article.html          # переписанный HTML (для копипаста в Студию или RSS позже)
  dzen-article.plain.md      # plain-text для ручной вставки
  dzen-meta.json             # title, description, char_count
  dzen-qa.md                 # PASS/BLOCKED
  dzen-images/
    cover-enclosure.jpg        # обложка ≥700px
    inline-01.jpg … inline-03.jpg
```

**Только при явном `rss-push`:**

```text
  dzen-rss-item.xml
  dzen-rss-push-result.json
  memory/blog/dzen-feed.xml    # merge feed
```

## Переписывание: сайт → Дзен

| Параметр | Сайт (Excalibur) | Дзен-версия |
|----------|------------------|-------------|
| Объём | 8 500–9 500 знаков | **5 000–5 500** (обязательно; FAIL если &lt;4800 или &gt;5600) |
| Тире | по контракту сайта | **только короткий дефис `-`** (запрещены `—`, `–`, `→` в тексте) |
| Заголовок | `meta_ab.title_seo` | `meta_ab.title_ctr` или новый крючок |
| Ссылки | много internal | **запрещены ссылки на сайт** (`etodigital.ru`, `/zametki/` и т.д.) |
| CTA | conversion map | **одна** нативная ссылка на личный Telegram из `conversion-map.md` (обычно `https://t.me/vpmarketing`) - в конце, без навязывания |
| FAQ | 5–7 пар H2/H3 | вплести 2–3 ответа в текст; без стены FAQ |
| Таблицы | допустимы | сжать или заменить списком; в постах форматирование таблиц слабое |
| Оглавление с якорями | запрещено на сайте | в Дзен RSS **можно** `h2/h3/h4` с `id` — но для feed-статей лучше без простыни |
| Тон | экспертный B2B | живее, короче абзацы (1–3 предложения), без AI-slop |

**Уникальность:** дзен-текст — **переписанный**, не копипаст `article.html`. Сохраняй факты из `fact-bank` / `research-notes`; не выдумывай метрики.

## HTML для RSS (`content:encoded`)

Только теги из [официальной таблицы](https://dzen.ru/help/ru/website/rss-modify.html):

`p`, `a`, `b`, `i`, `u`, `s`, `h1`–`h4`, `blockquote`, `ul`, `ol`, `li`, `figure`, `img`, `figcaption`, `video`/`source` (MP4), `iframe` (YouTube embed).

**Запрещено:** `div`, `span`, `style="..."`, `script`, кастомные классы для вёрстки, `<table>` (лучше списки — таблицы в RSS Дзена не в whitelist).

Изображения:

- Формат: JPEG, PNG, GIF
- **Минимальная ширина 700 px**
- Обложка: `<enclosure url="..." type="image/jpeg"/>` + первое `<figure><img>…</figure>` в теле
- Несколько картинок подряд — через `<figure>`, не голые `<img>` подряд

## RSS `<item>` (минимум)

```xml
<item>
  <title>Заголовок (дублировать h1 в content)</title>
  <link>https://etodigital.ru/zametki/slug/</link>
  <guid>stable-uuid-or-post-id</guid>
  <pubDate>Wed, 19 Jun 2026 12:00:00 +0300</pubDate>
  <category>native-draft</category>
  <category>format-article</category>
  <category>index</category>
  <category>comment-all</category>
  <enclosure url="https://.../cover.jpg" type="image/jpeg"/>
  <description>Краткое описание для карточки</description>
  <content:encoded><![CDATA[...]]></content:encoded>
</item>
```

Правила:

- URL без UTM
- Повторная отправка — тот же `guid`
- Не дублировать старьё: в ленту только свежие материалы
- После ручной правки в Студии — RSS-обновления для этого `guid` могут не применяться

## Режимы запроса

| Режим | Когда | Действие |
|-------|-------|----------|
| **`rewrite-only` (default)** | «перепиши для дзена», «текст и картинки» | `dzen-article.*` + `dzen-images/` + `dzen-qa.md` |
| **`rss-push`** | **только** явная просьба пользователя | + RSS item, merge feed, FTP |

Без слов «rss», «лента», «запушь в дзен» — работай как `rewrite-only`.

## Blockers

| Код | Причина |
|-----|---------|
| `❌ DZEN INPUT BLOCKER` | нет article_dir / article.html |
| `❌ DZEN REWRITE BLOCKER` | объём вне 4800–5600, slop, копипаст &gt;40% с сайтом |
| `❌ DZEN LINK BLOCKER` | есть ссылка на сайт; больше одной ссылки; ссылка не Telegram |
| `❌ DZEN TYPO BLOCKER` | в тексте `—`, `–` или `→` вместо короткого `-` |
| `❌ DZEN HTML BLOCKER` | теги вне whitelist |
| `❌ DZEN IMAGE BLOCKER` | нет cover или ширина <700px |
| `❌ DZEN RSS BLOCKER` | нет `PUBLIC_SITE_URL`, невалидный item XML |
| `❌ DZEN PUSH BLOCKER` | FTP/feed path не настроен |

## Handoff marker

`=== EXCALIBUR BLOG DZEN ===`

## Env (`site.env.local`)

```env
# Дзен RSS (опционально)
DZEN_RSS_ENABLED=no
DZEN_RSS_FEED_PATH=/etodigital.ru/public_html/feed/dzen.xml
DZEN_RSS_CHANNEL_TITLE=Ето Digital — заметки
DZEN_RSS_DEFAULT_CATEGORY=native-draft
DZEN_RSS_DEFAULT_FORMAT=format-article
DZEN_RSS_DEFAULT_INDEX=index
```

## Кто чем не занимается

| Роль | Запрещено |
|------|-----------|
| excalibur-blog-dzen | менять канон `article.html`, WP publish, git |
| excalibur-blog-writer | писать dzen-версию в основном пайплайне |
