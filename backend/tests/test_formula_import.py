"""
test_formula_import.py
Tests for POST /api/admin/formula-sheets/import

Uses FastAPI dependency_overrides to mock require_admin (the correct pattern
used throughout this codebase — see test_lesson_repair.py, test_formula_sheets.py).
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import require_admin

client = TestClient(app)

# ── Shared fixtures ───────────────────────────────────────────────────────────

MOCK_ADMIN = {"profile": {"id": "admin-uuid-1", "role": "admin", "username": "testadmin"}}

VALID_FORMULA = {
    "formula_name": "Remainder Theorem",
    "expression": "p(a) = remainder when p(x) divided by (x - a)",
    "chapter": "Polynomials",
    "difficulty": "medium",
    "explanation": "If p(x) is divided by (x - a), the remainder equals p(a).",
    "tags": ["polynomial", "remainder"],
    "active": True,
}

VALID_BODY = {
    "grade": "Grade 9",
    "subject": "Mathematics",
    "formulas": [VALID_FORMULA],
}


def _admin_override():
    return MOCK_ADMIN


def _no_admin_override():
    from fastapi import HTTPException
    raise HTTPException(status_code=403, detail="Admin only")


# ── Setup helpers ─────────────────────────────────────────────────────────────

def use_admin():
    app.dependency_overrides[require_admin] = _admin_override


def use_no_admin():
    app.dependency_overrides[require_admin] = _no_admin_override


def clear_overrides():
    app.dependency_overrides.clear()


# ── Auth tests ─────────────────────────────────────────────────────────────────

def test_import_requires_auth():
    """Without any override the real dependency runs → 401/403 from missing/invalid token."""
    clear_overrides()
    resp = client.post("/api/admin/formula-sheets/import", json=VALID_BODY)
    assert resp.status_code in (401, 403)
    clear_overrides()


def test_import_rejects_non_admin():
    """Non-admin override raises 403."""
    use_no_admin()
    resp = client.post("/api/admin/formula-sheets/import", json=VALID_BODY)
    assert resp.status_code == 403
    clear_overrides()


# ── Validation tests ───────────────────────────────────────────────────────────

def test_import_invalid_grade():
    """Grade outside 5–12 returns success=False."""
    use_admin()
    body = {**VALID_BODY, "grade": "Grade 13"}
    resp = client.post("/api/admin/formula-sheets/import", json=body)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "grade" in data.get("message", "").lower()


def test_import_empty_formulas():
    """Empty formulas list returns success=False."""
    use_admin()
    body = {**VALID_BODY, "formulas": []}
    resp = client.post("/api/admin/formula-sheets/import", json=body)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "empty" in data.get("message", "").lower()


def test_import_missing_subject():
    """Empty subject string returns success=False."""
    use_admin()
    body = {**VALID_BODY, "subject": ""}
    resp = client.post("/api/admin/formula-sheets/import", json=body)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "subject" in data.get("message", "").lower()


def test_import_missing_required_field():
    """A formula without 'expression' is rejected at Pydantic validation (422)
    or caught inside the endpoint as an error entry.
    Both behaviors are correct — expression is required."""
    bad_formula = {"formula_name": "Test Formula", "chapter": "Polynomials"}
    use_admin()
    body = {**VALID_BODY, "formulas": [bad_formula]}
    resp = client.post("/api/admin/formula-sheets/import", json=body)
    clear_overrides()
    # Pydantic validates 'expression' as required → 422 before endpoint runs
    # OR endpoint returns 200 with errors — both are valid
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        data = resp.json()
        assert data["success"] is False
        assert len(data.get("errors", [])) > 0


# ── Happy path: insert ─────────────────────────────────────────────────────────

def test_import_inserts_new_formula():
    """No existing row → INSERT → inserted=1, updated=0, errors=[]."""
    # Route chain: .select().ilike().eq(grade).eq(subject).ilike(chapter).execute()
    use_admin()
    with patch("app.routes.formula_import.admin_client") as mock_db:
        mock_select = MagicMock()
        mock_select.execute.return_value.data = []
        mock_db.table.return_value.select.return_value.ilike.return_value.eq.return_value.eq.return_value.ilike.return_value = mock_select

        mock_insert = MagicMock()
        mock_insert.execute.return_value.data = [{"id": "new-uuid"}]
        mock_db.table.return_value.insert.return_value = mock_insert

        resp = client.post("/api/admin/formula-sheets/import", json=VALID_BODY)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["inserted"] == 1
    assert data["updated"] == 0
    assert data["errors"] == []


# ── Happy path: update (upsert) ────────────────────────────────────────────────

def test_import_updates_existing_formula():
    """Existing row found → UPDATE → updated=1, inserted=0."""
    use_admin()
    with patch("app.routes.formula_import.admin_client") as mock_db:
        mock_select = MagicMock()
        mock_select.execute.return_value.data = [{"id": "existing-uuid"}]
        mock_db.table.return_value.select.return_value.ilike.return_value.eq.return_value.ilike.return_value = mock_select

        mock_update = MagicMock()
        mock_update.eq.return_value.execute.return_value.data = [{"id": "existing-uuid"}]
        mock_db.table.return_value.update.return_value = mock_update

        resp = client.post("/api/admin/formula-sheets/import", json=VALID_BODY)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["updated"] == 1
    assert data["inserted"] == 0
    assert data["errors"] == []


# ── Batch: mixed insert + update ──────────────────────────────────────────────

def test_import_batch_mixed():
    """Two formulas: one new, one existing → inserted+updated == 2."""
    formula_a = {**VALID_FORMULA, "formula_name": "New Formula A"}
    formula_b = {**VALID_FORMULA, "formula_name": "Existing Formula B"}
    use_admin()
    with patch("app.routes.formula_import.admin_client") as mock_db:
        mock_tbl = MagicMock()
        mock_tbl.select.return_value.ilike.return_value.eq.return_value.ilike.return_value.execute.side_effect = [
            MagicMock(data=[]),                        # formula_a: no existing
            MagicMock(data=[{"id": "existing-id"}]),  # formula_b: existing
        ]
        mock_tbl.insert.return_value.execute.return_value.data = [{}]
        mock_tbl.update.return_value.eq.return_value.execute.return_value.data = [{}]
        mock_db.table.return_value = mock_tbl

        body = {**VALID_BODY, "formulas": [formula_a, formula_b]}
        resp = client.post("/api/admin/formula-sheets/import", json=body)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["inserted"] + data["updated"] == 2
    assert data["errors"] == []


# ── Difficulty normalisation ───────────────────────────────────────────────────

def test_import_normalises_invalid_difficulty():
    """Unknown difficulty is normalised to 'medium' before insert."""
    # Route chain: .select().ilike().eq(grade).eq(subject).ilike(chapter).execute()
    formula = {**VALID_FORMULA, "difficulty": "impossible"}
    inserted_row = {}
    use_admin()
    with patch("app.routes.formula_import.admin_client") as mock_db:
        mock_select = MagicMock()
        mock_select.execute.return_value.data = []
        mock_db.table.return_value.select.return_value.ilike.return_value.eq.return_value.eq.return_value.ilike.return_value = mock_select

        def capture_insert(row):
            inserted_row.update(row)
            m = MagicMock()
            m.execute.return_value.data = [{}]
            return m

        mock_db.table.return_value.insert.side_effect = capture_insert

        body = {**VALID_BODY, "formulas": [formula]}
        resp = client.post("/api/admin/formula-sheets/import", json=body)
    clear_overrides()
    assert resp.status_code == 200
    assert inserted_row.get("difficulty") == "medium"


# ── Duplicate name+chapter in payload ────────────────────────────────────────

def test_import_duplicate_name_chapter_warning():
    """Two entries with the same name+chapter both process (last write wins, no hard error)."""
    dup_a = {**VALID_FORMULA, "formula_name": "Same Formula"}
    dup_b = {**VALID_FORMULA, "formula_name": "Same Formula"}
    use_admin()
    with patch("app.routes.formula_import.admin_client") as mock_db:
        mock_select = MagicMock()
        mock_select.execute.return_value.data = []
        mock_db.table.return_value.select.return_value.ilike.return_value.eq.return_value.ilike.return_value = mock_select
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [{}]

        body = {**VALID_BODY, "formulas": [dup_a, dup_b]}
        resp = client.post("/api/admin/formula-sheets/import", json=body)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] + data["updated"] == 2


# ── All optional fields accepted ─────────────────────────────────────────────

def test_import_accepts_all_optional_fields():
    """Rich formula with all optional fields should insert without error."""
    rich = {
        **VALID_FORMULA,
        "expression_latex": r"p(a) \div (x - a)",
        "topic": "Core Theorems",
        "chapter_order": 2,
        "display_order": 1,
        "explanation": "Substitute x = a to find remainder.",
        "variables": "p(x) = polynomial, a = value",
        "example": "p(x) = x^3 + 2x - 5 -> p(2) = 7",
        "solution_steps": "1. Find a\n2. Substitute\n3. Evaluate",
        "memory_tip": "Sign flips!",
        "tags": ["polynomial", "cbse-9"],
    }
    use_admin()
    with patch("app.routes.formula_import.admin_client") as mock_db:
        mock_select = MagicMock()
        mock_select.execute.return_value.data = []
        mock_db.table.return_value.select.return_value.ilike.return_value.eq.return_value.ilike.return_value = mock_select
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [{}]

        body = {**VALID_BODY, "formulas": [rich]}
        resp = client.post("/api/admin/formula-sheets/import", json=body)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["errors"] == []


# ── Response structure ────────────────────────────────────────────────────────

def test_import_response_has_required_fields():
    """Response always includes success, inserted, updated, skipped, errors, message."""
    use_admin()
    with patch("app.routes.formula_import.admin_client") as mock_db:
        mock_select = MagicMock()
        mock_select.execute.return_value.data = []
        mock_db.table.return_value.select.return_value.ilike.return_value.eq.return_value.ilike.return_value = mock_select
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [{}]
        resp = client.post("/api/admin/formula-sheets/import", json=VALID_BODY)
    clear_overrides()
    assert resp.status_code == 200
    data = resp.json()
    for field in ("success", "inserted", "updated", "skipped", "errors", "message"):
        assert field in data, f"Missing field: {field}"
