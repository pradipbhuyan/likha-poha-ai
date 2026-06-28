# Content Management

_Last updated: 2026-06-28_

This document describes how academic reference content (Formula Sheets, Study Materials) is structured, stored, loaded, and expanded on the Likhapoha AI platform.

---

## Formula Sheets

### Where Content Lives

Formula sheet content is stored in the **`formula_sheets`** table in the main Supabase database.

| Column | Type | Required | Description |
|---|---|---|---|
| `id` | UUID | auto | Primary key |
| `grade` | TEXT | ✅ | e.g. `"Grade 9"` — must match profile grades |
| `subject` | TEXT | ✅ | e.g. `"Mathematics"`, `"Science"`, `"Physics"`, `"Chemistry"` |
| `chapter` | TEXT | — | e.g. `"Triangles"` — nullable (applies to whole subject if null) |
| `section_title` | TEXT | ✅ | Groups formulas visually, e.g. `"Area Formulas"` |
| `formula_name` | TEXT | ✅ | Short title, e.g. `"Heron's Formula"` |
| `expression` | TEXT | ✅ | The formula itself, e.g. `"A = sqrt[s(s-a)(s-b)(s-c)]"` — plain text, no LaTeX required |
| `explanation` | TEXT | — | Plain-English meaning, e.g. `"s = (a+b+c)/2 is the semi-perimeter"` |
| `example` | TEXT | — | Worked example, e.g. `"a=3, b=4, c=5 → A=6"` |
| `display_order` | INT | ✅ | Sort order within a section (default 0) |
| `active` | BOOLEAN | ✅ | Set `false` to hide without deleting (default `true`) |
| `created_at` | TIMESTAMPTZ | auto | Timestamp |

### Migration

Run once per database:
```sql
-- File: backend/migrations/20260628_formula_sheets.sql
CREATE TABLE IF NOT EXISTS formula_sheets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grade           TEXT NOT NULL,
    subject         TEXT NOT NULL,
    chapter         TEXT,
    section_title   TEXT NOT NULL,
    formula_name    TEXT NOT NULL,
    expression      TEXT NOT NULL,
    explanation     TEXT,
    example         TEXT,
    display_order   INT  NOT NULL DEFAULT 0,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_formula_grade_subject ON formula_sheets (grade, subject);
CREATE INDEX IF NOT EXISTS idx_formula_active        ON formula_sheets (active);
```

### How Content Is Loaded

#### Option 1 — Seed Script (current)
```bash
cd backend
.venv/bin/python scripts/seed_formula_sheets.py
```
The seed script is **idempotent** — it checks `count(*)` and skips if rows already exist.
To re-seed: `DELETE FROM formula_sheets;` then re-run.

#### Option 2 — Supabase Studio (manual)
1. Open Supabase dashboard → Table Editor → `formula_sheets`
2. Insert rows directly via the UI

#### Option 3 — Admin API (planned)
Future: `POST /api/admin/content/formula-sheets` for bulk import via JSON/CSV.

### API Endpoint

```
GET /api/student/formula-sheets?grade=Grade+9&subject=Mathematics
```

Response:
```json
{
  "success": true,
  "available": true,
  "grade": "Grade 9",
  "subject": "Mathematics",
  "subjects": ["Mathematics", "Science"],
  "chapters": ["Triangles", "Circles", "Statistics"],
  "sections": [
    {
      "title": "Area Formulas",
      "formulas": [
        {
          "name": "Heron's Formula",
          "expression": "A = sqrt[s(s-a)(s-b)(s-c)]",
          "explanation": "s = (a+b+c)/2 is the semi-perimeter",
          "example": "a=3, b=4, c=5 → A=6",
          "chapter": "Triangles"
        }
      ]
    }
  ],
  "total": 7
}
```

If no content exists for a grade:
```json
{
  "success": true,
  "available": false,
  "message": "Formula sheet is not available for Grade 5 yet.",
  "sections": []
}
```

### Current Content Coverage

| Grade | Subjects | Formulas |
|---|---|---|
| Grade 5 | Mathematics | 4 |
| Grade 6 | Mathematics | 3 |
| Grade 7 | Mathematics | 4 |
| Grade 8 | Mathematics | 6 |
| Grade 9 | Mathematics, Science | 17 |
| Grade 10 | Mathematics, Science | 20 |
| Grade 11 | Mathematics, Physics, Chemistry | 23 |
| Grade 12 | Mathematics, Physics, Chemistry | 19 |

### Adding New Content

To add formulas for a new grade or subject:

1. Create a new seed script or append to `scripts/seed_formula_sheets.py`
2. Follow the schema table above
3. Use plain text for expressions (ASCII-safe: `sqrt`, `^`, `x`, `pi`)
4. Run script or insert via Supabase Studio
5. Verify via: `GET /api/student/formula-sheets?grade=Grade+X&subject=Mathematics`

**Content guidelines:**
- Use your own wording — do not copy verbatim from textbooks
- Formulas themselves are mathematical facts, not copyrightable
- Explanations and examples should be original
- Keep `expression` ASCII-friendly (no Unicode math symbols required, but allowed)

### Sample: Adding Grade 5 Science

```python
# In scripts/seed_formula_sheets.py or a new file
new_rows = [
    {
        "grade": "Grade 5",
        "subject": "Science",
        "chapter": "Food and Nutrition",
        "section_title": "Nutrition",
        "formula_name": "Food Energy",
        "expression": "Energy (kcal) = Carbohydrates + Proteins + Fats",
        "explanation": "Total energy from macronutrients in food",
        "example": "100g rice: ~130 kcal from carbs",
        "display_order": 1,
    }
]
admin_client.table("formula_sheets").insert(new_rows).execute()
```

---

## Study Materials

### Where Content Lives

Study materials (videos, PDFs, external resources) are currently served via the **Learn More** page (`resources` page key, `/api/resources` endpoint in `backend/app/routes/resources.py`).

The endpoint calls `get_learning_resources(subject, chapter, grade)` which returns curated links.

### Expanding Study Materials

1. Update `get_learning_resources()` in `backend/app/services/resources_service.py` (or equivalent)
2. Add links per grade/subject/chapter
3. Mark external resources as `type: "video"` or `type: "article"` for future filtering

### Planned: Admin Content Editor (not yet implemented)

A future admin interface will allow:
- Adding formula sheets via UI
- Adding/editing study material links
- Uploading reference PDFs
- Managing content by grade, subject, chapter

Until then: use seed scripts and Supabase Studio.

---

## Content Safety Rules

1. **No verbatim textbook content** — all explanations and examples must be original
2. **Formulas are mathematical facts** — expressions like `F = ma` are safe
3. **Diagrams** — not yet supported in formula sheets (text only)
4. **No external image dependencies** — keep content self-contained

---

## File Locations

| File | Purpose |
|---|---|
| `backend/migrations/20260628_formula_sheets.sql` | Table schema (idempotent) |
| `backend/scripts/seed_formula_sheets.py` | Seed data — Grade 5-12 |
| `backend/app/routes/formula_sheets.py` | API endpoint |
| `frontend/src/pages/FormulaSheetPage.jsx` | Formula sheet UI |
| `frontend/src/tests/FormulaSheetPage.test.jsx` | Frontend tests |
| `backend/tests/test_formula_sheets.py` | Backend tests (if added) |
