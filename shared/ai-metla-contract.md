# AI Метла — контракт очистки изображений Excalibur BLOG

Сервис: [AI Метла](https://mcp-kv.ru/ai-delete/) (mcp-kv.ru).

## Когда запускать

**Обязательно** после шага ④a Cover (quad split + inject), **до** ⑤ Indexer.

Порядок:

```text
④a Cover (MCP → split → inject)
④c AI Metla (очистка всех PNG)
④b Schema (может идти параллельно с ④a; Indexer ждёт ④a + ④c + ④b)
```

## Какие файлы

| Файл | Обязательно |
|------|-------------|
| `cover/cover.png` | да |
| `cover/inline-01.png` … `inline-03.png` | да |
| `cover/canvas-quad.png` | опционально (`--include-canvas`) |

## Скрипт

```bash
python scripts/excalibur_blog_ai_metla.py \
  --article-dir memory/blog/articles/<topic_id>-<slug>
```

Dry-run:

```bash
python scripts/excalibur_blog_ai_metla.py --article-dir ... --dry-run
```

## API

**Предпочтительно:** прямой upload файла:

```bash
curl -fsSL -X POST "https://mcp-kv.ru/ai-delete/api/clean" \
  -H "X-API-Key: $AI_DELETE_API_KEY" \
  -F "file=@cover/cover.png" \
  -F "title=..." -F "author=..." -F "copyright=..." \
  -F "software=Adobe Photoshop" -F "description=..." -F "keywords=..."
```

Ответ — бинарный PNG/JPEG (перезаписать исходный файл).

**Альтернатива (URL):** `POST /api/clean-url` + `GET /api/download/{id}` — если файл уже на публичном HTTPS.

Поля SEO (из `article.meta.json`):

- `title` — H1
- `author` — Виктор Прокопчук
- `copyright` — © Eto Digital
- `software` — Adobe Photoshop
- `description`, `keywords`

## Секреты

В `memory/site.env.local` (gitignore):

```env
AI_DELETE_API_KEY=
```

Алиасы: `AI_METLA_API_KEY`, `MCP_KV_AI_DELETE_KEY`.

**Никогда** не коммитить ключ в репозиторий, handoff, PR.

## Выход

`cover/ai-metla-report.json`:

```json
{
  "verdict": "PASS",
  "service": "mcp-kv-ai-delete",
  "files": [{ "file": "cover.png", "status": "PASS", "bytes": 123456 }]
}
```

## Blockers

| Статус | Причина |
|--------|---------|
| `❌ AI METLA BLOCKER` | нет API key |
| `❌ AI METLA BLOCKER` | нет PNG после cover |
| `❌ AI METLA FAIL` | API/сеть/timeout |

Без PASS **не** запускать Publish.

## Субагент

`Task(excalibur-blog-ai-metla)` · skill `ai-metla-excalibur-blog` · fragment `=== EXCALIBUR BLOG AI METLA ===`
