# Student Platform

_Last updated: 2026-07-07_

## Vision

The Student Dashboard motivates learning and makes the next best action immediately obvious — students should know what to do in under 5 seconds.

## Implemented Features

### Student Dashboard Redesign (Option 1 — Card-Based Layout)

**Backend:** `GET /api/student/dashboard/summary`
- Profile (safe fields: username, grade, streak, lessons_completed)
- Subscription + feature access (canonical resolver — never from raw `access_cbse`)
- Mock tests: total, avg, best, subject averages, recent, score trend
  - All scores via `_normalize_score_pct()` — never >100%
- Progress from `student_progress` table (last chapter for Continue Learning)
- Weak topics from `weak_area_alerts`
- Activity from `ai_usage_logs` (90d window)
- Rule-based achievements: streak, lessons, first test, high score
- Rule-based recommendations: inactive/practice/mock/upgrade
- Today's plan: 4 prioritized tasks
- Safety: student ownership enforced, no teacher/admin data exposed

**Frontend layout:**
1. **Hero** — "Good morning, Name!" + Day Streak card + Overall Progress card
2. **Quick Stats Row** — Today's Goal · Lessons Left · Next Exam · XP Points
3. **Main Row (3 cols)** — Continue Learning / Today's Plan / AI Learning Coach
4. **Middle Row (4 cols)** — Subject Progress / Recent Mock Tests / Weak Topics / Achievements
5. **Utility Row (4 cols)** — Revision Center / AI Doubt Solver / Upcoming Exams / Quick Actions
6. **Motivation Card** — rotating motivational quote

**CSS** — Responsive: 4-col → 2-col (tablet) → 1-col (mobile), CSS variables for light/dark mode.

**Fallback:** Every card handles missing data gracefully — no blank panels.

### Student Signup
- Single-step card-based signup (SignupPage.jsx)
- Parent + Student roles only (Teacher not in public signup)
- Student signup includes Grade selector (**Grade 5–12** — updated 2026-08; Grade 11/12 requires a mandatory stream selection: PCM / PCB / PCMB / Commerce / Humanities, enforced at 5 call sites in `backend/app/routes/auth.py`)
- Grade saved to profile and used to show relevant lessons on dashboard
- Google Sign In supported
- All new accounts start on Free Tier

## Access Rules

Student features must follow the canonical feature authorization matrix:

| Feature | Free Tier | Paid |
|---|---|---|
| AI Lessons | Limited | Full |
| Mock Tests | 5/day | Unlimited |
| Ask Doubts | Limited | Full |
| Exemplar | Locked | Full |
| Exemplar Research | Locked | Full |

- `parentId` alone never implies paid access.
- Feature access comes from `get_feature_summary(user_id)` — never from raw `subscription_plan`.

## Data Sources

| Data | Table | Key Column |
|---|---|---|
| Mock test history | `test_history` | `percentage` (0-100), `raw_score`, `max_score` |
| Lesson progress | `student_progress` | `completed`, `current_step_index` |
| Weak areas | `weak_area_alerts` | `best_score`, `subject`, `chapter` |
| AI activity | `ai_usage_logs` | `feature`, `created_at` |

**Important:** `chapter_progress` table does NOT exist. Use `student_progress`.
**Important:** `test_history.score` and `test_history.total_questions` columns do NOT exist. Use `percentage`.

## Score Normalization

All score display must use `_normalize_score_pct(percentage, raw_score, max_score)`:
- `percentage` in [0,100] → use directly
- `percentage` > 100 → invalid, fallback to `raw_score / max_score * 100`
- No valid data → return `None` → show "Score not available"
- Never multiply an already-percent value by 100
- Never divide by zero

## Auth / Session

- Session recovery on app boot: verifies Supabase session, refreshes token, fetches fresh profile
- Google OAuth hang fix: full OAuth processing only runs on actual OAuth redirect URLs (`#access_token=` or `?code=`), not on normal page reload with existing session
- `handleLogin` fetches fresh `/api/auth/profile` for ALL roles (not just students)
- `handleRefreshUser()` available to refresh after data mutations

