"""
test_product_catalogue_service.py — TD-14 regression coverage
================================================================
load_product_catalogue() must merge a stored admin_settings row onto the
current hardcoded defaults, not return the stored row verbatim — a real
stale row (coaching_programs keyed "JEE"/"NEET"/"CUET", pre-dating the
2026-08-26 rename to "jee_main"/"neet_ug"/"cuet_ug" + the sat/ielts/toefl
additions) already existed live and would otherwise have made every exam
read as hidden the instant the /status endpoint started trusting this data.

Tests:
  - No DB row -> hardcoded defaults, all 6 exams visible
  - Stale/partial stored row (old exam keys, missing new ones) -> healed to
    the current 6 keys, all default-visible, old keys dropped
  - Stored row that already has a current key with visible=False -> that
    admin choice is honored, not overridden
  - Stored row's "grades" section is never consulted -> the hardcoded
    ALL_GRADES list is always authoritative, even if a stored row carries
    a leftover "visible: False" from the removed grade-hiding feature
"""

import copy

from app.data.product_catalogue import DEFAULT_PRODUCT_CATALOGUE
from app.services import product_catalogue_service as svc


class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, row_value):
        self._row_value = row_value

    def select(self, *a):
        return self

    def eq(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        if self._row_value is None:
            return _FakeResp([])
        return _FakeResp([{"value": self._row_value}])


def _patch_admin_client(monkeypatch, row_value):
    import app.services.auth_service as auth_service

    monkeypatch.setattr(
        auth_service, "admin_client",
        type("_C", (), {"table": staticmethod(lambda t: _FakeTable(row_value))})(),
        raising=False,
    )


class TestLoadProductCatalogueMerge:
    def test_no_db_row_returns_defaults(self, monkeypatch):
        _patch_admin_client(monkeypatch, None)
        cat = svc.load_product_catalogue()
        assert cat == DEFAULT_PRODUCT_CATALOGUE
        assert set(cat["coaching_programs"].keys()) == {
            "jee_main", "neet_ug", "cuet_ug", "sat", "ielts", "toefl_ibt",
        }
        assert all(v["visible"] for v in cat["coaching_programs"].values())

    def test_stale_row_with_old_exam_keys_is_healed(self, monkeypatch):
        """Reproduces the exact live row found 2026-08-26."""
        stale_row = {
            "grades": copy.deepcopy(DEFAULT_PRODUCT_CATALOGUE["grades"]),
            "coaching_programs": {
                "JEE": {"visible": False, "full_name": "JEE Mains + Advanced"},
                "NEET": {"visible": False, "full_name": "NEET UG"},
                "CUET": {"visible": False, "full_name": "CUET UG"},
            },
        }
        _patch_admin_client(monkeypatch, stale_row)
        cat = svc.load_product_catalogue()

        assert set(cat["coaching_programs"].keys()) == {
            "jee_main", "neet_ug", "cuet_ug", "sat", "ielts", "toefl_ibt",
        }
        assert "JEE" not in cat["coaching_programs"]
        assert "NEET" not in cat["coaching_programs"]
        assert "CUET" not in cat["coaching_programs"]
        assert all(v["visible"] for v in cat["coaching_programs"].values()), (
            "a canonical key absent from a stale row must default to visible, "
            "not hidden — TD-14's whole point"
        )
        assert set(svc.get_live_visible_coaching_programs()) == {
            "jee_main", "neet_ug", "cuet_ug", "sat", "ielts", "toefl_ibt",
        }

    def test_explicit_hidden_flag_on_current_key_is_honored(self, monkeypatch):
        """An admin's real choice, made through the CURRENT (post-rename)
        toggle, must still take effect — the merge only protects missing
        keys, it must never mask ones that are actually present."""
        row = {
            "grades": copy.deepcopy(DEFAULT_PRODUCT_CATALOGUE["grades"]),
            "coaching_programs": {
                "sat": {**DEFAULT_PRODUCT_CATALOGUE["coaching_programs"]["sat"], "visible": False},
            },
        }
        _patch_admin_client(monkeypatch, row)
        cat = svc.load_product_catalogue()

        assert cat["coaching_programs"]["sat"]["visible"] is False
        assert cat["coaching_programs"]["jee_main"]["visible"] is True
        visible = svc.get_live_visible_coaching_programs()
        assert "sat" not in visible
        assert "jee_main" in visible

    def test_stored_grades_section_is_ignored_entirely(self, monkeypatch):
        """
        REGRESSION: grades have no admin toggle. A stored row that still
        carries a leftover "visible: False" for Grade 11/12 (from the
        removed grade-hiding feature — this exact shape was found live and
        silently demoted Grade 12 signups to Grade 9 with no error shown to
        anyone) must have zero effect. load_product_catalogue() must always
        return the hardcoded grades defaults, regardless of what's stored.
        """
        stale_grades = copy.deepcopy(DEFAULT_PRODUCT_CATALOGUE["grades"])
        stale_grades["Grade 11"]["visible"] = False
        stale_grades["Grade 12"]["visible"] = False
        row = {"grades": stale_grades, "coaching_programs": {}}
        _patch_admin_client(monkeypatch, row)

        cat = svc.load_product_catalogue()
        assert cat["grades"] == DEFAULT_PRODUCT_CATALOGUE["grades"]
        assert "Grade 12" in cat["grades"]
        assert "visible" not in cat["grades"]["Grade 12"]
