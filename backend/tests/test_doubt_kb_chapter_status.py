"""
get_dkb_chapter_status() regression tests.

This function had two real bugs, both confirmed against production data:
1. Exact chapter-string matching missed multi-book subjects, where the
   student-facing dropdown sends a display-prefixed chapter name (e.g.
   "Text Book - Part 1 - 1. Locating Places on the Earth") that differs
   from the bare syllabus chapter name -- fixed via normalize_chapter_core.
2. A plain .execute() with no .range() silently caps at 1000 rows
   (PostgREST default page size) -- every grade already has 1,500-3,900+
   active doubt_kb rows, so this was aggregating off a truncated sample.
   Fixed via explicit .range() pagination.

These tests use a minimal fake Supabase query-builder double so the
pagination and normalization logic can be verified without a live DB.
"""

import app.services.doubt_kb_service as doubt_kb_service


class _FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Chainable stand-in for supabase-py's table().select().eq()...execute()."""

    def __init__(self, all_rows):
        self._all_rows = all_rows
        self._range = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        if self._range is None:
            page = self._all_rows[:1000]  # mimic PostgREST's default cap
        else:
            start, end = self._range
            page = self._all_rows[start:end + 1]
        return _FakeExecuteResult(page)


class _FakeSupabase:
    def __init__(self, all_rows):
        self._all_rows = all_rows

    def table(self, _name):
        return _FakeQuery(self._all_rows)


def _syllabus_with_one_chapter():
    return {"CBSE": {"Social Science": ["1. Locating Places on the Earth"]}}


def test_paginates_past_the_1000_row_default_cap(monkeypatch):
    """A grade with >1000 active doubt_kb rows must not be silently truncated."""
    # 1200 rows, all for the one syllabus chapter under its exact bare name —
    # a naive single .execute() would only see the first 1000.
    rows = [{"subject": "Social Science", "chapter": "1. Locating Places on the Earth", "source": "prewarmed"}
             for _ in range(1200)]

    monkeypatch.setattr(doubt_kb_service, "get_content_db", lambda grade: _FakeSupabase(rows))
    monkeypatch.setattr(
        "app.services.prewarm_service.get_syllabus_for_grade",
        lambda grade: _syllabus_with_one_chapter(),
    )

    result = doubt_kb_service.get_dkb_chapter_status("Grade 6")

    assert len(result) == 1
    assert result[0]["entries"] == 1200


def test_aggregates_display_prefixed_chapter_variants(monkeypatch):
    """Rows stored under a display-prefixed chapter name (multi-book subjects)
    must count toward the same syllabus chapter as the bare-name rows."""
    rows = (
        [{"subject": "Social Science", "chapter": "1. Locating Places on the Earth", "source": "prewarmed"}
         for _ in range(24)]
        + [{"subject": "Social Science", "chapter": "Text Book - Part 1 - 1. Locating Places on the Earth", "source": "gpt55"}
           for _ in range(36)]
    )

    monkeypatch.setattr(doubt_kb_service, "get_content_db", lambda grade: _FakeSupabase(rows))
    monkeypatch.setattr(
        "app.services.prewarm_service.get_syllabus_for_grade",
        lambda grade: _syllabus_with_one_chapter(),
    )

    result = doubt_kb_service.get_dkb_chapter_status("Grade 6")

    assert len(result) == 1
    assert result[0]["entries"] == 60
    assert result[0]["prewarmed"] == 24
    assert result[0]["gpt55"] == 36


def test_reports_zero_when_truly_no_rows_match_any_variant(monkeypatch):
    monkeypatch.setattr(doubt_kb_service, "get_content_db", lambda grade: _FakeSupabase([]))
    monkeypatch.setattr(
        "app.services.prewarm_service.get_syllabus_for_grade",
        lambda grade: _syllabus_with_one_chapter(),
    )

    result = doubt_kb_service.get_dkb_chapter_status("Grade 6")

    assert result == [{
        "subject": "Social Science",
        "chapter": "1. Locating Places on the Earth",
        "entries": 0, "prewarmed": 0, "llm": 0, "gpt55": 0, "admin_approved": 0,
    }]