## Exam Schedule
- Student can add exam dates via "Upcoming Exams" card in dashboard
- Parent can also add for linked child
- No static/placeholder dates — all real data
- API: `/api/student/exams` and `/api/parent/children/{id}/exams`

## Student Profile Fields

| Field | Description |
|---|---|
| `study_streak_days` | Current learning streak |
| `lessons_completed` | Total lessons generated |
| `grade` | Grade 5–12 (set at signup; 11/12 also carries a `stream`) |
| `board` | CBSE (default) |
| `access_cbse` | Canonical paid access flag |
| `subscription_expires_at` | Expiry date if applicable |

## Exam Prep Center — Grade 11/12

### Access Rules
- **Grade 11/12 students**: content access gated by the `subscription_plan_settings.access_exam_prep` flag on their current plan — satisfied by the standalone **Exam Prep Center** plan (₹1,999/year) or any other plan an admin has flagged with `access_exam_prep=true`. **2026-08-26: the old per-exam pack purchase system (`exam_prep_packs`) was removed** — see `03_SUBSCRIPTIONS.md` and `FEATURE_MATRIX.md` for the current model. Without the flag: `preview_only: true`.
- **`akshita.teststudent`**: always gets full access (`reason: "test_user"`, `ADMIN_GRANT` plan)
- **admin role**: always gets full access
- **Grade 5–10 students**: see a grade-ineligible lock screen (Exam Prep Center remains Grade 11/12-only regardless of the broader Grade 5–12 signup/add-child range above)

### Stream-based Exam Eligibility
| Stream | JEE Main | NEET UG | CUET UG |
|---|---|---|---|
| PCM | ✅ Eligible | ❌ | ⏳ Coming Soon |
| PCB | ❌ | ✅ Eligible | ⏳ Coming Soon |
| PCMB | ✅ Eligible | ✅ Eligible | ⏳ Coming Soon |
| No stream | ❌ (unless test user) | ❌ (unless test user) | ⏳ Coming Soon |

Test users (`akshita.teststudent`) override stream eligibility — all exams show as eligible.

### Backend Endpoint
`GET /api/exam-prep/access-check` — returns canonical access state. Frontend must call this, never infer from plan string.

Response fields:
- `grade_eligible`: bool
- `has_access`: bool
- `preview_only`: bool
- `reason`: "full_access" | "free" | "nano" | "admin" | "test_user" | "grade_ineligible"
- `stream_missing`: bool
- `exam_eligibility`: `{jee_main, neet_ug, cuet_ug}` per-stream flags
- `canonical_plan_key`: string

### Exam Prep Question Bank
- Questions stored in `exam_prep_questions` table (Supabase 2 / grade_1112_client)
- States: `draft` → `published` → `archived`
- Admin can generate via AI prewarm or paste-import from ChatGPT/Custom GPT
- Students see only `published` questions

### Explanation Rendering
- `detailed_explanation` text is split on `Step N:`, `Option X:`, and `Therefore` patterns
- Each step renders as a separate `<div>` with margin (not one continuous block)

---

## Lesson Page Updates — July 2026

### LKB Chips (Quick Doubt Suggestions)
- Chips now appear **immediately** after lesson generation (not just on re-navigation)
- Fix: `ensureLessonKbChips()` called explicitly inside `handleGenerateLesson()` after `setLesson()`
- LKB chips take priority over DKB chips; graceful fallback if LKB unavailable

### Listen to Lesson (TTS)
- **Fast path added:** Button first checks `GET /api/tts/cached-url` — if pre-warmed audio exists, plays instantly from CDN (no generation delay)
- **Hindi support:** Hindi lessons use `hi-IN-SwaraNeural` (proper Devanagari narration)
- **Pause structure:** Narrator pauses between headings, paragraphs, and list items
- **Abbreviation expansion:** Narrator says "for example" for "e.g.", "C B S E" for "CBSE", etc.

