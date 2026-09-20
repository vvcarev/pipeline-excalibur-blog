# Excalibur BLOG — субагенты и распределение задач

Полная карта: [shared/pipeline-task-map.md](../shared/pipeline-task-map.md)

## Директор (не Task)

| | |
|-|-|
| **Файл** | [excalibur-blog-director.md](excalibur-blog-director.md) |
| **Skill** | [director-excalibur-blog](../skills/director-excalibur-blog/SKILL.md) |
| **Задача** | shell preflight, запуск Task, перенос fragments, финальный статус |

## 9 субагентов пайплайна + 2 по запросу (Task)

|| # | `Task(name)` | Роль | agent | skill |
|---|---|--------------|------|-------|-------|
|| 🔍 | `excalibur-blog-scout` | Разведка трендов и подбор тем | [scout](excalibur-blog-scout.md) | [scout-excalibur-blog](../skills/scout-excalibur-blog/SKILL.md) |
|| ① | `excalibur-blog-research` | Research, SERP, факты | [research](excalibur-blog-research.md) | [excalibur-research](../skills/excalibur-research/SKILL.md) |
| ② | `excalibur-blog-writer` | Longread HTML + meta | [writer](excalibur-blog-writer.md) | [writer-excalibur-blog](../skills/writer-excalibur-blog/SKILL.md) |
| ③ | `excalibur-blog-geo-qa` | QA-скрипты, PASS | [geo-qa](excalibur-blog-geo-qa.md) | [excalibur-geo-qa](../skills/excalibur-geo-qa/SKILL.md) |
| ④a | `excalibur-blog-cover` | ONE MCP quad i2i + inline | [cover](excalibur-blog-cover.md) | [cover-excalibur-blog](../skills/cover-excalibur-blog/SKILL.md) |
| ④b | `excalibur-blog-schema` | JSON-LD schema | [schema](excalibur-blog-schema.md) | [schema-excalibur-blog](../skills/schema-excalibur-blog/SKILL.md) |
| ⑤ | `excalibur-blog-indexer` | Interlink + llms | [indexer](excalibur-blog-indexer.md) | [indexer-excalibur-blog](../skills/indexer-excalibur-blog/SKILL.md) |
| ⑥ | `excalibur-blog-publish` | WP publish (post, featured, inline, schema) | [publish](excalibur-blog-publish.md) | [publish-excalibur-blog](../skills/publish-excalibur-blog/SKILL.md) |
| ⑦ | `excalibur-blog-category` | WP рубрика assign + verify | [category](excalibur-blog-category.md) | [category-excalibur-blog](../skills/category-excalibur-blog/SKILL.md) |
| ⑧ | `excalibur-blog-git-sync` | Git commit + push develop (allowlist) | [git-sync](excalibur-blog-git-sync.md) | [git-excalibur-blog](../skills/git-excalibur-blog/SKILL.md) |
| — | `excalibur-blog-indexing-monitor` | **По запросу:** IndexNow + Link Indexing Bot | [indexing-monitor](excalibur-blog-indexing-monitor.md) | [indexing-monitor-excalibur-blog](../skills/indexing-monitor-excalibur-blog/SKILL.md) |
| — | `excalibur-blog-dzen` | **По запросу:** Дзен текст + картинки + RSS | [dzen](excalibur-blog-dzen.md) | [dzen-excalibur-blog](../skills/dzen-excalibur-blog/SKILL.md) |

**④a + ④b** — параллельно, одним сообщением Директора (после ③ PASS).  
**⑦** — только после ⑥ PASS (нужен post_id).  
**⑧** — после ⑦ (+ индексация); skip если `git_sync=no` или нет изменений (SKIP).

## По запросу — монитор индексации (не шаг пайплайна)

| | |
|-|-|
| **Task** | `excalibur-blog-indexing-monitor` |
| **Команда** | `/excalibur-blog-indexing-status` |
| **Skill** | [indexing-monitor-excalibur-blog](../skills/indexing-monitor-excalibur-blog/SKILL.md) |
| **Скрипт** | `scripts/excalibur_blog_indexing_status.py` |

Отчёт: `blog/indexing-status-report.json` / `.md`. **Не** путать с `excalibur-blog-indexer` (interlink).

## Dzen adapter (по запросу)

| | |
|-|-|
| **Task** | `excalibur-blog-dzen` |
| **Команда** | `/excalibur-blog-dzen` |
| **Skill** | [dzen-excalibur-blog](../skills/dzen-excalibur-blog/SKILL.md) |
| **Контракт** | [shared/dzen-adapter-contract.md](../shared/dzen-adapter-contract.md) |

## Git sync (шаг ⑧ или `/excalibur-blog-git-sync`)

| | |
|-|-|
| **Task** | `excalibur-blog-git-sync` |
| **Команда** | `/excalibur-blog-git-sync` |
| **Skill** | [git-excalibur-blog](../skills/git-excalibur-blog/SKILL.md) |
| **Контракт** | [shared/excalibur-git-sync-contract.md](../shared/excalibur-git-sync-contract.md) |

## Где лежат файлы

```text
agents/                    ← исходники (локальная разработка)
.cursor/agents/            ← Cloud Task types (sync: scripts/sync_cursor_cloud.ps1)
skills/<role>/SKILL.md     ← детальные инструкции роли
```

## Handoff

- Cloud: `.cursor/excalibur-blog-handoff.md`
- Fragments (cover+schema): `.cursor/excalibur-blog-fragments/`
