# Dzen writing — внешние reference (не заменяют официальную справку)

Официальный источник: https://dzen.ru/help/ru/index.html · RSS: https://dzen.ru/help/ru/website/rss-modify.html

## Паттерны с GitHub / сообществ (borrowed)

### 1. openclaw/skills — `dzen` publisher

- Репозиторий: https://github.com/openclaw/skills (skill `ruslanlanket/dzen`)
- Суть: публикация через **сессию браузера** (Cookie + `x-csrf-token`), т.к. публичного API нет
- Медиа: jpg/png/webp/gif, mp4
- **Для Excalibur:** используем как fallback «ручная Студия»; основной путь — RSS + `native-draft`

### 2. arctic-hare/dzen-rss

- https://github.com/arctic-hare/dzen-rss
- TypeScript-библиотека RSS под [официальную разметку](https://dzen.ru/help/ru/website/rss-modify.html)
- Категории item: `native-draft`, `format-article`, `noindex`, `comment-all`
- **Для Excalibur:** эталон структуры XML; наш `excalibur_blog_dzen_rss.py` повторяет контракт

### 3. why-me-why-not/yandexzen-post-articles

- https://github.com/why-me-why-not/yandexzen-post-articles
- Selenium: `title`, `text_block`, `photo`, `hashtags`
- **Для Excalibur:** не в MVP; при необходимости автопоста без RSS

### 4. xxniiinxx/ai-social-media-post-automation

- Адаптерная архитектура под платформы (в т.ч. заготовка Dzen)
- **Для Excalibur:** паттерн `PlatformAdapter` — наш `dzen-adapter` = отдельный слой после publish

## Практики ленты Дзена (эвристики, не из ТОС)

Использовать при переписывании; при конфликте с [требованиями Дзена](https://dzen.ru/help/ru/requirements/content.html) — побеждают требования.

1. **Первые 2 строки** — ответ «зачем читать»; без вводных «сегодня поговорим о…»
2. **Абзац ≤3 предложения** — мобильное дочитывание
3. **Картинка каждые 800–1200 знаков** — из `cover/` quad или WP inline URLs
4. **Заголовок** — конкретная боль/цифра/вопрос; без кликбейта-обмана (официально запрещён misleading)
5. **Ссылка на сайт** — один раз в конце, не в каждом абзаце (внешние ссылки режут охват)
6. **Хештеги** (при ручной публикации) — 3–5 по нише, не спам
7. **Пост vs статья** (автоконвертация RSS):
   - &lt;800 знаков без картинок → пост
   - &lt;600 знаков + до 10 картинок → пост
   - иначе → статья

## Reddit / обсуждения (speculation)

Точных «skills» на Reddit мало; типичные советы авторов:

- Не гонять 1:1 SEO-текст — Дзен считает дубль
- Нативный материал с уникальным лидом лучше RSS-автопоста
- Тестировать `native-draft` → правка в Студии → publish

## Связь с Excalibur site contract

Сайт уже RSS-safe (`excalibur-article-writing-contract.md`). **Dzen-adapter всё равно переписывает**, потому что:

- объём SEO longread избыточен для ленты;
- FAQ и fact-check blockquote на сайте избыточны для Дзена;
- заголовок CTR ≠ SEO title.
