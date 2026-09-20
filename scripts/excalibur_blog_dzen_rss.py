#!/usr/bin/env python3
"""Excalibur BLOG — build Dzen RSS item and optional feed merge / FTP push."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any

from excalibur_blog_dzen_adapter import build_dzen_meta, resolve_article_dir
from excalibur_repo_paths import project_root, repo_relative

RSS_NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
    "atom": "http://www.w3.org/2005/Atom",
}


def _root() -> Path:
    return project_root(__file__)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def escape_cdata(html: str) -> str:
    """Wrap HTML in CDATA, escape nested ]]> if any."""
    return html.replace("]]>", "]]]]><![CDATA[>")


def enclosure_url(article_dir: Path, meta: dict[str, Any], public_site: str) -> str:
    local = article_dir / "dzen" / "dzen-images" / "cover-enclosure.jpg"
    if local.is_file() and public_site:
        slug = meta.get("slug") or "cover"
        return f"{public_site.rstrip('/')}/wp-content/uploads/dzen/{slug}-cover.jpg"
    wp = article_dir / "wp-publish-result.json"
    if wp.is_file():
        raw = load_json(wp).get("raw_output") or ""
        m = re.search(r"permalink=(https://\S+)", raw)
        if m:
            base = m.group(1).rstrip("/")
            return f"{base.rsplit('/', 1)[0]}/../wp-content/uploads/"  # fallback weak
    return ""


def build_rss_item_xml(article_dir: Path, env: dict[str, str]) -> str:
    dzen_dir = article_dir / "dzen"
    dzen_html_path = dzen_dir / "dzen-article.html"
    if not dzen_html_path.is_file():
        raise FileNotFoundError("dzen/dzen-article.html missing")

    meta_path = dzen_dir / "dzen-meta.json"
    meta = load_json(meta_path) if meta_path.is_file() else build_dzen_meta(article_dir, dzen_html_path)

    html = dzen_html_path.read_text(encoding="utf-8")
    title = meta.get("title_dzen") or "Без названия"
    link = meta.get("permalink") or env.get("PUBLIC_SITE_URL", "").rstrip("/") + "/zametki/"
    guid = meta.get("guid") or f"etodigital-{meta.get('slug', 'unknown')}"
    pub_date = meta.get("pub_date_rfc822") or format_datetime(datetime.now(timezone.utc).astimezone())
    description = meta.get("description_dzen") or ""

    categories = meta.get("rss_categories") or [
        env.get("DZEN_RSS_DEFAULT_CATEGORY", "native-draft"),
        env.get("DZEN_RSS_DEFAULT_FORMAT", "format-article"),
        env.get("DZEN_RSS_DEFAULT_INDEX", "index"),
        "comment-all",
    ]

    enc_url = enclosure_url(article_dir, meta, env.get("PUBLIC_SITE_URL", ""))

    lines = [
        "    <item>",
        f"      <title>{_xml_escape(title)}</title>",
        f"      <link>{_xml_escape(link)}</link>",
        f"      <guid>{_xml_escape(guid)}</guid>",
        f"      <pubDate>{pub_date}</pubDate>",
    ]
    for cat in categories:
        lines.append(f"      <category>{_xml_escape(cat)}</category>")
    if enc_url:
        lines.append(f'      <enclosure url="{_xml_escape(enc_url)}" type="image/jpeg"/>')
    lines.append(f"      <description>{_xml_escape(description)}</description>")
    lines.append(f"      <content:encoded><![CDATA[{escape_cdata(html)}]]></content:encoded>")
    lines.append("    </item>")
    return "\n".join(lines)


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_full_feed(channel_title: str, channel_link: str, items_xml: list[str]) -> str:
    items_block = "\n".join(items_xml)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="{RSS_NS['content']}"
  xmlns:dc="{RSS_NS['dc']}"
  xmlns:media="{RSS_NS['media']}"
  xmlns:atom="{RSS_NS['atom']}">
  <channel>
    <title>{_xml_escape(channel_title)}</title>
    <link>{_xml_escape(channel_link)}</link>
    <language>ru</language>
{items_block}
  </channel>
</rss>
"""


