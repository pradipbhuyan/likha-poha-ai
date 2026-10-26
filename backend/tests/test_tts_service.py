import ssl

import pytest

from app.services import tts_service


def test_edge_tts_uses_library_default_ssl_context_without_custom_bundle(
    monkeypatch,
):
    """Normal deployments retain Edge TTS's own verified SSL configuration."""
    default_context = object()
    monkeypatch.setattr(tts_service, "EDGE_TTS_CA_BUNDLE", "")
    monkeypatch.setattr(tts_service.edge_tts_communicate, "_SSL_CTX", default_context)

    assert tts_service._get_edge_tts_ssl_context() is default_context


def test_edge_tts_uses_verified_context_for_configured_ca_bundle(
    monkeypatch, tmp_path
):
    """A configured corporate CA bundle is loaded without disabling TLS checks."""
    bundle_path = tmp_path / "corporate-ca.pem"
    bundle_path.write_text(
        "-----BEGIN CERTIFICATE-----\ninvalid-test-certificate\n-----END CERTIFICATE-----\n"
    )
    captured = {}

    def fake_create_default_context(*, cafile):
        captured["cafile"] = cafile
        return "verified-context"

    monkeypatch.setattr(tts_service, "EDGE_TTS_CA_BUNDLE", str(bundle_path))
    monkeypatch.setattr(ssl, "create_default_context", fake_create_default_context)

    assert tts_service._get_edge_tts_ssl_context() == "verified-context"
    assert captured["cafile"] == str(bundle_path)


def test_edge_tts_rejects_missing_configured_ca_bundle(monkeypatch, tmp_path):
    """A bad CA path fails explicitly instead of silently weakening TLS."""
    missing_bundle = tmp_path / "missing-ca.pem"
    monkeypatch.setattr(tts_service, "EDGE_TTS_CA_BUNDLE", str(missing_bundle))

    with pytest.raises(RuntimeError, match="existing PEM certificate bundle"):
        tts_service._get_edge_tts_ssl_context()
