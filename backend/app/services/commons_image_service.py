"""
Wikimedia Commons Image Resolution Service
============================================
Resolves a plain-text image search description into an actual, freely
licensed image hosted on Wikimedia Commons — used to fill in the
`resolved_image_url` / `thumb_url` / `license` / `attribution` fields of
a SuggestedImage (see app/models/lesson_blocks.py) at chapter-ingestion
time, so serving a chapter to a student never needs a live network call.

Wikimedia Commons is used specifically because:
  - It requires no API key (fully open MediaWiki API).
  - Nearly everything hosted there is public-domain or Creative-Commons
    licensed, matching the "always prefer free/open-licence sources"
    instruction baked into the GPT-5.5 Advanced-chapter prompt (see
    scripts/prepare_gpt55_prompts_advanced.py).

This module NEVER runs at request-serving time — only from the
ingestion script (scripts/ingest_gpt55_chapter_output.py), so a slow or
failing Commons API call never affects a student's page load.
"""

from __future__ import annotations

import re
from typing import Optional

# On some machines (e.g. behind a corporate TLS-inspecting proxy), the
# certifi CA bundle bundled with `requests` does not include the local
# proxy's certificate, causing SSLCertVerificationError even though the
# system (macOS Keychain / Windows cert store) already trusts it.
# `truststore` patches ssl.SSLContext to delegate verification to the
# OS-native trust store instead, which resolves this without disabling
# verification. This must run before `requests`/urllib3 opens any
# connection, so it is injected at import time, once, for this module.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:  # pragma: no cover - safe to continue without it
    pass

import requests

from app.services.logger_service import get_logger

_log = get_logger("services.commons_image")

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "LikhapohaCBSETutor/1.0 (educational content enrichment; contact: admin@likhapoha.example)"
REQUEST_TIMEOUT_SECONDS = 8


def _search_commons_files(query: str, limit: int = 5) -> list[dict]:
    """Search Commons file namespace (ns=6) for a plain-text query.
    Returns a list of {"title": "File:...png", "pageid": int} dicts."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": 6,
        "srlimit": limit,
        "format": "json",
    }
    try:
        resp = requests.get(
            COMMONS_API, params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("query", {}).get("search", []) or []
    except Exception as exc:
        _log.warning("commons_image.search_failed", query=query[:80], error=str(exc))
        return []


_ACCEPTABLE_EXT_RE = re.compile(r"\.(jpe?g|png|svg|gif)$", re.IGNORECASE)


def _get_file_info(title: str) -> Optional[dict]:
    """Fetch imageinfo (actual file URL, thumb URL, license, artist) for
    one Commons File: title. Returns None if unavailable or not a usable
    raster/vector image (e.g. skips PDFs, audio, video)."""
    if not _ACCEPTABLE_EXT_RE.search(title):
        return None
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
        "iiurlwidth": 640,
        "format": "json",
    }
    try:
        resp = requests.get(
            COMMONS_API, params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            infos = page.get("imageinfo")
            if not infos:
                continue
            info = infos[0]
            width = info.get("width") or 0
            height = info.get("height") or 0
            # Skip tiny icons/thumbnails that are unlikely to be useful figures
            if width and height and (width < 200 or height < 150):
                continue
            extmeta = info.get("extmetadata", {}) or {}

            def _meta(key: str) -> str:
                val = extmeta.get(key, {})
                return re.sub(r"<[^>]+>", "", str(val.get("value", ""))).strip() if val else ""

            license_short = _meta("LicenseShortName") or _meta("License")
            artist = _meta("Artist")
            credit = _meta("Credit")
            attribution = artist or credit or ""

            return {
                "full_url": info.get("url", ""),
                "thumb_url": info.get("thumburl", "") or info.get("url", ""),
                "source_page_url": f"https://commons.wikimedia.org/wiki/{title.replace(' ', '_')}",
                "license": license_short,
                "attribution": attribution,
            }
    except Exception as exc:
        _log.warning("commons_image.fileinfo_failed", title=title[:80], error=str(exc))
    return None


def _shorten_query(query: str, max_words: int) -> str:
    """Return the first max_words words of query, dropping very short
    filler words like 'a', 'of', 'the' from the tail if it helps stay
    concise. Used as a fallback when the full descriptive phrase yields
    no Commons hits — Commons' search works far better with 2-4 solid
    nouns than a full descriptive sentence."""
    words = re.findall(r"[A-Za-z0-9']+", query)
    return " ".join(words[:max_words])


def resolve_commons_image(search_description: str, topic: str = "") -> Optional[dict]:
    """Given a plain-text search description (and optionally a short
    topic label), return the best-matching freely-licensed Commons image
    as a dict:
        {"full_url", "thumb_url", "source_page_url", "license", "attribution"}
    or None if nothing suitable was found.

    Commons' search engine works far better with short, concrete noun
    phrases than long descriptive sentences (e.g. "SI base units" finds
    matches; "International System of Units seven SI base units
    infographic" often does not). This tries several queries, from most
    to least specific, and returns the first usable match:
      1. the full search_description as given
      2. the first 4 words of search_description
      3. the topic label, if provided
      4. the first 2 words of search_description
    """
    candidates = []
    if search_description and search_description.strip():
        candidates.append(search_description.strip())
        short = _shorten_query(search_description, 4)
        if short and short.lower() != search_description.strip().lower():
            candidates.append(short)
    if topic and topic.strip():
        candidates.append(topic.strip())
    if search_description and search_description.strip():
        shortest = _shorten_query(search_description, 2)
        if shortest:
            candidates.append(shortest)

    seen = set()
    for query in candidates:
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)

        results = _search_commons_files(query, limit=5)
        for result in results:
            title = result.get("title", "")
            info = _get_file_info(title)
            if info and info.get("full_url"):
                return info
    return None
