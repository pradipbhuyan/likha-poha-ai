# Likha Poha AI — Student UX Implementation Plan (Phase 7)

Classification: **P0** blocks task completion / serious confusion · **P1** high-value usability ·
**P2** consistency/discoverability · **P3** optional visual refinement.

**Scope executed this pass:** all P0 items, plus P1 items assessed as low implementation risk. See
"Implemented" column. Everything else is documented here for future approval, per the task's
instruction to implement only P0 + low-risk P1.

---

## P0

### P0-1 — Chapter completion is unreachable in the live Lessons layout

- **Problem:** `USE_REFINED_LESSON_EXPERIENCE_LAYOUT` (hard-coded `true`) hides the only UI path
  that ever called `setCompleted(true)` / saved `completed: true`. A student can never mark a
  chapter complete or see "🎉 This chapter is completed."
- **Evidence:** `frontend/src/pages/LessonsPage.jsx` — the "Mark Step Complete" button (previously
  ~line 2086) was wrapped in `{!USE_REFINED_LESSON_EXPERIENCE_LAYOUT && (...)}`; the live bottom/top
  nav bars' "Next" button was simply `disabled` on the last step with no alternative action.
  Verified via grep that `completed: true` was sent to `saveChapterProgress` from exactly one place
  in the file, and that place was unreachable.
- **Proposed solution:** Add a `finishChapter()` helper that calls the *exact same*
  `saveChapterProgress` payload the old hidden button used (`completed: true`, current step index,
  highest unlocked step, last lesson, step lessons) and `setCompleted(true)`. On the last step, both
  the top and bottom nav bars now show a "Finish Chapter" button (or a "🎉 Chapter completed" chip
  once done) instead of a permanently-disabled "Next".
- **Files changed:** `frontend/src/pages/LessonsPage.jsx`.
- **Risk:** Low — no gating, persistence, or lesson-generation logic changed; the function reuses
  the pre-existing save contract verbatim.
- **Regression concerns:** Sequential gating (`highestUnlockedStep`) and `saveChapterProgress`'s
  request shape are untouched. The hidden legacy button block (still gated behind
  `!USE_REFINED_LESSON_EXPERIENCE_LAYOUT`) was left in place, not deleted, so no dead-code removal
  risk was introduced.
- **Tests required:** No existing automated test covered chapter completion (checked
  `LessonsPage.test.jsx` — it does not assert on `completed`/`saveChapterProgress` payloads for the
  last step). Recommend a follow-up test asserting `finishChapter` fires `saveChapterProgress` with
  `completed: true` on the last step; not added in this pass to avoid growing the diff beyond the
  navigation-focused scope of this task — flagged as a **P1 test-coverage gap** below.
- **Rollback:** Revert `frontend/src/pages/LessonsPage.jsx`; the old hidden button path still exists
  untouched, so reverting fully restores prior (broken) behavior with a single file revert.
- **Implemented:** ✅ Yes.

### P0-2 — Sidebar mixes daily tools, revision tools, progress, and account/support with no structure

- **Problem:** 14-item flat list with no grouping, no `aria-current`, and a mobile drawer with no
  Escape/backdrop/scroll-lock — see `docs/student-ux-audit.md` and
  `docs/student-navigation-architecture.md` for full evidence and the options comparison.
- **Proposed solution:** Group into Home / Learn / Practise & Prepare / Revision Tools / Progress /
  Help & Account (Option B); add `aria-current="page"`, `aria-label` on the nav landmark, and
  focus-visible outlines; make the mobile drawer close on Escape, on backdrop click, and on route
  selection, and lock body scroll while open.
- **Files changed:** `frontend/src/components/Sidebar.jsx`, `frontend/src/App.css`,
  `frontend/src/App.jsx` (removed now-redundant mobile-nav effect, moved into Sidebar).
- **Risk:** Low — no `key`, `roles`, `hideForAdmin`, `gradeFilter`, or `testUsers` field was changed
  on any page config object; only a new `group` field was added and array order changed. Group
  headers render only for `user.role === "student"`, so non-student roles see the exact flat list
  they did before.
