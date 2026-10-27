from fastapi.testclient import TestClient

from app.main import app
import app.routes.likha as likha_route
from tests.conftest import fake_student_profile

client = TestClient(app)


def _patch_owned_answer(monkeypatch, profile=None, history=None):
    monkeypatch.setattr(
        likha_route,
        "_get_profile",
        lambda user_id: profile or fake_student_profile(role="student"),
    )
    monkeypatch.setattr(
        likha_route,
        "_load_owned_history_answer",
        lambda history_id, profile_id: history
        if history is not None
        else {
            "id": history_id,
            "answer": "A shadow is dark because light is blocked.",
            "source_type": "DOUBT_KB",
        },
    )


def test_speech_request_rejects_arbitrary_client_answer_text():
    """The request contract must never accept a client-provided answer body."""
    response = client.post(
        "/api/likha/speak-doubt-answer",
        json={"answer_text": "Read this arbitrary text", "language": "en-IN"},
    )

    assert response.status_code == 422


def test_student_can_speak_only_owned_saved_answer(monkeypatch):
    _patch_owned_answer(monkeypatch)
    monkeypatch.setattr(
        likha_route,
        "_generate_audio_data_url",
        lambda text, voice: "data:audio/mpeg;base64,ZmFrZQ==",
    )

    response = client.post(
        "/api/likha/speak-doubt-answer",
        json={"history_id": "history-1", "language": "en-IN"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["voice"] == "en-IN-NeerjaNeural"
    assert "shadow is dark" in response.json()["spoken_text"]


def test_student_cannot_speak_another_students_history(monkeypatch):
    _patch_owned_answer(monkeypatch, history=None)
    monkeypatch.setattr(
        likha_route,
        "_load_owned_history_answer",
        lambda history_id, profile_id: None,
    )

    response = client.post(
        "/api/likha/speak-doubt-answer",
        json={"history_id": "another-students-history"},
    )

    assert response.status_code == 404


def test_non_student_cannot_use_voice_tutor(monkeypatch):
    _patch_owned_answer(monkeypatch, profile=fake_student_profile(role="teacher"))

    response = client.post(
        "/api/likha/speak-doubt-answer",
        json={"history_id": "history-1"},
    )

    assert response.status_code == 403


def test_invalid_language_is_rejected(monkeypatch):
    _patch_owned_answer(monkeypatch)

    response = client.post(
        "/api/likha/speak-doubt-answer",
        json={"history_id": "history-1", "language": "fr-FR"},
    )

    assert response.status_code == 400


def test_tts_provider_failure_returns_browser_fallback_data(monkeypatch):
    _patch_owned_answer(monkeypatch)
    monkeypatch.setattr(
        likha_route,
        "_generate_audio_data_url",
        lambda text, voice: (_ for _ in ()).throw(RuntimeError("provider down")),
    )

    response = client.post(
        "/api/likha/speak-doubt-answer",
        json={"history_id": "history-1"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["audio_url"] is None
    assert "shadow is dark" in response.json()["spoken_text"]
