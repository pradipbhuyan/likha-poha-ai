#!/usr/bin/env python3
"""
Publish a Mobile OTA Release
=============================================================================
Zips a built frontend (frontend/dist), uploads it to Supabase Storage, and
records it in mobile_ota_releases so the Android app's self-hosted
@capgo/capacitor-updater check (POST /api/mobile/ota/check) starts serving
it on the next app foreground.

Prerequisite: build the frontend first —
  cd frontend && npm run build

--min-version-code is required and is not a formality: it's the floor on
the native shell's Android versionCode (frontend/android/app/build.gradle)
that this bundle is safe to run on. Bump it whenever the bundle starts
relying on something only a newer native build provides (a new Capacitor
plugin, a new native permission, etc.) — an older installed APK that
doesn't have that plugin compiled in would otherwise silently break instead
of just staying on its current bundle. When in doubt, use the versionCode
of the oldest native build still known to be compatible with this bundle.

Usage:
    cd backend
    python3 scripts/publish_mobile_ota_release.py --min-version-code 55
    python3 scripts/publish_mobile_ota_release.py --min-version-code 55 --version 2026.09.14.1
    python3 scripts/publish_mobile_ota_release.py --min-version-code 55 --notes "Fix X" --dry-run
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.mobile_ota_service import (  # noqa: E402
    build_bundle_zip,
    record_release,
    sha256_hex,
    upload_bundle,
)

DEFAULT_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a self-hosted mobile OTA release")
    parser.add_argument("--dist-dir", default=str(DEFAULT_DIST_DIR), help="Path to the built frontend (default: frontend/dist)")
    parser.add_argument("--platform", default="android", choices=["android", "ios"])
    parser.add_argument("--channel", default="production")
    parser.add_argument("--version", default=None, help="Defaults to a UTC timestamp, e.g. 2026.09.14.1430")
    parser.add_argument("--min-version-code", type=int, required=True, help="Floor on the native Android versionCode this bundle requires")
    parser.add_argument("--notes", default="")
    parser.add_argument("--dry-run", action="store_true", help="Build and checksum the bundle but don't upload or record it")
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir).expanduser()
    if not dist_dir.is_dir():
        print(f"ERROR: {dist_dir} does not exist. Run `npm run build` in frontend/ first.")
        sys.exit(1)

    version = args.version or datetime.now(timezone.utc).strftime("%Y.%m.%d.%H%M")

    print("\n  Publishing mobile OTA release")
    print(f"  Platform: {args.platform}   Channel: {args.channel}   Version: {version}")
    print(f"  Min native versionCode: {args.min_version_code}")
    print(f"  Source: {dist_dir}\n")

    print("  Zipping bundle...")
    zip_bytes = build_bundle_zip(str(dist_dir))
    checksum = sha256_hex(zip_bytes)
    print(f"  Bundle: {len(zip_bytes):,} bytes, sha256={checksum}")

    if args.dry_run:
        print("\n  [DRY RUN] Would upload and record this release. Nothing written.\n")
        return

    print("  Uploading to Supabase Storage...")
    bundle_url = upload_bundle(args.platform, version, zip_bytes)
    print(f"  Uploaded: {bundle_url}")

    print("  Recording release (deactivating any previous active release)...")
    row = record_release(
        platform=args.platform,
        version=version,
        bundle_url=bundle_url,
        checksum=checksum,
        min_version_code=args.min_version_code,
        channel=args.channel,
        notes=args.notes,
    )

    print(f"\n  Done. Release {row['version']} is now live for {args.platform}/{args.channel}.")
    print("  Installed apps will pick it up on their next foreground check.\n")


if __name__ == "__main__":
    main()
