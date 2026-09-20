---
description: Excalibur BLOG — полный прогон статьи через оркестратор и субагентов.
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

# Excalibur BLOG — запуск пайплайна

Откройте workspace с плагином **EXCALIBUR** и выполните команду или напишите:

«Запусти Excalibur BLOG для темы **B01**»

## Параметры

- `topic_id`: B01 | B02 | B03 | all | P0-only (если не указан — Scout подбирает следующую P0)
- `publish`: yes | no (**default: yes** — публикация автоматически после Indexer)

### Правило publish (обязательно для директора)

1. **По умолчанию** после шага ⑤ Indexer директор **обязан** запустить шаг ⑥ `Task(excalibur-blog-publish)`.
2. Пропуск publish **только** при явном `publish: no` / «без публикации» / «draft only».
3. Субагент: `excalibur-blog-publish` + skill `publish-excalibur-blog/SKILL.md`.
4. Если `EXCALIBUR_BLOG_ALLOW_PUBLISH != yes` в `memory/site.env.local` — publish-агент возвращает `❌ PUBLISH BLOCKER` (шаг выполнен, не silent skip).

Примеры:

```text
/excalibur-blog-run topic_id: B04
/excalibur-blog-run topic_id: B04 publish: yes
/excalibur-blog-run topic_id: B04 publish: no
```

## Пайплайн (7 субагентов + директор)

```text
Scout → Research → Writer → GEO QA → Cover||Schema → Indexer → Publish (auto)
```

## Оркестратор

Директор — **основной агент чата** (не Task). Сценарий: [skills/director-excalibur-blog/SKILL.md](../skills/director-excalibur-blog/SKILL.md).

Handoff: `shared/excalibur-blog-handoff.md`
