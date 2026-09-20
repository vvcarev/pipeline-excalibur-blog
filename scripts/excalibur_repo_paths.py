"""Project root resolution for Excalibur BLOG (vendor scripts + per-project memory)."""

from __future__ import annotations

import os
from pathlib import Path


def project_root(caller_file: str | Path | None = None) -> Path:
    """
    Resolve Excalibur memory root.

    Priority:
    1. ``EXCALIBUR_PROJECT_ROOT`` env (e.g. ``<PROJECT_ROOT>/excalibur-blog-memory``)
    2. Parent of vendor package (legacy standalone EXCALIBUR repo layout)
    """
    env = os.environ.get("EXCALIBUR_PROJECT_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if caller_file is not None:
        return Path(caller_file).resolve().parents[1]
    return Path(__file__).resolve().parents[1]


def project_root_from(anchor: Path) -> Path:
    """Backward-compatible alias used by asset helpers."""
    return project_root(anchor)


def repo_relative(path: Path, root: Path | None = None) -> str:
    """Return POSIX path relative to project root for JSON reports."""
    p = path.resolve()
    base = (root or project_root()).resolve()
    try:
        return p.relative_to(base).as_posix()
    except ValueError:
        return p.as_posix()
