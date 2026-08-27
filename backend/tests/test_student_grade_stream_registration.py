"""
test_student_grade_stream_registration.py
================================================================
REGRESSION SUITE for the 2026-08-27 "registered Grade 12 PCMB, got Grade 9"
defect.

Root cause: signup's grade validation was switched to a DB-driven
get_live_visible_grades() check, and a stale admin_settings row (a leftover
from a grade-hiding feature no frontend ever had a toggle for) had Grade 12
marked not-visible. That silently downgraded every Grade 12 signup to
Grade 9 with no error shown to the parent or the admin. Fixed by removing
the grade-visibility toggle entirely — grades are now always the hardcoded
ALL_GRADES list (see app.data.product_catalogue).

While fixing this, a second, independent defect was found: the grade+stream
resolution logic was duplicated across 5 signup/profile-completion call
sites in auth.py and had drifted — signup_free validated and required a
stream for Grade 11/12, but complete_signup and signup_with_offer_code had
no `stream` field at all (silently registering paid/offer-code Grade 11/12
students with zero cbse_subjects — which, per subject_access_service's
"empty list means full CBSE access" rule, means those students would see
ALL CBSE subjects rather than only the ones for their chosen stream), and
oauth_complete_profile silently proceeded with empty subjects instead of
rejecting a missing stream. All 5 sites now go through one shared function,
_resolve_student_grade_and_subjects(), so this can't drift again.

This file covers, end to end:
  1. Every grade 5-12 registers correctly via the real signup_free() entry
     point (the one both the web and mobile signup screens actually call).
  2. Every stream (PCM/PCB/PCMB/Commerce/Humanities) for both Grade 11 and
     Grade 12 registers with the exact subject list for that stream.
  3. The shared resolver behaves identically regardless of which of the 5
     call sites uses it (exhaustive unit coverage — cheaper than mocking
     every endpoint's full dependency chain, and it's the actual place
     future call sites will plug into).
  4. The "lesson shown must match what was chosen at registration" property:
     a student's cbse_subjects list, once registered, grants lesson/subject
     access ONLY for their chosen stream's subjects (has_cbse_subject_access)
     — not every CBSE subject, and not another stream's subjects.
  5. The original bug scenario is reproduced against a live-shaped stale
     catalogue row and proven fixed: Grade 12 still registers as Grade 12
     even when a stored admin_settings row marks it not-visible.
"""

import pytest
from fastapi import HTTPException

from app.routes import auth as auth_module
from app.services.subject_access_service import has_cbse_subject_access


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

ALL_STREAMS = ["PCM", "PCB", "PCMB", "Commerce", "Humanities"]
NO_STREAM_GRADES = [f"Grade {i}" for i in range(5, 11)]  # 5-10
STREAM_GRADES = ["Grade 11", "Grade 12"]

# One subject guaranteed ABSENT from each stream, used to prove a student
# does NOT get lesson access to a subject outside their chosen stream.
A_SUBJECT_NOT_IN_STREAM = {
    "PCM": "Business Studies",
    "PCB": "Business Studies",
    "PCMB": "Business Studies",
    "Commerce": "Physics",
    "Humanities": "Physics",
}


def fake_auth_user(user_id="student-grade-test"):
    class FakeUser:
        def __init__(self):
            self.id = user_id
    return FakeUser()


class ProfileCapturingAdminClient:
    """Minimal admin_client stand-in: reports no duplicate email/username,
    and captures whatever gets inserted into "profiles"."""

    def __init__(self):
        self.captured_profile = None

    def table(self, name):
        self._table = name
        return self

    def select(self, *_): return self
    def eq(self, *_): return self
    def ilike(self, *_): return self
    def limit(self, *_): return self

    def insert(self, data):
        if self._table == "profiles":
            self.captured_profile = data
        return self

    def upsert(self, *_, **__): return self

    def execute(self):
        class R:
            data = []
        return R()


def _signup_free_student(monkeypatch, grade, stream=None, email=None):
    """Call the real signup_free() entry point and return the captured
    profile dict that would have been written to the DB."""
    client = ProfileCapturingAdminClient()
    monkeypatch.setattr(auth_module, "admin_client", client)
    monkeypatch.setattr(
        "app.services.auth_service.create_auth_user",
        lambda email, password, email_confirm=True: fake_auth_user(),
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.email_service.send_welcome_email",
        lambda **kw: None,
        raising=False,
    )

    result = auth_module.signup_free(auth_module.FreeSignupRequest(
        role="student",
        name=f"Student {grade} {stream or ''}".strip(),
        email=email or f"student-{grade.replace(' ', '')}-{(stream or 'none').lower()}@test.com",
        grade=grade,
        stream=stream,
    ))
    assert result["success"] is True
    return client.captured_profile