def merge_feed(feed_path: Path, new_item_xml: str, guid: str) -> None:
    """Insert or replace item by guid in feed file."""
    if feed_path.is_file():
        text = feed_path.read_text(encoding="utf-8")
        if guid in text:
            pattern = re.compile(
                r"<item>.*?</item>",
                flags=re.DOTALL,
            )
            parts = pattern.findall(text)
            replaced = False
            for part in parts:
                if guid in part:
                    text = text.replace(part, new_item_xml.strip())
                    replaced = True
                    break
            if not replaced:
                text = text.replace("</channel>", f"{new_item_xml}\n  </channel>")
        else:
            text = text.replace("</channel>", f"{new_item_xml}\n  </channel>")
        feed_path.write_text(text, encoding="utf-8")
    else:
        feed_path.parent.mkdir(parents=True, exist_ok=True)
        channel_title = os.environ.get("DZEN_RSS_CHANNEL_TITLE", "Excalibur BLOG")
        channel_link = os.environ.get("PUBLIC_SITE_URL", "https://example.com")
        feed_path.write_text(
            build_full_feed(channel_title, channel_link, [new_item_xml]),
            encoding="utf-8",
        )


def push_ftp(local_path: Path, remote_path: str) -> dict[str, Any]:
    host = os.environ.get("FTP_HOST", "").strip()
    user = os.environ.get("FTP_USER", "").strip()
    password = os.environ.get("FTP_PASS", "").strip()
    port = int(os.environ.get("FTP_PORT", "21"))
    if not all([host, user, password]):
        return {"verdict": "BLOCKED", "error": "FTP credentials missing"}

    from ftplib import FTP

    ftp = FTP()
    ftp.connect(host, port, timeout=60)
    ftp.login(user, password)
    try:
        remote_path = remote_path.replace("\\", "/")
        parts = [p for p in remote_path.split("/") if p]
        filename = parts[-1]
        dirs = parts[:-1]
        for d in dirs:
            try:
                ftp.cwd(d)
            except Exception:  # noqa: BLE001
                ftp.mkd(d)
                ftp.cwd(d)
        with local_path.open("rb") as fh:
            ftp.storbinary(f"STOR {filename}", fh)
        return {"verdict": "PASS", "remote": remote_path}
    finally:
        ftp.quit()


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Excalibur BLOG Dzen RSS builder")
    parser.add_argument("--topic-id")
    parser.add_argument("--slug")
    parser.add_argument("--article-dir")
    parser.add_argument("--write-item", action="store_true")
    parser.add_argument("--merge-feed", action="store_true")
    parser.add_argument("--push-ftp", action="store_true")
    args = parser.parse_args()

    root = _root()
    env_path = root / "site.env.local"
    load_env_file(env_path)

    article_dir = resolve_article_dir(
        root,
        topic_id=args.topic_id,
        slug=args.slug,
        article_dir=args.article_dir,
    )
    if article_dir is None:
        print("❌ DZEN INPUT BLOCKER", file=sys.stderr)
        return 1

    if args.merge_feed or args.push_ftp:
        if os.environ.get("DZEN_RSS_ENABLED", "no").lower() not in {"yes", "1", "true"}:
            print("❌ DZEN PUSH BLOCKER: DZEN_RSS_ENABLED!=yes", file=sys.stderr)
            return 2

    try:
        item_xml = build_rss_item_xml(article_dir, dict(os.environ))
    except FileNotFoundError as exc:
        print(f"❌ DZEN RSS BLOCKER: {exc}", file=sys.stderr)
        return 3

    dzen_dir = article_dir / "dzen"
    dzen_dir.mkdir(parents=True, exist_ok=True)
    item_path = dzen_dir / "dzen-rss-item.xml"
    item_path.write_text(item_xml + "\n", encoding="utf-8")

    result: dict[str, Any] = {
        "item_path": repo_relative(item_path, root),
        "verdict": "PASS",
    }

    meta = load_json(dzen_dir / "dzen-meta.json") if (dzen_dir / "dzen-meta.json").is_file() else {}
    guid = meta.get("guid", "")

    if args.merge_feed:
        feed_rel = os.environ.get("DZEN_RSS_FEED_LOCAL", "blog/dzen-feed.xml")
        feed_path = root / feed_rel
        merge_feed(feed_path, item_xml, guid)
        result["feed_path"] = repo_relative(feed_path, root)

    if args.push_ftp:
        feed_local = root / os.environ.get("DZEN_RSS_FEED_LOCAL", "blog/dzen-feed.xml")
        remote = os.environ.get("DZEN_RSS_FTP_PATH", "")
        if not remote:
            print("❌ DZEN PUSH BLOCKER: DZEN_RSS_FTP_PATH empty", file=sys.stderr)
            return 4
        push_result = push_ftp(feed_local, remote)
        result["ftp"] = push_result
        if push_result.get("verdict") != "PASS":
            return 5

    push_result_path = dzen_dir / "dzen-rss-push-result.json"
    save_json(push_result_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
