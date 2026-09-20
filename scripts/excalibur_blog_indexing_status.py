#!/usr/bin/env python3
"""Report IndexNow + Link Indexing Bot status for published Excalibur BLOG articles."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from excalibur_blog_link_indexing_bot import (
    env_or_file,
    fetch_task_status,
    load_env,
)
from excalibur_repo_paths import project_root

PUBLISHED_MARKDOWN = "published-articles.md"
ARTICLE_GLOBS = ("blog/articles", "memory/blog/articles")
INDEXNOW_OK = {200, 202}


def read_json(path: Path) -> dict[str, Any] | None:
    """Load JSON object from disk; return None if missing or invalid."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def slug_from_url(url: str) -> str:
    """Extract trailing slug from a published permalink."""
    path = urlparse(url).path.strip("/")
    if not path:
        return ""
    return path.split("/")[-1]


def parse_published_rows(root: Path) -> list[dict[str, str]]:
    """Parse markdown table rows from published-articles.md."""
    ledger = root / PUBLISHED_MARKDOWN
    if not ledger.is_file():
        return []
    rows: list[dict[str, str]] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|------") or "topic_id" in line:
            continue
        parts = [cell.strip() for cell in line.strip("|").split("|")]
        if len(parts) < 6:
            continue
        url = parts[5] if len(parts) > 5 else ""
        if not url.startswith("http"):
            continue
        rows.append(
            {
                "date": parts[0],
                "topic_id": parts[3] if len(parts) > 3 else "",
                "slug": parts[4] if len(parts) > 4 else slug_from_url(url),
                "url": url,
                "status": parts[-1] if parts else "",
            }
        )
    return rows


