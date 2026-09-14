"""
Mobile OTA Update Check
========================
Self-hosted "updateUrl" endpoint for the @capgo/capacitor-updater plugin
running inside the Android app. The plugin POSTs this exact request shape
on every app foreground (auto-update mode "atBackground") — verified
directly against the plugin's native Android source
(CapgoUpdater.java/CapacitorUpdaterPlugin.java, v8.51.15), not just its
docs, since a wrong field name here fails silently on-device.

Response contract (also verified against the native source):
  - Update available:  {"version": ..., "url": ..., "checksum": ...}
  - No update needed:  {"kind": "up_to_date", ...}   — "kind" is the field
    the plugin actually branches on; omitting "url" alone is NOT enough and
    is treated as an error by the native code.
  - Gated (native shell too old for this bundle): {"kind": "blocked", ...}
  - Any other/missing "kind" value is treated as "failed".

No auth — the plugin calls this before the user has necessarily logged in,
and the response reveals nothing sensitive (just a public bundle URL).
Rate-limited per IP instead (see MOBILE_OTA_CHECK_LIMITER).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.mobile_ota_service import get_latest_release
from app.services.rate_limit_service import MOBILE_OTA_CHECK_LIMITER, rate_limit_dependency

router = APIRouter()


class MobileOtaCheckRequest(BaseModel):
    platform: str = "android"
    device_id: str = ""
    app_id: str = ""
    custom_id: str = ""
    version_build: str = ""
    version_code: str = ""
    version_os: str = ""
    version_name: str = ""
    plugin_version: str = ""
    is_emulator: bool = False
    is_prod: bool = True


@router.post("/check")
async def check_mobile_ota_update(
    data: MobileOtaCheckRequest,
    _rl=Depends(rate_limit_dependency(MOBILE_OTA_CHECK_LIMITER)),
):
    platform = (data.platform or "android").strip().lower()

    release = get_latest_release(platform, channel="production")
    if not release:
        return {"kind": "up_to_date", "message": "No release published yet"}

    try:
        client_version_code = int(str(data.version_code).strip() or "0")
    except ValueError:
        client_version_code = 0

    if client_version_code < int(release["min_version_code"]):
        return {
            "kind": "blocked",
            "error": "native_shell_too_old",
            "message": "Update the app from the Play Store to receive further content updates.",
        }

    if data.version_name == release["version"]:
        return {"kind": "up_to_date", "message": "No new version available"}

    response = {"version": release["version"], "url": release["bundle_url"]}
    if release.get("checksum"):
        response["checksum"] = release["checksum"]
    return response
