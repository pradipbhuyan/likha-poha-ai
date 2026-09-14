"""
mobile_ota_service.py — Self-hosted OTA bundle releases for the Capacitor
Android app, backed by the @capgo/capacitor-updater plugin (updateUrl mode).

Storage: Supabase Storage (bucket "mobile-ota-bundles", public), same
admin_client pattern as audio_cache_service.py / rag_visual_service.py.
DB tracking: mobile_ota_releases table — one row per published release,
newest-first, only the latest `is_active` row per (platform, channel) is
ever served.

Populate via: backend/scripts/publish_mobile_ota_release.py
"""

import hashlib
import io
import os
import zipfile

from app.services.auth_service import admin_client
from app.services.logger_service import get_logger

_log = get_logger("mobile_ota_service")

BUCKET_NAME = os.getenv("MOBILE_OTA_BUCKET", "mobile-ota-bundles")

TABLE_NAME = "mobile_ota_releases"


def get_latest_release(platform: str, channel: str = "production") -> dict | None:
    """
    Return the latest active release row for this platform/channel, or None
    if nothing has been published yet.
    """
    try:
        resp = (
            admin_client.table(TABLE_NAME)
            .select("*")
            .eq("platform", platform)
            .eq("channel", channel)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        _log.error("mobile_ota.get_latest_release_failed", platform=platform, channel=channel, error=str(exc)[:200])
        return None

    rows = resp.data or []
    return rows[0] if rows else None


def _ensure_bucket_exists() -> None:
    try:
        admin_client.storage.get_bucket(BUCKET_NAME)
        return
    except Exception:
        pass

    try:
        admin_client.storage.create_bucket(
            BUCKET_NAME,
            options={
                "public": True,
                "file_size_limit": 50 * 1024 * 1024,  # 50MB — plenty for a JS/CSS/asset bundle
                "allowed_mime_types": ["application/zip"],
            },
        )
    except Exception as exc:
        raise RuntimeError(f"Could not create or find Supabase Storage bucket '{BUCKET_NAME}': {exc}") from exc


def build_bundle_zip(dist_dir: str) -> bytes:
    """
    Zip the CONTENTS of a Vite build output directory (index.html at the zip
    root, not nested under a wrapping folder) — the layout
    @capgo/capacitor-updater requires for a self-hosted bundle.
    """
    index_path = os.path.join(dist_dir, "index.html")
    if not os.path.isfile(index_path):
        raise ValueError(f"No index.html found at the root of {dist_dir} — did you run `npm run build`?")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(dist_dir):
            for name in files:
                abs_path = os.path.join(root, name)
                rel_path = os.path.relpath(abs_path, dist_dir)
                zf.write(abs_path, rel_path)
    return buf.getvalue()


def upload_bundle(platform: str, version: str, zip_bytes: bytes) -> str:
    """Upload the bundle zip to Supabase Storage and return its public URL."""
    _ensure_bucket_exists()
    file_path = f"{platform}/{version}.zip"

    try:
        admin_client.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=zip_bytes,
            file_options={"content-type": "application/zip", "upsert": "true"},
        )
    except Exception as exc:
        raise RuntimeError(f"Unable to upload OTA bundle to Supabase Storage bucket '{BUCKET_NAME}': {exc}") from exc

    return admin_client.storage.from_(BUCKET_NAME).get_public_url(file_path)


def record_release(
    platform: str,
    version: str,
    bundle_url: str,
    checksum: str,
    min_version_code: int,
    channel: str = "production",
    notes: str = "",
) -> dict:
    """
    Insert a new release row and deactivate every previous active release for
    the same (platform, channel) so exactly one row is ever served.
    """
    try:
        admin_client.table(TABLE_NAME).update({"is_active": False}).eq("platform", platform).eq(
            "channel", channel
        ).eq("is_active", True).execute()

        resp = (
            admin_client.table(TABLE_NAME)
            .insert(
                {
                    "platform": platform,
                    "channel": channel,
                    "version": version,
                    "bundle_url": bundle_url,
                    "checksum": checksum,
                    "min_version_code": min_version_code,
                    "is_active": True,
                    "notes": notes,
                }
            )
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(f"Unable to record OTA release in '{TABLE_NAME}': {exc}") from exc

    return resp.data[0]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
