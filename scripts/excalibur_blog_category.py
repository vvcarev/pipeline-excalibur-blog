#!/usr/bin/env python3
"""Map Excalibur plan clusters to WordPress category slugs (etodigital.ru /zametki/)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_CATEGORY_SLUGS: frozenset[str] = frozenset(
    {"sajt", "marketing", "lidy", "oshibki", "smm", "depjoy"}
)

CATEGORY_DISPLAY_NAMES: dict[str, str] = {
    "sajt": "Сайт",
    "marketing": "Маркетинг",
    "lidy": "Лиды",
    "oshibki": "Ошибки",
    "smm": "SMM",
    "depjoy": "Деплой",
}

FORBIDDEN_CATEGORY_SLUGS: frozenset[str] = frozenset(
    {"bez-rubriki", "uncategorized", "без-рубрики"}
)

CLUSTER_TO_CATEGORY: dict[str, str] = {
    "Конверсия": "sajt",
    "Сайт под ключ": "sajt",
    "Заявки с сайта": "sajt",
    "SEO для бизнеса": "marketing",
    "GEO/нейропоиск": "marketing",
    "Яндекс Директ": "marketing",
    "Контент для бизнеса": "marketing",
    "Маркетинг для бизнеса": "marketing",
    "Продвижение услуг": "marketing",
    "Аудит маркетинга": "marketing",
    "Внешний CMO": "marketing",
    "B2B/ниша": "marketing",
    "B2B услуги": "marketing",
    "Медицина маркетинг": "marketing",
    "Ремонт/дизайн заявки": "marketing",
    "Упаковка услуги": "marketing",
    "Отзывы и карты": "marketing",
    "Яндекс Метрика": "marketing",
    "Аналитика": "marketing",
    "Воронка продаж": "lidy",
    "Лидогенерация": "lidy",
    "CRM лиды": "lidy",
    "Ошибки маркетинга": "oshibki",
    "Мессенджеры заявки": "smm",
}


def resolve_category_slug(meta: dict[str, Any]) -> str:
    """
    Resolve WP category slug from article.meta.json or plan brief.

    Priority: wp_category / category_slug → cluster map → default marketing.
    """
    for key in ("wp_category", "category_slug", "category"):
        raw = str(meta.get(key) or "").strip().lower()
        if raw in VALID_CATEGORY_SLUGS:
            return raw

    cluster = str(meta.get("cluster") or "").strip()
    if cluster in CLUSTER_TO_CATEGORY:
        return CLUSTER_TO_CATEGORY[cluster]

    return "marketing"


def ensure_meta_has_category(article_dir: Path) -> str:
    """
    Ensure article.meta.json contains wp_category; write back if missing.

    Returns:
        Resolved category slug.
    """
    meta_path = article_dir / "article.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    slug = resolve_category_slug(meta)
    if meta.get("wp_category") != slug:
        meta["wp_category"] = slug
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return slug


def is_valid_live_category(slugs: list[str]) -> bool:
    """Return True if post has at least one allowed category and no forbidden slug."""
    if not slugs:
        return False
    normalized = [s.lower() for s in slugs]
    if any(s in FORBIDDEN_CATEGORY_SLUGS for s in normalized):
        return False
    return any(s in VALID_CATEGORY_SLUGS for s in normalized)