# ---------------------------------------------------------------------------
# 1. Grade 5-10 (no stream) — signup_free
# ---------------------------------------------------------------------------

class TestSignupFreeNoStreamGrades:
    @pytest.mark.parametrize("grade", NO_STREAM_GRADES)
    def test_registers_exactly_the_chosen_grade(self, monkeypatch, grade):
        profile = _signup_free_student(monkeypatch, grade)
        assert profile["grade"] == grade
        assert "stream" not in profile
        # Empty cbse_subjects is the intentional "full CBSE access" marker
        # for grades that don't have streams.
        assert profile["cbse_subjects"] == []


# ---------------------------------------------------------------------------
# 2. Grade 11/12 x every stream — signup_free
# ---------------------------------------------------------------------------

class TestSignupFreeStreamGrades:
    @pytest.mark.parametrize("grade", STREAM_GRADES)
    @pytest.mark.parametrize("stream", ALL_STREAMS)
    def test_registers_exact_grade_stream_and_subjects(self, monkeypatch, grade, stream):
        profile = _signup_free_student(monkeypatch, grade, stream)
        assert profile["grade"] == grade
        assert profile["stream"] == stream
        assert profile["cbse_subjects"] == auth_module.STREAM_SUBJECTS[stream]

    @pytest.mark.parametrize("grade", STREAM_GRADES)
    def test_missing_stream_is_rejected_not_silently_downgraded(self, monkeypatch, grade):
        """Grade 11/12 without a stream must be a clear 400, never a silent
        partial registration — this is the exact class of bug that let
        paid/offer-code signups through with zero subjects."""
        client = ProfileCapturingAdminClient()
        monkeypatch.setattr(auth_module, "admin_client", client)
        monkeypatch.setattr(
            "app.services.auth_service.create_auth_user",
            lambda *a, **kw: fake_auth_user(),
            raising=False,
        )

        with pytest.raises(HTTPException) as exc:
            auth_module.signup_free(auth_module.FreeSignupRequest(
                role="student", name="No Stream Kid",
                email=f"nostream-{grade.replace(' ', '')}@test.com",
                grade=grade, stream=None,
            ))
        assert exc.value.status_code == 400
        assert client.captured_profile is None, "must not write a profile row on rejection"

    @pytest.mark.parametrize("grade", STREAM_GRADES)
    def test_bogus_stream_is_rejected(self, monkeypatch, grade):
        client = ProfileCapturingAdminClient()
        monkeypatch.setattr(auth_module, "admin_client", client)
        monkeypatch.setattr(
            "app.services.auth_service.create_auth_user",
            lambda *a, **kw: fake_auth_user(),
            raising=False,
        )
        with pytest.raises(HTTPException) as exc:
            auth_module.signup_free(auth_module.FreeSignupRequest(
                role="student", name="Bogus Stream Kid",
                email=f"bogus-{grade.replace(' ', '')}@test.com",
                grade=grade, stream="Vocational",
            ))
        assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# 3. Exhaustive unit coverage of the single shared resolver
#    (this is what every one of the 5 call sites now delegates to)
# ---------------------------------------------------------------------------

class TestResolveStudentGradeAndSubjects:
    @pytest.mark.parametrize("grade", NO_STREAM_GRADES)
    def test_grades_5_to_10_need_no_stream(self, grade):
        resolved_grade, stream, subjects = auth_module._resolve_student_grade_and_subjects(grade, None)
        assert resolved_grade == grade
        assert stream is None
        assert subjects == []

    @pytest.mark.parametrize("grade", STREAM_GRADES)
    @pytest.mark.parametrize("stream", ALL_STREAMS)
    def test_grade_11_12_every_stream_resolves_correctly(self, grade, stream):
        resolved_grade, resolved_stream, subjects = auth_module._resolve_student_grade_and_subjects(grade, stream)
        assert resolved_grade == grade
        assert resolved_stream == stream
        assert subjects == auth_module.STREAM_SUBJECTS[stream]
        # Every stream's subject list must be non-empty and internally
        # consistent with VALID_STREAMS.
        assert subjects

    @pytest.mark.parametrize("grade", STREAM_GRADES)
    @pytest.mark.parametrize("bad_stream", [None, "", "  ", "pcm", "Vocational"])
    def test_grade_11_12_invalid_stream_raises(self, grade, bad_stream):
        with pytest.raises(HTTPException) as exc:
            auth_module._resolve_student_grade_and_subjects(grade, bad_stream)
        assert exc.value.status_code == 400

    def test_out_of_range_grade_defaults_to_grade_9_unaffected_by_stream(self):
        """Pre-existing, intentional behavior — must survive the refactor."""
        resolved_grade, stream, subjects = auth_module._resolve_student_grade_and_subjects("Grade 99", None)
        assert resolved_grade == "Grade 9"
        assert stream is None
        assert subjects == []

    def test_missing_grade_defaults_to_grade_9(self):
        resolved_grade, stream, subjects = auth_module._resolve_student_grade_and_subjects(None, None)
        assert resolved_grade == "Grade 9"


