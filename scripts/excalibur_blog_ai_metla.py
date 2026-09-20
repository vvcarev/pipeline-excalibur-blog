#!/usr/bin/env python3
"""Clean AI-generated blog images via mcp-kv AI Метла (metadata strip + re-encode)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asset_download import download_url_bytes  # noqa: E402

AI_DELETE_BASE = "https://mcp-kv.ru/ai-delete"
DEFAULT_GLOBS = ("cover.png", "inline-01.png", "inline-02.png", "inline-03.png", "canvas-quad.png")


def project_root() -> Path:
    env_root = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[1]


def load_site_env(root: Path) -> None:
    """Load key=value pairs from memory/site.env.local into os.environ if unset."""
    env_path = root / "site.env.local"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def api_key() -> str:
    for name in ("AI_DELETE_API_KEY", "AI_METLA_API_KEY", "MCP_KV_AI_DELETE_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise RuntimeError(
        "missing AI_DELETE_API_KEY (set in site.env.local or env; never commit)"
    )


def upload_catbox(image_path: Path) -> str:
    proc = subprocess.run(
        [
            "curl",
            "-fsSL",
            "-F",
            "reqtype=fileupload",
            "-F",
            f"fileToUpload=@{image_path}",
            "https://catbox.moe/user/api.php",
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        url = proc.stdout.decode("utf-8", errors="replace").strip()
        if url.startswith("https://"):
            return url
    # urllib fallback
    boundary = "----ExcaliburMetlaBoundary"
    body_prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="reqtype"\r\n\r\n'
        f"fileupload\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="fileToUpload"; filename="{image_path.name}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8")
    body_suffix = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = body_prefix + image_path.read_bytes() + body_suffix
    request = urllib.request.Request(
        "https://catbox.moe/user/api.php",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "ExcaliburBlogAiMetla/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        url = response.read().decode("utf-8", errors="replace").strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"catbox upload failed: {url[:200]}")
    return url


def clean_image_url(
    *,
    image_url: str,
    title: str,
    author: str,
    copyright_text: str,
    software: str,
    description: str,
    keywords: str,
    key: str,
) -> str:
    payload = {
        "image_url": image_url,
        "title": title,
        "author": author,
        "copyright": copyright_text,
        "software": software,
        "description": description,
        "keywords": keywords,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    proc = subprocess.run(
        [
            "curl",
            "-fsSL",
            "-X",
            "POST",
            f"{AI_DELETE_BASE}/api/clean-url",
            "-H",
            "Content-Type: application/json",
            "-H",
            f"X-API-Key: {key}",
            "-d",
            payload_json,
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout:
        data = json.loads(proc.stdout.decode("utf-8"))
    else:
        body = payload_json.encode("utf-8")
        request = urllib.request.Request(
            f"{AI_DELETE_BASE}/api/clean-url",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": key,
                "User-Agent": "ExcaliburBlogAiMetla/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    if not data.get("success"):
        raise RuntimeError(f"ai-delete clean-url failed: {data}")
    download_path = (data.get("download_url") or "").strip()
    if not download_path:
        raise RuntimeError(f"ai-delete missing download_url: {data}")
    if download_path.startswith("/"):
        return f"{AI_DELETE_BASE}{download_path}"
    return download_path


def meta_defaults(article_dir: Path) -> dict[str, str]:
    meta_path = article_dir / "article.meta.json"
    title = "Eto Digital blog image"
    author = "Виктор Прокопчук"
    copyright_text = "© Eto Digital"
    keywords = "маркетинг, бизнес, etodigital"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        title = (meta.get("h1") or meta.get("title") or title)[:120]
        pk = (meta.get("primary_keyword") or "").strip()
        if pk:
            keywords = f"{pk}, маркетинг, etodigital"
    return {
        "title": title,
        "author": author,
        "copyright": copyright_text,
        "software": "Adobe Photoshop",
        "description": f"Иллюстрация к статье: {title}"[:200],
        "keywords": keywords,
    }


def download_cleaned_bytes(download_url: str) -> bytes:
    """Download cleaned image; curl fallback when urllib SSL fails."""
    try:
        data, _evidence = download_url_bytes(download_url)
        if data:
            return data
    except (urllib.error.URLError, RuntimeError, TimeoutError):
        pass
    proc = subprocess.run(
        ["curl", "-fsSL", download_url],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(
            f"download failed for {download_url}: {proc.stderr.decode('utf-8', errors='replace')[:200]}"
        )
    return proc.stdout


def clean_local_file_multipart(image_path: Path, *, meta: dict[str, str], key: str) -> dict:
    """POST file directly to /api/clean — returns cleaned image bytes."""
    proc = subprocess.run(
        [
            "curl",
            "-fsSL",
            "-X",
            "POST",
            f"{AI_DELETE_BASE}/api/clean",
            "-H",
            f"X-API-Key: {key}",
            "-F",
            f"file=@{image_path}",
            "-F",
            f"title={meta['title']}",
            "-F",
            f"author={meta['author']}",
            "-F",
            f"copyright={meta['copyright']}",
            "-F",
            f"software={meta['software']}",
            "-F",
            f"description={meta['description']}",
            "-F",
            f"keywords={meta['keywords']}",
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"ai-delete /api/clean failed for {image_path.name}: {err}")
    cleaned_bytes = proc.stdout
    if len(cleaned_bytes) < 1000:
        raise RuntimeError(f"ai-delete returned too small payload for {image_path.name}")
    image_path.write_bytes(cleaned_bytes)
    return {
        "file": image_path.name,
        "endpoint": "/api/clean",
        "bytes": len(cleaned_bytes),
        "status": "PASS",
    }


def clean_local_file(
    image_path: Path,
    *,
    meta: dict[str, str],
    key: str,
    skip_upload: bool = False,
    source_url: str = "",
) -> dict:
    hosted = source_url.strip()
    if not hosted and not skip_upload:
        hosted = upload_catbox(image_path)
    if not hosted:
        raise RuntimeError(f"no source URL for {image_path.name}")

    download_url = clean_image_url(
        image_url=hosted,
        title=meta["title"],
        author=meta["author"],
        copyright_text=meta["copyright"],
        software=meta["software"],
        description=meta["description"],
        keywords=meta["keywords"],
        key=key,
    )
    cleaned_bytes = download_cleaned_bytes(download_url)
    image_path.write_bytes(cleaned_bytes)
    return {
        "file": image_path.name,
        "source_url": hosted,
        "download_url": download_url,
        "bytes": len(cleaned_bytes),
        "status": "PASS",
    }


def discover_images(cover_dir: Path, patterns: tuple[str, ...]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        path = cover_dir / pattern
        if path.is_file():
            found.append(path)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description="Strip AI metadata from cover/inline PNGs via AI Метла")
    ap.add_argument("--article-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--include-canvas",
        action="store_true",
        help="Also clean canvas-quad.png (default: cover + inline only)",
    )
    ap.add_argument(
        "--use-mcp-url",
        default="",
        help="If set, clean this MCP result URL instead of local files (pre-split)",
    )
    args = ap.parse_args()

    root = project_root()
    load_site_env(root)

    article_dir = Path(args.article_dir)
    if not article_dir.is_absolute():
        article_dir = root / article_dir
    cover_dir = article_dir / "cover"
    if not cover_dir.is_dir():
        print(f"❌ AI METLA BLOCKER: missing {cover_dir}", file=sys.stderr)
        return 1

    patterns = ("cover.png", "inline-01.png", "inline-02.png", "inline-03.png")
    if args.include_canvas:
        patterns = DEFAULT_GLOBS

    report: dict = {
        "verdict": "PASS",
        "service": "mcp-kv-ai-delete",
        "api_base": AI_DELETE_BASE,
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "article_dir": str(article_dir),
        "files": [],
    }

    if args.dry_run:
        images = discover_images(cover_dir, patterns)
        report["verdict"] = "DRY_RUN"
        report["would_process"] = [p.name for p in images]
        out = cover_dir / "ai-metla-report.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"DRY_RUN files={len(images)}")
        return 0

    try:
        key = api_key()
    except RuntimeError as exc:
        print(f"❌ AI METLA BLOCKER: {exc}", file=sys.stderr)
        return 1

    meta = meta_defaults(article_dir)

    if args.use_mcp_url.strip():
        canvas_path = cover_dir / "canvas-quad.png"
        try:
            entry = clean_local_file(
                canvas_path,
                meta=meta,
                key=key,
                skip_upload=True,
                source_url=args.use_mcp_url.strip(),
            )
            report["files"].append(entry)
        except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
            report["verdict"] = "FAIL"
            report["files"].append({"file": "canvas-quad.png", "status": "FAIL", "error": str(exc)})
            print(f"❌ AI METLA FAIL: {exc}", file=sys.stderr)
    else:
        images = discover_images(cover_dir, patterns)
        if not images:
            print(f"❌ AI METLA BLOCKER: no PNGs in {cover_dir}", file=sys.stderr)
            return 1
        for image_path in images:
            try:
                entry = clean_local_file_multipart(image_path, meta=meta, key=key)
                report["files"].append(entry)
                print(f"OK cleaned={image_path.name} bytes={entry['bytes']}")
            except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
                report["verdict"] = "FAIL"
                report["files"].append(
                    {"file": image_path.name, "status": "FAIL", "error": str(exc)}
                )
                print(f"WARN fail {image_path.name}: {exc}", file=sys.stderr)

    out = cover_dir / "ai-metla-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["verdict"] == "FAIL":
        print("❌ AI METLA BLOCKER: one or more files failed", file=sys.stderr)
        return 1
    print(f"OK ai-metla-report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
