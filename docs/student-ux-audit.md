# Likha Poha AI — Student UX Audit (Phase 1)

**Scope:** Every student-facing screen reachable from the sidebar: Dashboard, Lessons, Ask Doubt,
Mock Test, Formulas & Concepts, Exemplar Research, Learn More, Exam Prep Center, Board Papers,
Analytics, Leaderboard, Platform Walkthrough, Subscription, Change Password, plus the shared
header/sidebar shell.

**Method:** Direct code inspection of `frontend/src/pages/*.jsx`, `frontend/src/components/Sidebar.jsx`,
`frontend/src/App.jsx`, and associated CSS/tests. No production data was inspected; "hard-coded" /
"real data" calls are based on what the component actually computes vs. falls back to.

**Architectural fact that shapes several findings below:** the authenticated app does **not** use
URL-based routing. Page switching is driven by an `activePage` string held in React state
(`App.jsx`), persisted to `localStorage` on change, and the browser URL never changes for any
in-app page. Practical effect: there is no bookmarkable/deep-linkable URL per feature, and browser
back/forward does not step between app pages. This is a pre-existing, intentional architecture
(not something introduced by this audit) and is called out once here rather than repeated per row.
Changing it is out of scope (see Implementation Plan, "Recommended, not implemented").

## Legend

- **Severity:** Critical (blocks the student's task or is actively misleading) · High (real friction
  or a11y gap) · Medium (noticeable but has a workaround) · Low (polish)
- **Should implement now:** reflects the *scope of this pass* (P0 + low-risk P1 only). "No" does not
  mean "never" — see `docs/student-ux-implementation-plan.md` for the P1–P3 backlog.

## Audit table