- **Regression concerns:** Route reachability for every role; grade-gating for Exam Prep/Board
  Papers/Exemplar Research; admin's `hideForAdmin` filtering. All verified unchanged — see the
  route-to-navigation mapping table in the final report.
- **Tests required:** Added — see `frontend/src/tests/Sidebar.test.jsx` (group order, item order,
  `aria-current`, non-interactive group labels, non-student roles stay flat, long-username
  rendering, logout reachability, backdrop/Escape/close-on-select/close-on-backdrop-click).
- **Rollback:** Revert the three files listed above; `Sidebar.test.jsx` additions can be reverted
  alongside with no dependency on other changes.
- **Implemented:** ✅ Yes.

---

## P1 — implemented (low risk)

| # | Problem | Files | Risk | Implemented |
|---|---|---|---|---|
| P1-1 | KaTeX rendered formulas with `output:"html"`, stripping the MathML annotation screen readers rely on | `frontend/src/pages/FormulaSheetPage.jsx` | Low | ✅ |
| P1-2 | Formula search box and both filter `<select>`s had no accessible name | `frontend/src/pages/FormulaSheetPage.jsx` | Low | ✅ |
| P1-3 | External resource links (Learn More) signalled "opens in new tab" via a visual glyph only | `frontend/src/pages/ResourcesPage.jsx`, `frontend/src/App.css` (new `.sr-only` utility) | Low | ✅ |
| P1-4 | Walkthrough language toggle used color/border only for active state | `frontend/src/pages/WalkthroughPage.jsx` | Low | ✅ |
| P1-5 | Ask Doubt used five different names for the same concept ("Ask Doubt" / "Ask AI Tutor" / "Open Mentor" / "Mentor Context" / "AI mentor") | `frontend/src/pages/DoubtPage.jsx` | Low | ✅ |
| P1-6 | Leaderboard gave no way to find "yourself," and didn't explain that test count isn't weighted into the ranking | `frontend/src/pages/LeaderboardPage.jsx`, `frontend/src/App.css` | Low | ✅ (ranking **calculation** itself untouched — ranking math change is flagged separately below for product approval) |
| P1-7 | Change Password card was 760px wide (unnecessarily wide for 3 fields) with no show/hide toggle | `frontend/src/pages/ChangePasswordPage.jsx`, `frontend/src/App.css` | Low | ✅ |
| P1-8 | Mobile hamburger/close buttons had no accessible name | `frontend/src/App.jsx`, `frontend/src/components/Sidebar.jsx` | Low | ✅ |
| P1-9 | Username in the sidebar user-card had no truncation and could overflow with a long value | `frontend/src/components/Sidebar.jsx`, `frontend/src/App.css` | Low | ✅ |
| P1-10 | Orphaned, never-imported CSS file (`components/student/StudentDashboard.css`) risked a future editor styling the wrong file | deleted | Low | ✅ |

---

## P1 — recommended, not implemented (needs more than a low-risk diff)