def find_article_dir(root: Path, *, topic_id: str = "", slug: str = "") -> Path | None:
    """Locate article directory by topic_id prefix or slug suffix."""
    candidates: list[Path] = []
    for base in ARTICLE_GLOBS:
        articles_root = root / base
        if not articles_root.is_dir():
            continue
        for child in articles_root.iterdir():
            if not child.is_dir():
                continue
            name = child.name
            if topic_id and name.startswith(f"{topic_id}-"):
                candidates.append(child)
            elif slug and name.endswith(f"-{slug}"):
                candidates.append(child)
            elif slug and name == slug:
                candidates.append(child)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def summarize_indexnow(data: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize IndexNow artifact."""
    if not data:
        return {"verdict": "missing", "endpoints": []}
    endpoints = data.get("endpoints") or []
    ok = any(int(item.get("status") or 0) in INDEXNOW_OK for item in endpoints if isinstance(item, dict))
    verdict = str(data.get("verdict") or ("submitted" if ok else "failed"))
    return {
        "verdict": verdict,
        "method": data.get("method"),
        "date": data.get("date"),
        "endpoints": endpoints,
    }


def summarize_bot_local(data: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize local Link Indexing Bot submit artifact."""
    if not data:
        return {"verdict": "missing", "submits": []}
    submits = []
    for item in data.get("submits") or []:
        if not isinstance(item, dict):
            continue
        engine = str(item.get("searchengine") or "")
        payload = item.get("data") or {}
        submits.append(
            {
                "searchengine": engine,
                "verdict": item.get("verdict"),
                "task_id": str(payload.get("task_id") or ""),
                "limits_used": payload.get("limits_used"),
                "msg": item.get("msg"),
            }
        )
    return {
        "verdict": data.get("verdict"),
        "date": data.get("date"),
        "submits": submits,
    }


def rollup_status(
    *,
    indexnow: dict[str, Any],
    bot: dict[str, Any],
    api_checks: list[dict[str, Any]],
) -> str:
    """Human-readable rollup for one article."""
    indexnow_ok = indexnow.get("verdict") in {"submitted"}
    bot_verdict = str(bot.get("verdict") or "missing")
    if bot_verdict == "missing" and not indexnow_ok:
        return "not_submitted"
    if bot_verdict == "missing" and indexnow_ok:
        return "indexnow_only"
    if api_checks:
        task_statuses = [
            str(item.get("task_status"))
            for item in api_checks
            if item.get("task_status") in {"active", "complete", "failed"}
        ]
        if task_statuses:
            statuses = set(task_statuses)
            if statuses <= {"complete"}:
                return "bot_complete"
            if "failed" in statuses:
                return "bot_failed"
            if "active" in statuses:
                return "bot_in_progress"
        if any(int(item.get("http_status") or 0) == 403 for item in api_checks):
            return "submitted_pending"
    if bot_verdict == "submitted":
        return "submitted_pending"
    if bot_verdict == "failed":
        return "bot_submit_failed"
    return "unknown"


def inspect_article(
    root: Path,
    *,
    topic_id: str,
    slug: str,
    url: str,
    check_api: bool,
    api_key: str,
    user_id: str,
) -> dict[str, Any]:
    """Build status record for one published article."""
    article_dir = find_article_dir(root, topic_id=topic_id, slug=slug)
    indexnow_path = (article_dir / "yandex-indexing-result.json") if article_dir else None
    bot_path = (article_dir / "link-indexing-bot-result.json") if article_dir else None
    indexnow = summarize_indexnow(read_json(indexnow_path) if indexnow_path else None)
    bot = summarize_bot_local(read_json(bot_path) if bot_path else None)

    api_checks: list[dict[str, Any]] = []
    if check_api and api_key and user_id:
        for submit in bot.get("submits") or []:
            task_id = str(submit.get("task_id") or "").strip()
            if not task_id:
                continue
            check = fetch_task_status(api_key, user_id, task_id)
            check["searchengine"] = submit.get("searchengine")
            api_checks.append(check)

    status = rollup_status(indexnow=indexnow, bot=bot, api_checks=api_checks)
    return {
        "topic_id": topic_id,
        "slug": slug,
        "url": url,
        "article_dir": article_dir.as_posix() if article_dir else None,
        "rollup_status": status,
        "indexnow": indexnow,
        "link_indexing_bot": bot,
        "api_task_checks": api_checks,
    }


def status_label(status: str) -> str:
    """Map machine status to Russian label for reports."""
    labels = {
        "not_submitted": "не отправлялась",
        "indexnow_only": "только IndexNow",
        "submitted_pending": "отправлено, ждём бота",
        "bot_in_progress": "индексируется (active)",
        "bot_complete": "бот отработал (complete)",
        "bot_failed": "ошибка бота (failed)",
        "bot_submit_failed": "отправка в бот не прошла",
        "unknown": "неизвестно",
    }
    return labels.get(status, status)


def render_markdown(report: dict[str, Any]) -> str:
    """Render human-readable indexing report."""
    lines = [
        "# Excalibur BLOG — статус индексации",
        "",
        f"Дата отчёта: {report.get('generated_at')}",
        f"Статей в отчёте: {report.get('articles_count', 0)}",
        "",
    ]
    for item in report.get("articles") or []:
        lines.extend(
            [
                f"## {item.get('topic_id') or '—'} — {item.get('slug') or '—'}",
                "",
                f"- URL: {item.get('url')}",
                f"- Статус: **{status_label(str(item.get('rollup_status') or ''))}**",
                "",
            ]
        )
        indexnow = item.get("indexnow") or {}
        lines.append(
            f"- IndexNow: `{indexnow.get('verdict')}`"
            + (f" ({indexnow.get('date')})" if indexnow.get("date") else "")
        )
        bot = item.get("link_indexing_bot") or {}
        if bot.get("verdict") == "missing":
            lines.append("- Link Indexing Bot: нет `link-indexing-bot-result.json`")
        else:
            for submit in bot.get("submits") or []:
                task_id = submit.get("task_id") or "—"
                lines.append(
                    f"- Link Indexing Bot / {submit.get('searchengine')}: "
                    f"task **{task_id}**, submit `{submit.get('verdict')}`"
                )
        for check in item.get("api_task_checks") or []:
            lines.append(
                f"  - API task {check.get('task_id')}: `{check.get('task_status') or check.get('verdict')}`"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexing status for Excalibur BLOG articles")
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--topic-id", default="", help="Filter by topic_id, e.g. Z12")
    parser.add_argument("--slug", default="", help="Filter by slug")
    parser.add_argument("--url", default="", help="Single URL to inspect")
    parser.add_argument(
        "--recent",
        type=int,
        default=0,
        help="Only last N rows from published-articles.md (0 = all matching filters)",
    )
    parser.add_argument(
        "--check-api",
        action="store_true",
        help="Poll Link Indexing Bot GET /api/tasks/{id} for each task_id",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Write indexing-status-report.json/.md here (default: <root>/blog/)",
    )
    args = parser.parse_args()

    root = (args.project_root or project_root(__file__)).resolve()
    env = load_env(root)
    api_key = env_or_file(env, "LINK_INDEXING_BOT_API_KEY")
    user_id = env_or_file(env, "LINK_INDEXING_BOT_USER_ID")

    rows = parse_published_rows(root)
    if args.url.strip():
        slug = slug_from_url(args.url.strip())
        rows = [{"date": "", "topic_id": args.topic_id.strip(), "slug": slug, "url": args.url.strip(), "status": ""}]
    else:
        if args.topic_id.strip():
            rows = [row for row in rows if row.get("topic_id") == args.topic_id.strip()]
        if args.slug.strip():
            rows = [row for row in rows if row.get("slug") == args.slug.strip()]
        if args.recent > 0:
            rows = rows[-args.recent :]

    articles = [
        inspect_article(
            root,
            topic_id=row.get("topic_id", ""),
            slug=row.get("slug", ""),
            url=row.get("url", ""),
            check_api=args.check_api,
            api_key=api_key,
            user_id=user_id,
        )
        for row in rows
    ]

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report: dict[str, Any] = {
        "generated_at": generated_at,
        "report_date": date.today().isoformat(),
        "project_root": root.as_posix(),
        "articles_count": len(articles),
        "check_api": bool(args.check_api),
        "articles": articles,
    }

    output_dir = (args.output_dir or root / "blog").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "indexing-status-report.json"
    md_path = output_dir / "indexing-status-report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote: {json_path}", file=sys.stderr)
    print(f"Wrote: {md_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