### Maths Lessons — LaTeX Quality
- LLM prompt strengthened: all math expressions must be in `$...$`
- Broken lessons (with rendering issues) are detected, archived, and regenerated
- Students should see clean rendered math; report via "Report Issue" if still broken

---

## Lesson Page — July 2026 Redesign

### Layout Architecture
The Lessons page uses a **compact horizontal top bar** replacing the old left sidebar.

**Top bar** contains (left to right): 📚 Grade selector · Subject selector · Chapter selector · Step N/N pill · ✨ Generate / 🔄 Refresh

**Lesson content** takes the full width of the page.

**Feature flags** in `LessonsPage.jsx`:
```js
const USE_TOP_BAR_LAYOUT = true;   // compact top bar; set false to roll back to sidebar
```

### Workbook Layout (Option B — Active)
`LessonSections.jsx` renders all sections **expanded inline** with a colour-coded left border.

**Feature flags:**
```js
const USE_WORKBOOK_LAYOUT = true;   // Option B (active)
const USE_CARD_FEED_LAYOUT = false; // Option A (colour cards)
// both false = legacy accordion
```

**Floating TOC button:** `≡` button fixed to right side of screen (`position:fixed; right:16px`). Opens a dark-background panel listing all section headings. Clicking a heading scrolls to that section and closes the panel.

**Section type → colour coding:**
| Type | Border colour | Icon |
|---|---|---|
| Introduction/Overview | Blue | 🎯 |
| Concept/Explanation | Amber | 📘 |
| Example/Worked | Green | 🧪 |
| Warning/Mistake | Orange | ⚠️ |
| Quick Check/Question | Red | ✅ |
| Summary/Recap | Purple | 📌 |

### parseSections() — 5 Heading Patterns
`LessonSections.jsx` supports 5 patterns for splitting lesson markdown into sections:
1. `## 1. Title` or `**1. Title**` — numbered with hash/bold wrapper
2. `## Title` — markdown H2/H3 without number
3. `**Title**` or `**Title:**` — standalone bold line
4. `Step N: Title` — plain text (no terminal `.`)

Numbered list items (e.g. `1. Read the sentence carefully.`) end with `.` and are correctly **not** treated as section headings.

### getRenderableContent() — Worked Example Protection
If a section contains `Question:` followed by `Step N:` or `Answer:` (i.e. a worked example with solution), the **full body is rendered** including question + solution. Previously, everything after `Question:` was stripped (272 words lost in a real lesson).

### Inline Math Fix
`fixInlineDisplayMath()` runs directly on `renderableContent` before ReactMarkdown renders. Converts `$$expr$$` or unclosed `$$expr` inline to `$expr$`. Does not touch proper standalone display math blocks.

### Ask Doubt Page — Full Width
`DoubtPage.jsx` uses the same compact top bar pattern. Mentor Context sidebar is hidden. Doubt textbox takes full width.

**Feature flag:** Currently inline styles applied directly — no flag needed. To revert, restore the `<aside>` display and `<section>` grid styles.

### Practice Questions — Stricter Scoring
| Metric | Old value | New value |
|---|---|---|
| Keyword score floor | `max(1,...)` | `max(0,...)` |
| Pass threshold | `score >= 6` | `score >= 7` |
| Evaluator mode | Warm/encouraging | Strict/textbook-grounded |

### Prewarm Question Generation — RAG Scaling
The `/api/lesson/prewarm/generate-questions` endpoint scales question count by available RAG content:
- ≤ 2 RAG chunks: 1 question (tiny chapter)
- 3–5 RAG chunks: 2 questions
- 6+ RAG chunks: 3 questions

Existing textbook exercise questions in the RAG chunks are used **directly** before generating new ones.
