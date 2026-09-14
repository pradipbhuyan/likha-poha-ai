"""
Tests for POST /api/mobile/ota/check — the self-hosted updateUrl endpoint
the @capgo/capacitor-updater plugin polls from the Android app.

Mirrors the mocking style in test_teacher_lesson_plan_edits.py: monkeypatch
the service-layer function imported into app.routes.mobile_ota (a
Supabase-backed service, no local equivalent to exercise directly).

The response shapes here are load-bearing, not stylistic — verified
directly against the plugin's native Android source (CapgoUpdater.java /
CapacitorUpdaterPlugin.java, @capgo/capacitor-updater v8.51.15):
  - "kind" must be exactly "up_to_date", "blocked", or "failed"; any other
    value (including a missing key alongside a missing "url") is treated
    as a failure by the native code.
  - Omitting "url" alone, without a recognized "kind", is NOT a valid
    "no update" signal — it's treated as an error ("Error no url or wrong
    format") that logs and aborts, not a clean no-op.
"""
from fastapi.testclient import TestClient

from app.main import app
import app.routes.mobile_ota as mobile_ota_route

client = TestClient(app)

RELEASE = {
    "platform": "android",
    "channel": "production",
    "version": "2026.09.14.1200",
    "bundle_url": "https://example.supabase.co/storage/v1/object/public/mobile-ota-bundles/android/2026.09.14.1200.zip",
    "checksum": "abc123",
    "min_version_code": 56,
    "is_active": True,
}


def _check(monkeypatch, release, **body):
    monkeypatch.setattr(mobile_ota_route, "get_latest_release", lambda platform, channel="production": release)
    payload = {"platform": "android", "version_code": "56", "version_name": "builtin", **body}
    return client.post("/api/mobile/ota/check", json=payload)


class TestNoReleasePublished:
    def test_reports_up_to_date_not_an_error(self, monkeypatch):
        r = _check(monkeypatch, None)
        assert r.status_code == 200
        assert r.json()["kind"] == "up_to_date"


class TestNativeShellTooOld:
    def test_below_min_version_code_is_blocked_not_failed(self, monkeypatch):
        r = _check(monkeypatch, RELEASE, version_code="55")
        body = r.json()
        assert r.status_code == 200
        assert body["kind"] == "blocked"
        assert body["error"] == "native_shell_too_old"

    def test_exactly_at_min_version_code_is_eligible(self, monkeypatch):
        r = _check(monkeypatch, RELEASE, version_code="56", version_name="builtin")
        body = r.json()
        assert "kind" not in body
        assert body["version"] == RELEASE["version"]


class TestAlreadyUpToDate:
    def test_matching_version_name_reports_up_to_date(self, monkeypatch):
        r = _check(monkeypatch, RELEASE, version_code="60", version_name=RELEASE["version"])
        assert r.json()["kind"] == "up_to_date"


class TestUpdateAvailable:
    def test_returns_version_url_and_checksum(self, monkeypatch):
        r = _check(monkeypatch, RELEASE, version_code="60", version_name="builtin")
        body = r.json()
        assert body["version"] == RELEASE["version"]
        assert body["url"] == RELEASE["bundle_url"]
        assert body["checksum"] == RELEASE["checksum"]
        assert "kind" not in body

    def test_omits_checksum_key_when_release_has_none(self, monkeypatch):
        release = {**RELEASE, "checksum": ""}
        r = _check(monkeypatch, release, version_code="60", version_name="builtin")
        body = r.json()
        assert "checksum" not in body
        assert body["url"] == RELEASE["bundle_url"]