| Screen | Primary student goal | Strengths | Usability problems | Severity | Recommended change | Impl. risk | Implement now? |
|---|---|---|---|---|---|---|---|
| **Global Sidebar** | Get anywhere in ≤2 clicks, always know where I am | Single shared component for all roles; role/grade/plan filtering already centralized | Flat 14-item list mixing daily tools, revision tools, progress, and account/support with no grouping; no `aria-current`; mobile drawer had no Escape-to-close, no scroll lock, no backdrop | High | Group into Home / Learn / Practise & Prepare / Revision Tools / Progress / Help & Account; add `aria-current`, focus-visible outline, Escape + backdrop + scroll-lock | Low | **Yes — done** |
| **Global Header (topbar)** | Consistent orientation on every page | One shared `<header className="topbar">` (not duplicated per page); `PAGE_META` drives title/subtitle consistently | Hamburger button (`☰`) had no accessible name; "Your Personal Tutor – AI Powered" eyebrow repeats verbatim on every page including non-student roles; `profile-pill` is a static div, not an account menu | Medium–High | Add `aria-label` to hamburger (done); eyebrow de-noising and account-menu are larger, cross-role changes — documented, not implemented this pass | Low (label) / Medium (eyebrow, menu) | Partial — aria-label **done**; eyebrow/account-menu **not implemented** |
| **Lessons — chapter completion** | Finish a chapter and see it marked done | Sticky top+bottom Prev/Next bar keeps navigation reachable; auto-loads generated steps | In the live layout, the only code path that ever set `completed:true` was behind a permanently-disabled feature flag — a student could **never** reach chapter completion or the "🎉 completed" message | **Critical** | Add a "Finish Chapter" action on the last step, reusing the existing `saveChapterProgress` call (no gating/logic change) | Low | **Yes — done** |
| **Lessons — step state** | Know which steps are locked/done/available | — | No per-step lock/complete iconography in the live layout, only a single aggregate "% complete" chip | High | Add a compact per-step progress rail | Low–Medium | No (documented) |
| **Lessons — selectors** | Pick Grade/Subject/Chapter quickly | Compact single-row bar | The visible Grade/Subject/Chapter `<select>`s have no accessible name; a correctly labelled version exists but is dead (`display:none`) | High | Add `aria-label`s — **attempted, but reverted**: the dead hidden `<label>` markup with the same text already exists in the DOM, so adding a label to the live select created a duplicate accessible name (confirmed by `LessonsPage.test.jsx` failing on `getByLabelText(/subject/i)` matching two elements) | Low label / Medium to do safely (needs the dead markup removed first) | No — needs the dead markup cleanup first (documented) |
| **Ask Doubt — terminology** | Understand this is "my AI tutor" | Clear "Ask AI Tutor" primary action, always above the fold | Five different names for one concept in one page: "Ask Doubt", "Ask AI Tutor", "Open Mentor", "Mentor Context", "AI mentor" | Medium | Standardize on "AI Tutor" throughout the composer copy | Low | **Yes — done** |
| **Ask Doubt — selectors** | Pick Grade/Subject/Chapter | — | Same dead-duplicate-label issue as Lessons | High | Same as above | Low label / Medium to do safely | No (documented, same root cause as Lessons) |
| **Ask Doubt — recovery** | Recover from a locked/out-of-plan question | Clear "outside your plan" gate with a "See plans →" CTA | None found | Low | — | — | No (already good) |
| **Mock Test — mode cards** | Understand MCQ vs Written vs Mixed | Clear copy per mode | Mode cards use `var(--surface, #fff)` which is never defined as a token, so they render white-on-dark-text regardless of light/dark theme | Medium | Swap to `var(--panel)` (the actual theme token) | Low | No (documented) |
| **Mock Test — negative marking** | Configure a test with confidence | — | "Enable Negative Marking" checkbox does not disable the negative-marks `<select>` — the two controls look linked but aren't | Medium | Bind `disabled={!negativeMarking}` on the select | Low | No (documented) |
| **Mock Test — in-progress exit** | Not lose an in-progress test by accident | — | No confirmation before navigating away mid-test | Medium | Add a confirm-on-navigate guard | Low–Medium | No (documented) |
| **Exam Prep Center — "Test Access"** | Understand my access level | — | "Test Access — early access before student launch" is internal QA language a real student could see | Medium | Replace with student-facing copy or hide for non-QA accounts | Low | No (documented) |
| **Exam Prep Center — study phases** | Know where I am in the 5-phase plan | NTA-style simulated test view is genuinely polished (legend, confirm-before-submit, escalating timer) | The 5 study-plan phases render with no current/completed/future visual state | Medium | Add a "you are here" indicator across phases | Low–Medium | No (documented) |
| **Board Papers — marketing strip** | Get to past papers quickly | Locked/unlocked timeline states are clear | 4 promo cards render above the timeline, pushing real content below the fold, worst on mobile | Medium | Move promo strip below the paper list, or collapse it | Low | No (documented) |
| **Board Papers — loading state** | Trust the page isn't stuck | — | Bare unstyled "Loading…" text, can repeat several times on screen at once | Low | Add a skeleton or single loading indicator | Low | No (documented) |
| **Formulas & Concepts — accessibility** | Trust the math renders correctly | Responsive auto-fill grid genuinely needs no breakpoint | KaTeX was called with `output:"html"`, stripping the MathML annotation — screen readers got **nothing** for any formula | **High** | Drop `output:"html"` (use KaTeX's default `htmlAndMathml`) | Low | **Yes — done** |
| **Formulas & Concepts — labels** | Search/filter without a mouse | — | Search box and both filter `<select>`s had no accessible name | Medium | Add `aria-label`s | Low | **Yes — done** |
| **Formulas & Concepts — chapter nav** | Keep my place while reading a long chapter | — | Chapter list isn't sticky; scrolls away on long chapters | Medium | `position: sticky` on the chapter rail | Low | No (documented — needs layout verification across breakpoints) |
| **Exemplar Research** | Understand what this feature is / how it differs from Lessons & Ask Doubt | Immediate visual feedback on card click, good "Explain This" disabled-state handling | Difficulty filter is skewed (~61% of cards tagged "Hard"), reducing its usefulness; no explicit contrast with Ask Doubt/Lessons | Low | Show counts per difficulty option; add one clarifying sentence | Low | No (documented, cosmetic) |
| **Learn More — external links** | Know I'm leaving the site before I click | Thumbnail-first video cards (no perf cost until clicked); explicit empty state | External links signalled "opens in new tab" only via a visual "→" glyph, nothing for screen readers | Medium | Add visually-hidden "(opens in a new tab)" text | Low | **Yes — done** |
| **Learn More — video metadata** | Judge a video before playing | — | Duration not shown before playing (likely a data gap, not a UI bug) | Medium | Surface duration if the API returns it | Medium (needs backend field) | No (documented) |
| **Analytics — AI Insight** | Understand *why* I got this insight | Good empty state, real per-subject data elsewhere on the page | "AI Insight" is 3 hard-coded strings keyed only on average score — reads as personalized but isn't | Medium | Rename label to be honest about what it is, or compute from real weak-subject data | Low (rename) / Medium (real computation) | No (documented — no calculation change without approval, per scope) |
| **Analytics — trend axis** | See my trend over time | — | X-axis uses "Test 1, Test 2…" instead of real dates | Medium | Use the submission date as the axis label | Low–Medium | No (documented) |
| **Analytics — weak subjects** | Act on what I'm weak at | — | Weak-subject data has no link to Lessons/Practice — dead-end information | High | Add a "Practice this subject" link per subject | Low | No (documented — page not touched this pass to keep the diff focused on navigation) |
| **Leaderboard — fairness transparency** | Understand how ranking works | Good empty state; responsive podium | Ranking is by raw average score with no explanation that test count isn't weighted (1 lucky test can outrank 50 consistent ones) — **flagged for separate product approval, not changed** | High (fairness), documentation-only here | Add a one-line disclaimer near the heading (does not change the calculation) | Low | **Yes — disclaimer added; ranking math untouched** |
| **Leaderboard — "find yourself"** | Locate my own rank quickly | — | No visual indicator of which row/card is "me" despite `user` already being available to the page | High | Highlight the current user's row/card + "(You)" label | Low | **Yes — done** |
| **Platform Walkthrough — placement** | New students: learn the platform. Returning students: rarely need this | Clean toggle, lazy-loaded video per language | Sits in the primary nav next to daily-use tools (Analytics, Leaderboard) | Medium | Move to Help & Account group (this pass's sidebar restructuring does exactly this) | Low | **Yes — done (via sidebar regrouping)** |
| **Platform Walkthrough — a11y** | Know which language is selected | — | Language toggle used color/border only to indicate the active language | Low | Add `aria-pressed` | Low | **Yes — done** |
| **Subscription** | Know my plan, upgrade if I want to | Single-sourced current-plan banner via the canonical resolver; parent-linked students get a clear read-only message | Nav placement was mixed in with daily tools | Low | Move to Help & Account group (done via regrouping) | Low | **Yes — done (via sidebar regrouping)** |
| **Change Password — layout** | Change my password quickly and safely | Correct `autoComplete` attributes, proper label association, no password logging | Card was 760px wide — unnecessarily wide for a 3-field security form; no show/hide toggle | Low–Medium | Narrow the card to ~460px; add a show/hide toggle | Low | **Yes — done** |
| **Change Password — placement** | Find account/security settings | — | Sat next to daily learning tools in the flat nav | Low | Move to Help & Account group (done via regrouping) | Low | **Yes — done (via sidebar regrouping)** |

## Dashboard (detailed — most-visited screen)

| Section | Assessment | Severity | Now? |
|---|---|---|---|
| Up Next / hero | Correctly placed first with the strongest visual treatment; adapts to resume/recommend/cold-start | — | Already good |
| Up Next — fallback path | When the API falls back, `progress.available` is hard-coded `false`, so returning students can never see "Continue Learning" resume state, only a generic recommendation | High | No (documented — needs a real progress-fetch in the fallback path, out of scope for a navigation-focused pass) |
| Today's Goal / Today's Plan | Fallback path fabricates a generic "15 min" goal and checklist rather than marking the goal unavailable | Medium | No (documented) |
| XP Points | Client-side arbitrary formula (`tests*50 + chapters*100`) with no backend XP concept — looks like a real game economy but isn't | Medium | No (documented — needs a product decision, not a UI fix) |
| Achievements | Falls back to 3 hard-coded rows shown even at value 0 — reads as fake/broken gamification | Medium | No (documented) |
| Weak Topics / Recent Tests / Subject Progress / Revision Center | Genuinely computed from real API data, sensible empty states, clickable affordances | — | Already good |
| Orphaned CSS | `components/student/StudentDashboard.css` was a near-duplicate file, never imported anywhere | Low | **Yes — deleted (dead file, zero risk)** |

## Cross-cutting accessibility findings

1. **Math content had no screen-reader fallback** (Formulas & Concepts) — fixed this pass.
2. **Color/glyph-only signals**: external-link "opens in new tab" (Learn More, fixed), language-toggle
   active state (Walkthrough, fixed), MCQ correctness in `JourneyRenderer` (documented, not fixed).
3. **Missing accessible names** on several icon-only/unlabeled controls: mobile hamburger (fixed),
   Formulas search/filters (fixed), various `title`-only tooltips on Mock Test / Board Papers /
   Exam Prep (documented, not fixed — larger surface area than this pass's scope).
4. **No `aria-current`** on the active nav item — fixed this pass.
5. **No Escape-to-close / scroll-lock / backdrop** on the mobile nav drawer — fixed this pass.
6. **Duplicate accessible names from dead markup**: Lessons and Ask Doubt each have a fully
   labelled Grade/Subject/Chapter form that is permanently `display:none` (dead code, kept only for
   its state variables). This blocked a straightforward `aria-label` fix on the *live* selects
   (confirmed by test failure) and is the single highest-value accessibility cleanup left on the
   table — see the implementation plan.

## Notes on scope discipline

No backend APIs, request/response contracts, authentication, role-based access, subscription
entitlement, paid/free plan rules, route URLs, database schema, student progress calculations,
lesson-generation logic, mock-test generation logic, exam-prep calculations, analytics formulas, or
leaderboard ranking math were changed. Where a genuine calculation concern was found (leaderboard
fairness, analytics "insight" honesty), it is flagged here and in the implementation plan for
separate product approval, not silently changed.