| # | Problem | Why it's not low-risk | Recommendation |
|---|---|---|---|
| P1-11 | Lessons/Ask Doubt Grade/Subject/Chapter `<select>`s have no accessible name, but a fully-labelled *dead* copy of the same form already exists in the DOM (`display:none`, kept only for its state variables) | Adding `aria-label` to the live select creates a duplicate accessible name (confirmed: broke `LessonsPage.test.jsx`'s `getByLabelText(/subject/i)`). Fixing it properly means removing or `aria-hidden`-ing the dead markup first — a larger diff touching more of the page than a navigation-focused pass should. | Remove the dead `lesson-control-panel`/`premium-doubt-context` markup (confirmed unreachable since `USE_TOP_BAR_LAYOUT`/`USE_REFINED_LESSON_EXPERIENCE_LAYOUT` are hard-coded `true`), *then* add `aria-label`s to the live selects. Needs its own test-verification pass. |
| P1-12 | Dashboard "Continue Learning" resume state can never appear in the API-fallback path (`progress.available` hard-coded `false`) | Touches data-fetching logic on the highest-traffic page; needs verification against the real progress API contract, which is explicitly protected ("do not change student progress calculations"). | Fetch last-lesson progress from the existing lessons/progress API in the fallback path instead of hard-coding unavailable. |
| P1-13 | Dashboard XP Points is an arbitrary client-side formula with no backend concept of XP; Achievements falls back to fake-looking zero-value rows | Needs a product decision (build real backend XP/achievements, or relabel expectations) — not a pure UI fix. | Product review needed before any code change. |
| P1-14 | Mock Test mode cards use an undefined `--surface` CSS variable, so they don't follow the dark/light theme | Touches a component with locked-state logic (paywall messaging) that should be re-verified visually in both themes before shipping. | Swap to `var(--panel)`; verify locked-state contrast in dark mode. |
| P1-15 | Mock Test's "Enable Negative Marking" checkbox doesn't disable the negative-marks selector | Needs a decision on whether the selector should also reset its value when disabled (affects what gets submitted). | Bind `disabled` to the checkbox state; confirm submit payload behavior with backend owner. |
| P1-16 | Board Papers marketing strip pushes the real paper list below the fold on mobile | Touches page layout order on a content-heavy page; needs a mobile screenshot pass to confirm the promo strip's new position doesn't look broken. | Move promo strip below the timeline, or collapse to a single dismissible banner. |
| P1-17 | Analytics "AI Insight" is 3 hard-coded strings keyed only on average score | Explicitly out of scope: "Do not alter analytics formulas without tests and documented approval." | Product decision: either honestly relabel (e.g. "Score Summary") or invest in a real per-subject insight computation. |
| P1-18 | Analytics has no link from a weak subject to Lessons/Practice | Requires picking a target chapter/subject mapping and confirming it doesn't imply incorrect subject-to-chapter assumptions. | Add "Practice this subject →" per subject card, pointed at Mock Test or Lessons filtered to that subject. |
| P1-19 | Leaderboard ranks by raw average score with no minimum-attempts floor (1 lucky test can outrank 50 consistent tests) | **Explicitly out of scope** — "Do not change ranking calculations as part of this UX task." | Recommend a minimum-attempts threshold or a confidence-weighted score, for separate product approval. A one-line disclaimer was added this pass as a transparency mitigation without touching the math. |
| P1-20 | No automated test covers the new Lessons "Finish Chapter" action (P0-1) | Adding it responsibly means also stubbing `saveChapterProgress`/`getChapterProgress` realistically, which is more surface area than a quick add. | Add a targeted test asserting `saveChapterProgress` receives `completed: true` when "Finish Chapter" is clicked on the last step. |

---

## P2 — consistency / discoverability (documented only)

- Header eyebrow "Your Personal Tutor – AI Powered" repeats unconditionally across all pages and
  roles, including admin/teacher/sales where it's irrelevant. (`frontend/src/App.jsx`)
- `profile-pill` in the header is a static div, not an account-menu button — no way to reach Logout
  from the header (only from the sidebar footer). Turning it into a real menu needs to reuse
  existing account routes/actions only, per the task's explicit constraint.
- Two overlapping `@media (max-width: 900px)` blocks both restyle `.topbar`/`.mobile-menu-btn` with
  `!important`-heavy rules — a maintenance smell, not a user-visible bug.
- Exam Prep Center's 5-phase study plan has no current/completed/future visual state.
- Formulas & Concepts chapter list is not sticky; scrolls away on long chapters.
- Exemplar Research's difficulty filter is skewed (~61% "Hard"), reducing its usefulness.

## P3 — optional visual refinement (documented only)

- Analytics x-axis uses "Test 1, Test 2…" instead of real submission dates.
- Board Papers loading state is bare unstyled text rather than a skeleton.
- Learn More doesn't surface video duration before playback (may be a data-availability gap).
- Change Password has no live password-strength indicator (only a static hint + post-submit error).

---

## Explicit non-changes (confirmed, not touched)

Backend APIs and contracts, authentication logic, role-based access, subscription entitlement
logic, paid/free plan rules, route URLs, database schema, student progress calculations,
lesson-generation logic, mock-test generation logic, exam-prep calculations, analytics formulas,
leaderboard ranking math, and existing persisted user data. No existing feature was removed. No
working component was replaced for stylistic preference alone.
