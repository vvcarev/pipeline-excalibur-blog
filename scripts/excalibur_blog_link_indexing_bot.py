#!/usr/bin/env python3
"""Submit article URL(s) to Link Indexing Bot API (Yandex/Google/Bing)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

API_TASKS_NEW = "https://link-indexing-bot.ru/api/tasks/new"
API_TASK = "https://link-indexing-bot.ru/api/tasks/{task_id}"
API_USER = "https://link-indexing-bot.ru/api/users/{user_id}"


def load_env(root: Path) -> dict[str, str]:
    """Load key=value pairs from memory/site.env.local under project root."""
    for name in ("site.env.local", "memory/site.env.local", "memory/site.env.local.example"):
        path = root / name
        if not path.is_file():
            continue
        env: dict[str, str] = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
        return env
    return {}


def env_or_file(env: dict[str, str], key: str) -> str:
    """Resolve config from process env first, then site.env.local."""
    return (os.environ.get(key) or env.get(key) or "").strip()


def http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    """Perform HTTP request and parse JSON body."""
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = int(getattr(resp, "status", 200))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = int(exc.code)
    parsed: dict[str, Any] = {}
    if body.strip():
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}
    return status, parsed


def parse_search_engines(raw: str, *, single: str | None = None) -> list[str]:
    """Parse comma-separated search engines; validate allowed values."""
    allowed = {"yandex", "google", "bing"}
    if single:
        return [single] if single in allowed else []
    engines = [part.strip().lower() for part in raw.replace(";", ",").split(",") if part.strip()]
    out: list[str] = []
    for engine in engines:
        if engine in allowed and engine not in out:
            out.append(engine)
    return out or ["yandex", "google"]


def submit_task(
    *,
    api_key: str,
    user_id: str,
    links: list[str],
    searchengine: str = "yandex",
    se_type: str = "normal",
    priority: bool = False,
) -> dict[str, Any]:
    """Create indexing task via POST /api/tasks/new."""
    payload: dict[str, Any] = {
        "api_key": api_key,
        "user_id": user_id,
        "links": "\n".join(links),
        "searchengine": searchengine,
        "se_type": se_type,
    }
    if priority:
        payload["priority"] = True
    http_status, body = http_json(API_TASKS_NEW, method="POST", payload=payload)
    api_status = int(body.get("status") or http_status)
    msg = str(body.get("msg") or "")
    ok = api_status in {200, 201} and bool(body.get("data"))
    already = api_status == 400 and "уже существует" in msg.lower()
    verdict = "submitted" if ok else ("already_submitted" if already else "failed")
    return {
        "http_status": http_status,
        "api_status": api_status,
        "msg": msg,
        "data": body.get("data") or {},
        "verdict": verdict,
        "raw": body,
    }


def fetch_balance(api_key: str, user_id: str) -> dict[str, Any]:
    """GET /api/users/{id} — balance and limits."""
    query = urllib.parse.urlencode({"api_key": api_key})
    url = f"{API_USER.format(user_id=user_id)}?{query}"
    http_status, body = http_json(url, method="GET")
    return {
        "http_status": http_status,
        "api_status": int(body.get("status") or http_status),
        "data": body.get("data") or {},
        "msg": body.get("msg", ""),
    }


def fetch_task_status(api_key: str, user_id: str, task_id: str) -> dict[str, Any]:
    """
    GET /api/tasks/{id} — Link Indexing Bot task status.

    Possible ``data.status`` values: ``active``, ``complete``, ``failed``.
    """
    query = urllib.parse.urlencode({"api_key": api_key, "user_id": user_id})
    url = f"{API_TASK.format(task_id=task_id)}?{query}"
    http_status, body = http_json(url, method="GET")
    api_status = int(body.get("status") or http_status)
    data = body.get("data") or {}
    task_status = str(data.get("status") or "").lower()
    ok = api_status == 200 and task_status in {"active", "complete", "failed"}
    return {
        "http_status": http_status,
        "api_status": api_status,
        "task_id": task_id,
        "task_status": task_status or None,
        "data": data,
        "msg": str(body.get("msg") or ""),
        "verdict": task_status if ok else ("not_found" if api_status == 404 else "failed"),
    }


def write_result(path: Path, payload: dict[str, Any]) -> None:
    """Persist machine-readable indexing result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit URLs to Link Indexing Bot API")
    parser.add_argument("--url", action="append", dest="urls", help="URL to index (repeatable)")
    parser.add_argument("--article-dir", type=Path, help="Write link-indexing-bot-result.json here")
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument(
        "--searchengines",
        default=None,
        help="Comma-separated: yandex,google,bing (default from env or yandex,google)",
    )
    parser.add_argument("--searchengine", choices=("yandex", "google", "bing"), default=None)
    parser.add_argument("--se-type", choices=("normal", "hard"), default=None)
    parser.add_argument("--priority", action="store_true", help="Yandex priority x2 cost")
    parser.add_argument("--balance", action="store_true", help="Only show account balance")
    parser.add_argument(
        "--check-task",
        action="append",
        dest="check_tasks",
        metavar="TASK_ID",
        help="Fetch Link Indexing Bot task status (repeatable)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.project_root
    if root is None:
        excalibur_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
        root = Path(excalibur_root) if excalibur_root else Path.cwd()
    root = root.resolve()

    env = load_env(root)
    api_key = env_or_file(env, "LINK_INDEXING_BOT_API_KEY")
    user_id = env_or_file(env, "LINK_INDEXING_BOT_USER_ID")
    engines_raw = args.searchengines or env_or_file(env, "LINK_INDEXING_BOT_SEARCHENGINES") or env_or_file(
        env, "LINK_INDEXING_BOT_SEARCHENGINE"
    ) or "yandex,google"
    engines = parse_search_engines(engines_raw, single=args.searchengine)
    se_type = (args.se_type or env_or_file(env, "LINK_INDEXING_BOT_SE_TYPE") or "normal").lower()
    priority = args.priority or env_or_file(env, "LINK_INDEXING_BOT_PRIORITY").lower() in {"1", "true", "yes"}

    if not api_key:
        print("BLOCKER: LINK_INDEXING_BOT_API_KEY not set (site.env.local or env)", file=sys.stderr)
        return 2
    if not user_id:
        print(
            "BLOCKER: LINK_INDEXING_BOT_USER_ID not set. Get it from @Link_Indexing_bot → /help",
            file=sys.stderr,
        )
        return 2

    if args.balance:
        balance = fetch_balance(api_key, user_id)
        print(json.dumps(balance, ensure_ascii=False, indent=2))
        return 0 if balance.get("api_status") == 200 else 1

    check_tasks = [t.strip() for t in (args.check_tasks or []) if t and t.strip()]
    if check_tasks:
        checks = [fetch_task_status(api_key, user_id, task_id) for task_id in check_tasks]
        print(json.dumps({"tasks": checks}, ensure_ascii=False, indent=2))
        return 0 if all(c.get("verdict") in {"active", "complete", "failed"} for c in checks) else 1

    urls = [u.strip() for u in (args.urls or []) if u and u.strip()]
    if not urls:
        print("BLOCKER: pass --url or --article-dir with wp-publish-result.json permalink", file=sys.stderr)
        return 2

    result: dict[str, Any] = {
        "date": date.today().isoformat(),
        "method": "link_indexing_bot_api",
        "urls": urls,
        "searchengines": engines,
        "se_type": se_type,
        "priority": priority,
    }

    if args.dry_run:
        result["verdict"] = "dry_run"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.article_dir:
            write_result(args.article_dir / "link-indexing-bot-result.json", result)
        return 0

    submits: list[dict[str, Any]] = []
    for engine in engines:
        engine_priority = priority and engine == "yandex"
        submit = submit_task(
            api_key=api_key,
            user_id=user_id,
            links=urls,
            searchengine=engine,
            se_type=se_type,
            priority=engine_priority,
        )
        submit["searchengine"] = engine
        submits.append(submit)

    result["submits"] = submits
    ok_verdicts = {"submitted", "already_submitted"}
    result["verdict"] = "submitted" if all(s["verdict"] in ok_verdicts for s in submits) else "failed"

    if args.article_dir:
        write_result(args.article_dir / "link-indexing-bot-result.json", result)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "submitted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