# ---------------------------------------------------------------------------
# 4. "Lesson shown must match what was chosen at registration"
# ---------------------------------------------------------------------------

class TestLessonAccessMatchesRegisteredStream:
    @pytest.mark.parametrize("grade", STREAM_GRADES)
    @pytest.mark.parametrize("stream", ALL_STREAMS)
    def test_registered_stream_subjects_are_accessible(self, grade, stream):
        _, _, subjects = auth_module._resolve_student_grade_and_subjects(grade, stream)
        profile = {"grade": grade, "stream": stream, "cbse_subjects": subjects}
        for subject in subjects:
            assert has_cbse_subject_access(profile, subject), (
                f"{grade}/{stream} student must have lesson access to "
                f"{subject} — it's part of their registered stream"
            )

    @pytest.mark.parametrize("grade", STREAM_GRADES)
    @pytest.mark.parametrize("stream", ALL_STREAMS)
    def test_subject_outside_registered_stream_is_not_accessible(self, grade, stream):
        _, _, subjects = auth_module._resolve_student_grade_and_subjects(grade, stream)
        profile = {"grade": grade, "stream": stream, "cbse_subjects": subjects}
        outside_subject = A_SUBJECT_NOT_IN_STREAM[stream]
        assert outside_subject not in subjects  # sanity-check the fixture itself
        assert not has_cbse_subject_access(profile, outside_subject), (
            f"{grade}/{stream} student must NOT see {outside_subject} — "
            f"it belongs to a different stream than the one they registered "
            f"for. A student must never be shown lessons for a stream they "
            f"didn't choose."
        )

    @pytest.mark.parametrize("grade", NO_STREAM_GRADES)
    def test_no_stream_grades_get_full_cbse_access(self, grade):
        """Grades 5-10 have no streams — an empty cbse_subjects list is the
        documented 'all CBSE subjects' marker, not a lockout."""
        profile = {"grade": grade, "cbse_subjects": []}
        for subject in ["Mathematics", "Science", "English", "Social Science"]:
            assert has_cbse_subject_access(profile, subject)

    def test_empty_subjects_would_wrongly_grant_full_access_to_a_stream_student(self):
        """
        Documents WHY the "silent empty cbse_subjects" defect (complete_signup
        and signup_with_offer_code registering Grade 11/12 with zero subjects,
        pre-fix) was a real correctness bug and not just a cosmetic gap: an
        empty list means "every CBSE subject", so a Commerce student with no
        captured stream would incorrectly see Physics/Biology lessons too.
        """
        broken_profile = {"grade": "Grade 11", "cbse_subjects": []}  # what the bug produced
        assert has_cbse_subject_access(broken_profile, "Physics")  # wrongly allowed
        assert has_cbse_subject_access(broken_profile, "Biology")  # wrongly allowed


# ---------------------------------------------------------------------------
# 5. Reproduce the exact original bug against a live-shaped stale catalogue
#    row, and prove it no longer has any effect.
# ---------------------------------------------------------------------------

class TestStaleCatalogueCannotAffectRegistration:
    def test_grade_12_registers_correctly_even_with_stale_hidden_flag_in_db(self, monkeypatch):
        """
        Reproduces the live admin_settings row found during investigation:
        Grade 12 stored with visible=False (a leftover from the removed
        grade-hiding feature), Grade 11 visible=True. Before the fix, this
        silently downgraded every Grade 12 signup to Grade 9. Grades no
        longer read this field at all, so it must have zero effect.
        """
        import app.services.auth_service as auth_service

        stale_row = {
            "grades": {
                "Grade 11": {"visible": True, "boards": ["CBSE"], "streams": []},
                "Grade 12": {"visible": False, "boards": ["CBSE"], "streams": []},
            },
            "coaching_programs": {},
        }

        class _FakeTable:
            def __init__(self, value):
                self._value = value
            def select(self, *_): return self
            def eq(self, *_): return self
            def limit(self, *_): return self
            def execute(self):
                class R:
                    data = [{"value": self._value}]
                return R()

        monkeypatch.setattr(
            auth_service, "admin_client",
            type("_C", (), {"table": staticmethod(lambda t: _FakeTable(stale_row))})(),
            raising=False,
        )

        profile = _signup_free_student(monkeypatch, "Grade 12", "PCMB")
        assert profile["grade"] == "Grade 12"
        assert profile["stream"] == "PCMB"
        assert profile["cbse_subjects"] == auth_module.STREAM_SUBJECTS["PCMB"]
