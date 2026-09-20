#!/usr/bin/env python3
"""Excalibur BLOG — git allowlist scan, stage, report (no auto-commit)."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Paths relative to workspace root (mysite) that Excalibur git-sync may touch.
ALLOW_PREFIXES: tuple[str, ...] = (
    "excalibur-blog-memory/blog/",
    "excalibur-blog-memory/published-articles.md",
    "excalibur-blog-memory/plan-90-",
    "excalibur-blog-memory/EXCALIBUR-",
    "excalibur-blog-memory/topics/",
    "research/semantic-core-runs/etodigital-zametki-",
    "scripts/etodigital/excalibur",
    "scripts/etodigital/assign-excalibur",
    "scripts/etodigital/submit-post-indexing.py",
    ".cursor/rules/excalibur-etodigital.mdc",
    "shared/etodigital/wp-categories-excalibur.md",
    "docs/roadmap.md",
)

FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(^|/)site\.env\.local$"),
    re.compile(r"(^|/)\.env\.local$"),
    re.compile(r"(^|/)\.env$"),
    re.compile(r"^\.playwright-mcp/"),
    re.compile(r"^excalibur-blog-memory/memory/"),
    re.compile(r"credentials\.json$", re.I),
    re.compile(r"\.pem$"),
)

FORBIDDEN_EXACT: frozenset[str] = frozenset(
    {
        "excalibur-blog-memory/site.env.local",
        "excalibur-blog-memory/memory/site.env.local",
    }
)


def run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git command and return completed process."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def is_git_repo(root: Path) -> bool:
    """Return True if root is inside a git work tree."""
    return run_git(root, "rev-parse", "--is-inside-work-tree").returncode == 0


def current_branch(root: Path) -> str:
    """Return current git branch name."""
    proc = run_git(root, "branch", "--show-current")
    return (proc.stdout or "").strip() or "unknown"


def parse_porcelain(root: Path) -> list[dict[str, str]]:
    """Return porcelain entries as dicts with status and path."""
    proc = run_git(root, "status", "--porcelain")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "git status failed")
    entries: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2].strip() or line[0]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append({"status": status, "path": path.replace("\\", "/")})
    return entries


def path_allowed(rel: str) -> bool:
    """Return True if relative path matches Excalibur allowlist."""
    norm = rel.replace("\\", "/")
    return any(norm == p.rstrip("/") or norm.startswith(p) for p in ALLOW_PREFIXES)


def path_forbidden(rel: str) -> bool:
    """Return True if path must never be staged."""
    norm = rel.replace("\\", "/")
    if norm in FORBIDDEN_EXACT:
        return True
    return any(p.search(norm) for p in FORBIDDEN_PATTERNS)


def classify_changes(entries: list[dict[str, str]]) -> dict[str, Any]:
    """Split porcelain entries into allowed, blocking forbidden, ignored."""
    allowed: list[dict[str, str]] = []
    forbidden: list[dict[str, str]] = []
    ignored: list[dict[str, str]] = []
    for entry in entries:
        rel = entry["path"]
        if path_allowed(rel):
            if path_forbidden(rel):
                forbidden.append(entry)
            else:
                allowed.append(entry)
        elif path_forbidden(rel):
            ignored.append(entry)
        else:
            ignored.append(entry)
    return {"allowed": allowed, "forbidden": forbidden, "ignored": ignored}


def stage_allowed(root: Path, allowed: list[dict[str, str]]) -> list[str]:
    """Stage allowlisted paths; return list of staged paths."""
    staged: list[str] = []
    for entry in allowed:
        rel = entry["path"]
        proc = run_git(root, "add", "--", rel)
        if proc.returncode == 0:
            staged.append(rel)
        else:
            raise RuntimeError(f"git add failed for {rel}: {proc.stderr}")
    return staged


def suggest_commit_message(trigger: str, topic_id: str, slug: str, wp_category: str) -> str:
    """Build conventional commit subject from trigger metadata."""
    if trigger == "publish" and topic_id and slug:
        return f"feat(excalibur): publish {topic_id} — {slug}"
    if trigger == "plan":
        return "chore(excalibur): update plan-90 progress / editorial queue"
    if trigger == "category" and topic_id and wp_category:
        return f"fix(excalibur): category guard {topic_id} → {wp_category}"
    if trigger == "repair" and topic_id:
        return f"fix(excalibur): repair {topic_id}"
    return "chore(excalibur): sync blog memory and plan artifacts"


def write_report(report_path: Path, payload: dict[str, Any]) -> None:
    """Write git-sync-report.json."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    """CLI entry: dry-run or stage allowlisted Excalibur changes."""
    parser = argparse.ArgumentParser(description="Excalibur BLOG git allowlist helper")
    parser.add_argument(
        "--workspace-root",
        default=os.environ.get("MYSITE_ROOT", os.environ.get("PROJECT_ROOT", ".")),
        help="Git repository root (mysite)",
    )
    parser.add_argument(
        "--trigger",
        choices=("publish", "plan", "category", "repair", "manual"),
        default="manual",
    )
    parser.add_argument("--topic-id", default="")
    parser.add_argument("--slug", default="")
    parser.add_argument("--wp-category", default="")
    parser.add_argument("--article-dir", default="", help="Write git-sync-report.json here")
    parser.add_argument("--stage", action="store_true", help="git add allowlisted paths only")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default if no --stage)")
    args = parser.parse_args()

    root = Path(args.workspace_root).expanduser().resolve()
    if not is_git_repo(root):
        print("BLOCKER: not a git repository", file=sys.stderr)
        return 2

    entries = parse_porcelain(root)
    buckets = classify_changes(entries)
    allowed = buckets["allowed"]
    forbidden = buckets["forbidden"]

    if forbidden:
        print("BLOCKER: forbidden paths in working tree:", file=sys.stderr)
        for item in forbidden:
            print(f"  {item['status']} {item['path']}", file=sys.stderr)
        verdict = "BLOCKER"
    elif not allowed:
        verdict = "SKIP"
    else:
        verdict = "PASS"

    staged: list[str] = []
    if args.stage and verdict == "PASS":
        staged = stage_allowed(root, allowed)

    report = {
        "date": date.today().isoformat(),
        "workspace_root": str(root),
        "branch": current_branch(root),
        "trigger": args.trigger,
        "topic_id": args.topic_id or None,
        "slug": args.slug or None,
        "wp_category": args.wp_category or None,
        "verdict": verdict,
        "allowed_count": len(allowed),
        "ignored_count": len(buckets["ignored"]),
        "forbidden_count": len(forbidden),
        "allowed": allowed,
        "forbidden": forbidden,
        "staged": staged,
        "suggested_commit_subject": suggest_commit_message(
            args.trigger, args.topic_id, args.slug, args.wp_category
        ),
        "push_command": "git push origin develop",
    }

    if args.article_dir:
        report_path = Path(args.article_dir).expanduser() / "git-sync-report.json"
    else:
        report_path = root / "excalibur-blog-memory" / "blog" / "git-sync-report.json"
    write_report(report_path, report)

    print(json.dumps({"verdict": verdict, "report": str(report_path), "staged": staged}, ensure_ascii=False))
    if verdict == "BLOCKER":
        return 1
    if args.dry_run or not args.stage:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
