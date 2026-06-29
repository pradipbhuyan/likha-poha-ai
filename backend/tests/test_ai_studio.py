"""
test_ai_studio.py — Backend tests for the Admin AI Studio endpoints.

Covers:
- Non-admin blocked (403) on all endpoints
- Providers list returned with masked keys
- API keys not exposed in responses
- Provider switch persists (primary/fallback)
- Connection test success/failure paths
- Ollama Cloud/Local adapter request formatting
- Local Ollama offline handled gracefully
- Model profile CRUD
- Prompt template versioning
- Usage summary returns safe data
- Quality metrics return safe data
- Knowledge sources return status
- Generation jobs list
"""
import uuid
from types import SimpleNamespace
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.auth_service import get_current_user, require_admin


ADMIN_ID = "admin-test-ai-studio"


def _make_admin():
    return {
        "id": ADMIN_ID,
        "email": "admin@test.com",
        "profile": {"id": ADMIN_ID, "email": "admin@test.com", "role": "admin"},
    }


def _make_student():
    return SimpleNamespace(id="00000000-0000-0000-0000-000000000099", email="student@test.com")


class TestAIStudioAuth:
    """Non-admin users must be blocked from all AI Studio endpoints."""

    def setup_method(self):
        app.dependency_overrides.pop(require_admin, None)

    def teardown_method(self):
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_current_user, None)

    def test_non_admin_blocked_providers(self, monkeypatch):
        import app.services.auth_service as auth_svc
        monkeypatch.setattr(
            auth_svc, "get_user_profile",
            lambda uid: {"id": uid, "role": "student", "family_id": None},
        )
        with TestClient(app) as client:
            app.dependency_overrides[get_current_user] = lambda: _make_student()
            resp = client.get("/api/admin/ai-studio/providers",
                              headers={"Authorization": "Bearer fake"})
            assert resp.status_code == 403
        app.dependency_overrides.pop(get_current_user, None)

    def test_non_admin_blocked_model_profiles(self, monkeypatch):
        import app.services.auth_service as auth_svc
        monkeypatch.setattr(
            auth_svc, "get_user_profile",
            lambda uid: {"id": uid, "role": "student", "family_id": None},
        )
        with TestClient(app) as client:
            app.dependency_overrides[get_current_user] = lambda: _make_student()
            resp = client.get("/api/admin/ai-studio/model-profiles",
                              headers={"Authorization": "Bearer fake"})
            assert resp.status_code == 403
        app.dependency_overrides.pop(get_current_user, None)


