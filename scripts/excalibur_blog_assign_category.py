#!/usr/bin/env python3
"""Assign and verify WordPress category for Excalibur BLOG post (SSH + wp-cli)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

import paramiko

from excalibur_blog_category import (
    CATEGORY_DISPLAY_NAMES,
    FORBIDDEN_CATEGORY_SLUGS,
    VALID_CATEGORY_SLUGS,
    ensure_meta_has_category,
    is_valid_live_category,
    resolve_category_slug,
)
from excalibur_blog_wp_publish import load_env
from excalibur_repo_paths import project_root

WP_PHP = "/usr/local/bin/php8.1"
WP_CLI = "/usr/local/bin/wp-cli.phar"


def shell_quote(value: str) -> str:
    """Shell-safe single-quoted string."""
    return "'" + value.replace("'", "'\\''") + "'"


def resolve_remote_site_root(env: dict[str, str]) -> str:
    """Resolve WordPress root on hosting for SSH/wp-cli."""
    for key in ("REMOTE_SITE_ROOT", "WP_ROOT", "FTP_ROOT"):
        value = (env.get(key) or "").strip().rstrip("/")
        if not value:
            continue
        if value.startswith("/etodigital.ru/"):
            suffix = value.removeprefix("/etodigital.ru/").lstrip("/")
            return f"~/etodigital.ru/{suffix}" if suffix else "~/etodigital.ru/public_html"
        if value.startswith("etodigital.ru/"):
            return f"~/{value}"
        return value
    return "~/etodigital.ru/public_html"


def ssh_run(env: dict[str, str], cmd: str, *, timeout: int = 120) -> str:
    """Execute command on remote WP host via SSH."""
    host = (env.get("SSH_HOST") or "").strip()
    user = (env.get("SSH_USER") or "").strip()
    password = (env.get("SSH_PASSWORD") or "").strip()
    port = int((env.get("SSH_PORT") or "22").strip() or "22")
    root = resolve_remote_site_root(env)
    if not all([host, user, password, root]):
        raise RuntimeError("SSH_HOST, SSH_USER, SSH_PASSWORD and FTP_ROOT required in site.env.local")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port=port, username=user, password=password, timeout=25)
    try:
        full = f"cd {root} && {cmd}"
        _, stdout, stderr = client.exec_command(full, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        if code != 0:
            raise RuntimeError(f"SSH failed ({code}): {full}\n{err}\n{out}")
        return out
    finally:
        client.close()


def ensure_category_term(env: dict[str, str], slug: str) -> None:
    """Create WP category term if missing."""
    wp = f"{WP_PHP} {WP_CLI}"
    name = CATEGORY_DISPLAY_NAMES.get(slug, slug)
    exists = ssh_run(
        env,
        f"{wp} term list category --slug={shell_quote(slug)} --field=term_id --format=ids",
    ).strip()
    if exists:
        return
    ssh_run(
        env,
        f"{wp} term create category {shell_quote(name)} --slug={shell_quote(slug)}",
    )


def get_post_categories(env: dict[str, str], post_id: int) -> list[str]:
    """Return category slugs currently assigned to post."""
    wp = f"{WP_PHP} {WP_CLI}"
    raw = ssh_run(
        env,
        f"{wp} post term list {post_id} category --field=slug --format=json",
    ).strip()
    if not raw or raw == "[]":
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for item in data:
        if isinstance(item, dict):
            slug = str(item.get("slug") or "").strip()
            if slug:
                out.append(urllib.parse.unquote(slug))
        elif item:
            out.append(urllib.parse.unquote(str(item).strip()))
    return out


def assign_post_category(env: dict[str, str], post_id: int, category_slug: str) -> str:
    """Set primary category for a WP post."""
    wp = f"{WP_PHP} {WP_CLI}"
    ensure_category_term(env, category_slug)
    out = ssh_run(
        env,
        f"{wp} post term set {post_id} category {shell_quote(category_slug)}",
    )
    ssh_run(env, f"{wp} cache flush", timeout=60)
    return out.strip()


def write_result(article_dir: Path, payload: dict[str, object]) -> None:
    """Write category-guard result JSON next to article artifacts."""
    path = article_dir / "category-guard-result.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Excalibur BLOG — WP category assign + verify")
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--article-dir", type=Path, required=True)
    parser.add_argument("--category", help="Override category slug")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    root = project_root(__file__)
    article_dir = args.article_dir if args.article_dir.is_absolute() else root / args.article_dir
    env = load_env(root)
    post_id = args.post_id

    if args.check_only:
        slugs = get_post_categories(env, post_id)
        ok = is_valid_live_category(slugs)
        print(json.dumps({"post_id": post_id, "categories": slugs, "verdict": "PASS" if ok else "FAIL"}, ensure_ascii=False))
        return 0 if ok else 1

    if args.category:
        category_slug = args.category.strip().lower()
        ensure_meta_has_category(article_dir)
    else:
        category_slug = ensure_meta_has_category(article_dir)

    if category_slug not in VALID_CATEGORY_SLUGS:
        print(f"BLOCKER: invalid category {category_slug!r}", file=sys.stderr)
        return 2

    before = get_post_categories(env, post_id)
    assign_post_category(env, post_id, category_slug)
    after = get_post_categories(env, post_id)
    ok = is_valid_live_category(after) and category_slug in [s.lower() for s in after]

    result: dict[str, object] = {
        "post_id": post_id,
        "topic_id": json.loads((article_dir / "article.meta.json").read_text(encoding="utf-8")).get("topic_id"),
        "expected_category": category_slug,
        "categories_before": before,
        "categories_after": after,
        "verdict": "PASS" if ok else "FAIL",
        "forbidden_detected": any(s.lower() in FORBIDDEN_CATEGORY_SLUGS for s in after),
    }
    write_result(article_dir, result)

    if not ok:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(f"OK post {post_id} -> category {category_slug}")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
