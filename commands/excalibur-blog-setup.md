---
description: Excalibur BLOG — интерактивная инициализация и настройка проекта.
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

# Excalibur BLOG — Настройка проекта

Выполните эту команду, чтобы инициализировать проект, заполнить бриф бизнеса и настроить безопасный ENV-файл доступов.

## Запуск в терминале:

```bash
python scripts/excalibur_blog_setup.py
```

## Что произойдет:
1. Вы увидите приветственное сообщение и ASCII-арт.
2. Мастер спросит у вас информацию о вашем блоге: название, полный URL, нишу и целевую аудиторию.
3. Эти данные будут автоматически записаны в бриф `memory/brief/site-brief.md`.
4. Мастер попросит указать данные интеграции для WordPress (хост, порт, логин и пароль FTP).
5. Эти секретные данные будут безопасно сохранены в локальный файл `memory/site.env.local` (он скрыт от коммитов и git-системы через `.gitignore`).
6. Будет выведен список дальнейших шагов для запуска генерации первой статьи.