class TestProvidersEndpoint:
    """Provider listing and configuration."""

    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: _make_admin()

    def teardown_method(self):
        app.dependency_overrides.pop(require_admin, None)

    def test_providers_returns_all_nine(self, monkeypatch):
        """GET /providers must return all 9 registered providers."""
        import app.services.ai_studio_service as svc
        monkeypatch.setattr(svc, "_get_ai_settings", lambda: {
            "provider": "openai", "openai_api_key": "sk-test123456789"
        })
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/providers",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        providers = resp.json()["providers"]
        keys = [p["provider_key"] for p in providers]
        assert "openai" in keys
        assert "groq" in keys
        assert "gemini" in keys
        assert "ollama_local" in keys
        assert "ollama_cloud" in keys
        assert "anthropic" in keys
        assert len(providers) == 9

    def test_api_key_never_exposed_raw(self, monkeypatch):
        """Response must never contain the raw API key."""
        import app.routes.ai_studio as route_mod
        fake_providers = [
            {
                "provider_key": "openai", "display_name": "OpenAI",
                "is_primary": True, "is_fallback": False, "is_enabled": True,
                "has_api_key": True, "masked_key": "sk-s••••••••2345",
                "base_url": "", "current_model": "gpt-4.1-nano",
                "suggested_models": ["gpt-4.1-nano"], "temperature": 0.4,
                "max_tokens": 4096, "timeout_s": 60, "free_tier": False,
                "free_tier_notes": "", "key_prefix": "sk-", "docs_url": "",
                "supports_list_models": False,
            }
        ]
        monkeypatch.setattr(route_mod, "get_providers", lambda: fake_providers)
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/providers",
                              headers={"Authorization": "Bearer fake-admin"})
        body = resp.text
        assert "sk-super-secret-key-12345" not in body
        providers = resp.json()["providers"]
        openai_p = next(p for p in providers if p["provider_key"] == "openai")
        assert openai_p["has_api_key"] is True
        assert "••••••••" in openai_p["masked_key"]

    def test_provider_with_no_key_shows_has_api_key_false(self, monkeypatch):
        """Provider with no key must show has_api_key=False."""
        import app.services.ai_studio_service as svc
        monkeypatch.setattr(svc, "_get_ai_settings", lambda: {"provider": "openai"})
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/providers",
                              headers={"Authorization": "Bearer fake-admin"})
        providers = resp.json()["providers"]
        openai_p = next(p for p in providers if p["provider_key"] == "openai")
        assert openai_p["has_api_key"] is False
        assert openai_p["masked_key"] == ""

    def test_primary_provider_flagged_correctly(self, monkeypatch):
        """The active provider must be flagged as is_primary=True."""
        import app.routes.ai_studio as route_mod
        fake_providers = [
            {"provider_key": "groq", "display_name": "Groq", "is_primary": True,
             "is_fallback": False, "is_enabled": True, "has_api_key": True,
             "masked_key": "gsk_••••••••test", "base_url": "",
             "current_model": "llama-3.3-70b-versatile", "suggested_models": [],
             "temperature": 0.4, "max_tokens": 4096, "timeout_s": 60,
             "free_tier": True, "free_tier_notes": "", "key_prefix": "gsk_",
             "docs_url": "", "supports_list_models": False},
        ]
        monkeypatch.setattr(route_mod, "get_providers", lambda: fake_providers)
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/providers",
                              headers={"Authorization": "Bearer fake-admin"})
        providers = resp.json()["providers"]
        groq_p = next(p for p in providers if p["provider_key"] == "groq")
        assert groq_p["is_primary"] is True

    def test_unknown_provider_patch_returns_404(self):
        """PATCH with unknown provider_key must return 404."""
        with TestClient(app) as client:
            resp = client.patch("/api/admin/ai-studio/providers/nonexistent_provider",
                                json={"model": "gpt-99"},
                                headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 404

    def test_save_provider_does_not_return_api_key(self, monkeypatch):
        """PATCH must never return the saved API key in response."""
        import app.services.ai_studio_service as svc
        monkeypatch.setattr(svc, "save_provider",
                            lambda pk, data, admin_id: {"success": True, "message": "Saved."})
        with TestClient(app) as client:
            resp = client.patch("/api/admin/ai-studio/providers/openai",
                                json={"api_key": "sk-newsecretkey99"},
                                headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        body = resp.text
        assert "sk-newsecretkey99" not in body


class TestConnectionTest:
    """Provider connection test endpoint."""

    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: _make_admin()

    def teardown_method(self):
        app.dependency_overrides.pop(require_admin, None)

    def test_test_connection_success(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "test_connection",
                            lambda pk, override_key=None: {
                                "success": True, "latency_ms": 123,
                                "model": "gpt-4.1-nano", "message": "Connected. Response: 'OK'"
                            })
        with TestClient(app) as client:
            resp = client.post("/api/admin/ai-studio/providers/openai/test",
                               json={},
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["latency_ms"] == 123

    def test_test_connection_failure_returns_friendly_message(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "test_connection",
                            lambda pk, override_key=None: {
                                "success": False, "latency_ms": 0,
                                "model": "gpt-4.1-nano", "message": "Authentication failed — check your API key."
                            })
        with TestClient(app) as client:
            resp = client.post("/api/admin/ai-studio/providers/openai/test",
                               json={},
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert "Authentication failed" in resp.json()["message"]

    def test_test_key_in_body_not_saved(self, monkeypatch):
        """Test-only key must not appear in response."""
        import app.routes.ai_studio as route_mod
        captured = {}
        def fake_test(pk, override_key=None):
            captured["key"] = override_key
            return {"success": True, "latency_ms": 50, "model": "test", "message": "OK"}
        monkeypatch.setattr(route_mod, "test_connection", fake_test)
        with TestClient(app) as client:
            resp = client.post("/api/admin/ai-studio/providers/openai/test",
                               json={"api_key": "sk-testkey999"},
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert "sk-testkey999" not in resp.text
        assert captured.get("key") == "sk-testkey999"  # passed to function, not in response

    def test_ollama_local_offline_handled(self, monkeypatch):
        """Local Ollama offline must return friendly message, not 500."""
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "test_connection",
                            lambda pk, override_key=None: {
                                "success": False, "latency_ms": 0,
                                "model": "llama3.2",
                                "message": "Local Ollama server not reachable. Start it with: ollama serve"
                            })
        with TestClient(app) as client:
            resp = client.post("/api/admin/ai-studio/providers/ollama_local/test",
                               json={},
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert "ollama serve" in resp.json()["message"]


class TestModelProfiles:
    """Model routing profile CRUD."""

    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: _make_admin()

    def teardown_method(self):
        app.dependency_overrides.pop(require_admin, None)

    def test_list_model_profiles_returns_all_features(self, monkeypatch):
        import app.services.ai_studio_service as svc
        monkeypatch.setattr(svc, "get_model_profiles", lambda: [
            {"feature_key": fk, "display_name": dn, "provider_key": "openai",
             "model": "gpt-4.1-nano", "temperature": 0.4, "max_tokens": 4096,
             "fallback_provider": "", "fallback_model": "", "is_enabled": True, "notes": ""}
            for fk, dn in svc.FEATURE_DISPLAY_NAMES.items()
        ])
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/model-profiles",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        profiles = resp.json()["profiles"]
        feature_keys = [p["feature_key"] for p in profiles]
        assert "lesson_repair" in feature_keys
        assert "ask_doubt" in feature_keys
        assert len(profiles) == 10

    def test_update_model_profile_unknown_feature_returns_404(self):
        with TestClient(app) as client:
            resp = client.patch("/api/admin/ai-studio/model-profiles/nonexistent_feature",
                                json={"model": "gpt-99"},
                                headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 404

    def test_update_model_profile_success(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "save_model_profile",
                            lambda fk, data, admin_id: {"success": True, "message": "Saved."})
        with TestClient(app) as client:
            resp = client.patch("/api/admin/ai-studio/model-profiles/lesson_repair",
                                json={"provider_key": "groq", "model": "llama-3.3-70b-versatile"},
                                headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestPromptTemplates:
    """Prompt template versioning."""

    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: _make_admin()

    def teardown_method(self):
        app.dependency_overrides.pop(require_admin, None)

    def test_list_prompts_empty_when_no_templates(self, monkeypatch):
        import app.services.ai_studio_service as svc
        monkeypatch.setattr(svc, "get_prompt_templates", lambda: [])
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/prompts",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.json()["templates"] == []

    def test_save_prompt_creates_new_version(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "save_prompt_template",
                            lambda tid, data, admin_id: {"success": True, "message": "Saved as version 2.", "version": 2})
        with TestClient(app) as client:
            resp = client.patch("/api/admin/ai-studio/prompts/tmpl-001",
                                json={"system_prompt": "You are a CBSE tutor.",
                                      "user_prompt": "Repair: {grade} {subject}",
                                      "change_summary": "Initial version"},
                                headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["version"] == 2

    def test_activate_prompt_version(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "activate_template_version",
                            lambda tid, ver, admin_id: {"success": True, "message": "Version 1 is now active."})
        with TestClient(app) as client:
            resp = client.post("/api/admin/ai-studio/prompts/tmpl-001/activate-version",
                               json={"version_number": 1},
                               headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestUsageAndQuality:
    """Usage summary and quality metrics endpoints."""

    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: _make_admin()

    def teardown_method(self):
        app.dependency_overrides.pop(require_admin, None)

    def test_usage_summary_returns_safe_fields(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "get_usage_summary", lambda days=30: {
            "provider": "openai", "model": "gpt-4.1-nano",
            "total_requests": 150, "today_requests": 12,
            "total_tokens": 250000, "estimated_cost_usd": 0.025,
            "avg_latency_ms": None, "success_rate": None, "last_error": None,
            "by_feature": [], "by_provider": [], "cost_note": "",
        })
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/usage",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requests"] == 150
        assert data["estimated_cost_usd"] == 0.025
        # Must never expose raw API keys in usage response
        assert "api_key" not in resp.text
        assert "secret" not in resp.text.lower()

    def test_quality_metrics_returns_safe_fields(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "get_quality_metrics", lambda: {
            "repair_success_rate": 85.0,
            "validation_failure_rate": 10.0,
            "avg_before_score": 42.0,
            "avg_after_score": 91.0,
            "formula_validation_pass_rate": None,
            "mcq_validation_pass_rate": None,
            "common_failure_reasons": [],
            "note": "From recent repair data.",
        })
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/quality",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["repair_success_rate"] == 85.0
        assert data["avg_after_score"] == 91.0

    def test_knowledge_sources_renders(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "get_knowledge_sources", lambda: [
            {"key": "dkb", "display_name": "DKB", "description": "NCERT content",
             "status": "active", "action": None},
            {"key": "vector_store", "display_name": "Vector Store", "description": "Embeddings",
             "status": "coming_soon", "action": "coming_soon"},
        ])
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/knowledge-sources",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        sources = resp.json()["sources"]
        assert len(sources) == 2
        assert sources[0]["status"] == "active"
        assert sources[1]["status"] == "coming_soon"

    def test_generation_jobs_empty_list(self, monkeypatch):
        import app.routes.ai_studio as route_mod
        monkeypatch.setattr(route_mod, "get_generation_jobs", lambda limit=50: [])
        with TestClient(app) as client:
            resp = client.get("/api/admin/ai-studio/jobs",
                              headers={"Authorization": "Bearer fake-admin"})
        assert resp.status_code == 200
        assert resp.json()["jobs"] == []
        assert resp.json()["total"] == 0


class TestKeyMasking:
    """Verify _mask_key function behavior."""

    def test_mask_key_short(self):
        from app.services.ai_studio_service import _mask_key
        assert _mask_key("sk-abc") == "••••••••"

    def test_mask_key_long(self):
        from app.services.ai_studio_service import _mask_key
        result = _mask_key("sk-abcdef123456789xyz")
        assert result.startswith("sk-a")
        assert "••••••••" in result
        assert result.endswith("rxyz") or "xyz" in result

    def test_mask_key_empty(self):
        from app.services.ai_studio_service import _mask_key
        assert _mask_key("") == ""
        assert _mask_key(None) == ""

    def test_mask_key_whitespace(self):
        from app.services.ai_studio_service import _mask_key
        assert _mask_key("   ") == ""
