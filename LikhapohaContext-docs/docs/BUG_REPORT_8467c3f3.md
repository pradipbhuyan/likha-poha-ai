# Bug Report — Likha Poha AI
# Defect 8467c3f3-1bb6-4d31-9ef2-67d0a7d305d1

---

## SECTION 1 — Defect Identity

| Field | Value |
|---|---|
| **Defect ID** | `8467c3f3-1bb6-4d31-9ef2-67d0a7d305d1` |
| **Type** | `content issue` — math rendering |
| **Severity** | `medium` |
| **Status** | `open` |
| **Reported** | `13/07/2026, 08:33:17` |

---

## SECTION 2 — What the User Sees (Exact Description)

**Verbatim copied text from the browser (kinematic equations section):**

```
v = v0 + at x = x0 + v0t + 
1
/
2
1/2at^2$$ 
v
2
v 
2
  = 
v
0
2
v0 
2
  + 2ax
```

**Screenshot shows:**
```
v = v0 + at x = x0 + v0t + 1/2at^2$$ v² = v0² + 2ax
```

The `$$` delimiter is displayed as literal text. The equations `v = v0 + at` and `x = x0 + v0t` are plain text instead of formatted math. Only the last equation's exponents (`v²`, `v0²`) are rendered by KaTeX.

### Context

| Field | Value |
|---|---|
| **Route** | `lessons` |
| **Grade** | `Grade 11` |
| **Subject** | `Physics` |
| **Chapter** | `Units and Measurements` |
| **Step / Section** | `Core explanation` (also visible in `Step-by-step breakdown`) |
| **User role** | `student` |
| **Platform** | `MacIntel` |
| **Viewport** | `1374 × 645` |

---

## SECTION 3 — Root Cause (Diagnosed)

The bug is entirely in the client-side markdown normalization pipeline:
**`frontend/src/utils/markdownCleanup.js` → `normalizeTutorMarkdown()`**

Five cascading defects were found and fixed:

| # | Function | Bug | Fix commit |
|---|---|---|---|
| 1 | `normalizeInlineDisplayMath` Step 3 | Regex `\S` matched leading `$` of `$$eq$$` lines, stripping closing `$$` | `33c7475` |
| 2 | `normalizeInlineDisplayMath` pre-step | JS replacement string `"$$\n$$"` → `"$\n$"` (JS `$$` escape) | `33c7475` |
| 3 | `normalizeInlineDisplayMath` compact | Line-wrapped `$$eq+\ncont$$` had closing `$$` stripped by Step 3 | `44e95e3` |
| 4 | `normalizePlainExponents` | `1/2at^2` → `2at^2` converted to `$2at^2$`, creating adjacent `$$` junction | `abdc6a8` |
| 5 | `normalizePlainExponents` | Same bug via LaTeX `}` boundary: `\frac{1}{2}at^2` | `c2363c8` |

**Important architecture note:**
`normalizeTutorMarkdown()` is a **client-side render-time function**. The Supabase `lesson_cache` table stores raw LLM output untouched. The corruption was never stored — it was a rendering-only defect. No database migration needed.

---

## SECTION 4 — Definition of Done

- [x] All equation format variants produce clean output (no visible `$$`)
- [x] Regression tests added: `frontend/src/tests/markdownCleanup.test.js` (11/11 pass)
- [x] No existing tests broken
- [x] `cd frontend && npx vitest run` — 11/11 pass
- [x] `cd frontend && npx eslint src/ --max-warnings 50` — 0 errors, 50 warnings (within limit)
- [x] Backend not touched — no pytest run needed
- [ ] **Pending:** Click `🔄 Refresh lesson` on the affected lesson to regenerate from LLM (the existing cached raw content is in a plain-text format with no proper `$$` delimiters; the normalization fixes handle it but regeneration gives fully formatted output)

---

## SECTION 5 — How to Verify the Fix

1. Open `http://localhost:5174/` (dev) or the deployed URL
2. Navigate to: **Lessons → Grade 11 → Physics → Units and Measurements → Core explanation**
3. The kinematic equations should display without any visible `$$` characters
4. If `$$` still shows → click `🔄 Refresh lesson` to regenerate from LLM

---

---
---

# CODEX SESSION BOOTSTRAP — Auto-Context

> Read these before touching any code. All paths relative to repo root:
> `/Users/a0247716/Pradips_Project/cbse-tutor-platform/`

## Mandatory Pre-Task Reading

1. `LikhapohaContext-docs/docs/CODEX_BOOTSTRAP.md`
2. `LikhapohaContext-docs/docs/CODEX_CONTEXT.md` (as of 2026-08-26 this is the only copy — the old second root-level copy is now a redirect stub)
3. `LikhapohaContext-docs/docs/09_AI_PLATFORM.md` ← **required for this bug (lessons + LLM)**
4. `LikhapohaContext-docs/docs/02_ARCHITECTURE.md`

---

## Files Directly Relevant to This Bug

| File | Relevance |
|---|---|
| `frontend/src/utils/markdownCleanup.js` | **Primary fix location** — `normalizeTutorMarkdown()` pipeline |
| `frontend/src/tests/markdownCleanup.test.js` | Regression tests added here |
| `frontend/src/components/LessonSections.jsx` | Calls `normalizeTutorMarkdown(lesson)` then `fixInlineDisplayMath()` |
| `frontend/src/pages/LessonsPage.jsx` | Route that triggers lesson generation |
| `backend/app/services/tutor_service.py` | LLM prompt + cache-first lesson generation |
| `backend/app/services/lesson_cache_service.py` | Supabase `lesson_cache` table access |

---

## Lesson Rendering Rules (Never Violate)

- `normalizeTutorMarkdown()` **runs client-side at render time** on raw cached content — never server-side
- `parseSections()` handles 5 heading patterns — never reduce
- `getRenderableContent()`: if section has `Question:` + `Step N:`, it is a worked example — **never strip the solution**
- Inline `$$expr$$` → use `fixInlineDisplayMath()` before ReactMarkdown (also runs in `WorkbookSection` and `CardFeedSection`)
- The Supabase cache stores **raw LLM output** — regenerate with `force_refresh=True` to get fresh content

---

## Test Counts (Do Not Regress)

| Suite | Count |
|---|---|
| Backend (pytest) | 535+ |
| Frontend (vitest, 46 files) | 578 (was 576 before this fix — 2 regression tests added) |

**Mandatory pre-push:**
```bash
cd frontend && npx vitest run && npx eslint src/ --max-warnings 50
```

---

## Key Hard Rules Relevant to This Bug

- `normalizeTutorMarkdown()` is **never called server-side** — it is a frontend render-time function
- `$$expr$$` inline without `fixInlineDisplayMath()` → breaks KaTeX rendering
- **Never** add a server-side normalization step that writes modified content back to `lesson_cache` — the cache must store raw LLM output so `force_refresh` produces a clean regeneration
- The `🔄 Refresh lesson` button calls `force_refresh=True` on the backend → bypasses cache → regenerates from LLM → stores raw new content → client normalizes at render time

---

## Anti-Patterns Specific to This Area

| Anti-Pattern | Reason |
|---|---|
| Running `normalizeTutorMarkdown()` on the backend | Client-only; server has no KaTeX context |
| Writing normalized content back to `lesson_cache` | Prevents clean regeneration; raw output must be preserved |
| Calling `fixInlineDisplayMath()` on already-normalized text | Double-processing causes regex mismatch |
| Testing `normalizeTutorMarkdown()` only with `$$\n...\n$$` blocks | Must also test `$$eq$$` single-line and same-line variants |
