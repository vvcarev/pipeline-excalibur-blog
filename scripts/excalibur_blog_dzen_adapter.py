#!/usr/bin/env python3
"""Excalibur BLOG — Dzen adapter: resolve article, prepare images, validate HTML, similarity."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from excalibur_repo_paths import project_root, repo_relative

DZEN_ALLOWED_TAGS = frozenset(
    {
        "p",
        "a",
        "b",
        "i",
        "u",
        "s",
        "h1",
        "h2",
        "h3",
        "h4",
        "blockquote",
        "ul",
        "ol",
        "li",
        "figure",
        "img",
        "figcaption",
        "video",
        "source",
        "iframe",
        "br",
    }
)
MIN_IMAGE_WIDTH = 700
MAX_SIMILARITY_RATIO = 0.40
DZEN_CHAR_MIN = 4800
DZEN_CHAR_MAX = 5600
DZEN_CHAR_TARGET = "5000-5500"


def _root() -> Path:
    return project_root(__file__)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def char_count_no_html(html: str) -> int:
    return len(strip_html(html))


def ngram_set(text: str, n: int = 5) -> set[str]:
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def similarity_ratio(a: str, b: str) -> float:
    sa, sb = ngram_set(a), ngram_set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


class DzenHTMLValidator(HTMLParser):
  """Validate Dzen RSS HTML whitelist."""

  def __init__(self) -> None:
      super().__init__()
      self.errors: list[str] = []

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
      t = tag.lower()
      if t not in DZEN_ALLOWED_TAGS:
          line, col = self.getpos()
          self.errors.append(f"Forbidden tag <{t}> at {line}:{col}")
      if t in {"script", "style", "div", "span", "table"}:
          line, col = self.getpos()
          self.errors.append(f"Blocked tag <{t}> at {line}:{col}")

  def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
      self.handle_starttag(tag, attrs)


def validate_dzen_html(html: str) -> list[str]:
    errors: list[str] = []
    if re.search(r"\sstyle\s*=", html, flags=re.I):
        errors.append("Inline style= is forbidden for Dzen RSS")
    if re.search(r"<script\b", html, flags=re.I):
        errors.append("<script> is forbidden")
    parser = DzenHTMLValidator()
    try:
        parser.feed(html)
        errors.extend(parser.errors)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"HTML parse error: {exc}")
    return errors


def validate_dzen_policy(html: str) -> list[str]:
    """Dzen editorial policy: length, hyphens, links."""
    errors: list[str] = []
    text = strip_html(html)
    cc = len(text)
    if cc < DZEN_CHAR_MIN or cc > DZEN_CHAR_MAX:
        errors.append(
            f"Char count {cc} outside {DZEN_CHAR_TARGET} (allowed {DZEN_CHAR_MIN}-{DZEN_CHAR_MAX})"
        )
    if "—" in html or "–" in html:
        errors.append("Use short hyphen `-` only; em/en dash found")
    if "→" in html:
        errors.append("Arrow `→` forbidden; use `-` or words")
    links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', html, flags=re.I)
    if len(links) > 1:
        errors.append(f"Max 1 link allowed, found {len(links)}: {links}")
    for url in links:
        if "t.me/" not in url and "telegram" not in url.lower():
            errors.append(f"Only Telegram link allowed, got: {url}")
    site_hosts = ("etodigital.ru", "/zametki/", "http://", "https://etodigital")
    for url in links:
        if any(h in url for h in site_hosts if h != "http://" and h != "https://"):
            if "t.me" not in url:
                errors.append(f"Site/external link forbidden: {url}")
    # img src on wp-content for images is OK (not <a> links)
    if re.search(r"etodigital\.ru/zametki", html, flags=re.I):
        errors.append("Site URL in text forbidden (etodigital.ru/zametki)")
    return errors


def find_article_dirs(root: Path) -> list[Path]:
    base = root / "blog" / "articles"
    if not base.is_dir():
        base = root / "memory" / "blog" / "articles"
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir())


def resolve_article_dir(
    root: Path,
    *,
    topic_id: str | None = None,
    slug: str | None = None,
    permalink: str | None = None,
    article_dir: str | None = None,
) -> Path | None:
    if article_dir:
        p = Path(article_dir)
        if not p.is_absolute():
            p = root / p
        return p if (p / "article.html").is_file() else None

    if permalink:
        slug_match = re.search(r"/zametki/([^/?#]+)/?", permalink)
        if slug_match:
            slug = slug_match.group(1)

    for d in find_article_dirs(root):
        name = d.name
        if topic_id and name.startswith(f"{topic_id}-"):
            return d
        if slug and (name.endswith(f"-{slug}") or name.split("-", 1)[-1] == slug):
            return d
        meta_path = d / "article.meta.json"
        if meta_path.is_file():
            meta = load_json(meta_path)
            if slug and meta.get("slug") == slug:
                return d
            if topic_id and meta.get("topic_id") == topic_id:
                return d
    return None


def require_pillow():
    try:
        from PIL import Image  # noqa: F401

        return True
    except ImportError:
        return False


def prepare_image(src: Path, dest: Path, min_width: int = MIN_IMAGE_WIDTH) -> dict[str, Any]:
    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im.load()
        w, h = im.size
        out = im.convert("RGB") if im.mode not in ("RGB", "L") else im
        if w < min_width:
            scale = min_width / w
            out = out.resize((min_width, max(1, int(h * scale))), Image.Resampling.LANCZOS)
            w, h = out.size
        suffix = dest.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            out.save(dest, format="JPEG", quality=88, optimize=True)
            mime = "image/jpeg"
        else:
            dest = dest.with_suffix(".jpg")
            out.save(dest, format="JPEG", quality=88, optimize=True)
            mime = "image/jpeg"
        return {
            "source": repo_relative(src, _root()),
            "path": repo_relative(dest, _root()),
            "width": w,
            "height": h,
            "mime": mime,
            "ok": w >= min_width,
        }


def collect_image_sources(article_dir: Path, wp: dict[str, Any] | None) -> list[tuple[str, Path | str]]:
    """Return (role, local path or absolute URL)."""
    sources: list[tuple[str, Path | str]] = []
    cover = article_dir / "cover" / "cover.png"
    if cover.is_file():
        sources.append(("cover", cover))
    for i in range(1, 6):
        inline = article_dir / "cover" / f"inline-{i:02d}.png"
        if inline.is_file():
            sources.append((f"inline_{i:02d}", inline))
    if wp and wp.get("raw_output"):
        for match in re.finditer(
            r"inline_image_upload=\d+ src=\S+ url=(https://\S+)",
            wp["raw_output"],
        ):
            sources.append((f"wp_{len(sources)}", match.group(1)))
    return sources


def prepare_images(article_dir: Path) -> dict[str, Any]:
    if not require_pillow():
        return {"verdict": "BLOCKED", "error": "Pillow required: pip install Pillow"}

    dzen_dir = article_dir / "dzen" / "dzen-images"
    wp_path = article_dir / "wp-publish-result.json"
    wp = load_json(wp_path) if wp_path.is_file() else None
    report: dict[str, Any] = {"images": [], "verdict": "PASS"}

    idx = 0
    for role, src in collect_image_sources(article_dir, wp):
        if isinstance(src, Path):
            if role == "cover":
                dest = dzen_dir / "cover-enclosure.jpg"
            else:
                idx += 1
                dest = dzen_dir / f"inline-{idx:02d}.jpg"
            try:
                info = prepare_image(src, dest)
                info["role"] = role
                report["images"].append(info)
                if not info["ok"]:
                    report["verdict"] = "BLOCKED"
            except OSError as exc:
                report["images"].append({"role": role, "error": str(exc), "ok": False})
                report["verdict"] = "BLOCKED"
        else:
            report["images"].append({"role": role, "url": src, "ok": True, "remote": True})

    return report


def build_dzen_meta(article_dir: Path, dzen_html_path: Path) -> dict[str, Any]:
    meta_path = article_dir / "article.meta.json"
    meta = load_json(meta_path) if meta_path.is_file() else {}
    wp_path = article_dir / "wp-publish-result.json"
    wp = load_json(wp_path) if wp_path.is_file() else {}

    dzen_html = dzen_html_path.read_text(encoding="utf-8") if dzen_html_path.is_file() else ""
    ab = meta.get("meta_ab") or {}

    guid = str(wp.get("post_id") or meta.get("topic_id") or uuid.uuid4())
    permalink = wp.get("permalink") or ""

    return {
        "topic_id": meta.get("topic_id"),
        "slug": meta.get("slug"),
        "permalink": permalink,
        "guid": f"etodigital-{guid}",
        "title_dzen": ab.get("title_ctr") or meta.get("h1") or meta.get("title"),
        "description_dzen": ab.get("description_ctr") or meta.get("description"),
        "char_count": char_count_no_html(dzen_html),
        "dzen_format": "format-article",
        "rss_categories": ["native-draft", "format-article", "index", "comment-all"],
        "pub_date_rfc822": format_datetime(datetime.now(timezone.utc).astimezone()),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Excalibur BLOG Dzen adapter utilities")
    parser.add_argument("--topic-id")
    parser.add_argument("--slug")
    parser.add_argument("--permalink")
    parser.add_argument("--article-dir")
    parser.add_argument("--resolve-only", action="store_true")
    parser.add_argument("--prepare-images", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--similarity-check", action="store_true")
    parser.add_argument("--build-meta", action="store_true")
    args = parser.parse_args()

    root = _root()
    article_dir = resolve_article_dir(
        root,
        topic_id=args.topic_id,
        slug=args.slug,
        permalink=args.permalink,
        article_dir=args.article_dir,
    )
    if article_dir is None:
        print("❌ DZEN INPUT BLOCKER: article_dir not found", file=sys.stderr)
        return 1

    rel = repo_relative(article_dir, root)
    print(json.dumps({"article_dir": rel, "ok": True}, ensure_ascii=False))

    if args.resolve_only:
        return 0

    report: dict[str, Any] = {"article_dir": rel, "steps": {}}

    dzen_dir = article_dir / "dzen"
    dzen_html = dzen_dir / "dzen-article.html"

    if args.prepare_images:
        img_report = prepare_images(article_dir)
        report["steps"]["images"] = img_report
        if img_report.get("verdict") == "BLOCKED":
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2

    if args.validate and dzen_html.is_file():
        html = dzen_html.read_text(encoding="utf-8")
        errors = validate_dzen_html(html) + validate_dzen_policy(html)
        cc = char_count_no_html(html)
        report["steps"]["validate"] = {
            "char_count": cc,
            "char_target": DZEN_CHAR_TARGET,
            "errors": errors,
            "verdict": "PASS"
            if not errors and DZEN_CHAR_MIN <= cc <= DZEN_CHAR_MAX
            else "BLOCKED",
        }
        if errors or cc < DZEN_CHAR_MIN or cc > DZEN_CHAR_MAX:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 3

    if args.similarity_check and dzen_html.is_file():
        canon = (article_dir / "article.html").read_text(encoding="utf-8")
        dzen = dzen_html.read_text(encoding="utf-8")
        ratio = similarity_ratio(strip_html(canon), strip_html(dzen))
        report["steps"]["similarity"] = {
            "ratio": round(ratio, 4),
            "max_allowed": MAX_SIMILARITY_RATIO,
            "verdict": "PASS" if ratio <= MAX_SIMILARITY_RATIO else "BLOCKED",
        }
        if ratio > MAX_SIMILARITY_RATIO:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 4

    if args.build_meta or (args.validate and dzen_html.is_file()):
        dzen_dir.mkdir(parents=True, exist_ok=True)
        meta = build_dzen_meta(article_dir, dzen_html)
        save_json(dzen_dir / "dzen-meta.json", meta)
        report["steps"]["meta"] = meta

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
