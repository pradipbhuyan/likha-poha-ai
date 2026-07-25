# Likha Poha AI — Student Navigation Architecture (Phase 2)

## Current state

The sidebar (`frontend/src/components/Sidebar.jsx`) renders one flat, ungrouped list of buttons for
every role. For a student it previously read, top to bottom:

Dashboard, Lessons, Ask Doubt, Mock Test, Formulas & Concepts, Exemplar Research, Learn More,
Exam Prep Center, Board Papers, Analytics, Leaderboard, Platform Walkthrough, Subscription,
Change Password — then a pinned Logout.

Problems this caused (see `docs/student-ux-audit.md` for the full evidence):

- Daily-use tools (Lessons, Ask Doubt, Mock Test), revision tools (Formulas, Exemplar, Learn More),
  progress views (Analytics, Leaderboard), and account/support items (Walkthrough, Subscription,
  Change Password) were interleaved with no visual separation — a new student has to read all 14
  labels to figure out what's "for today" vs. "for later."
- No `aria-current` on the active route, no focus-visible outline, no landmark label on the nav.
- The mobile drawer had no Escape-to-close, no backdrop, and didn't lock background scroll.

## Options considered

### Option A — Journey-based (single flat list, reordered by learning sequence)

Dashboard → Lessons → Ask Doubt → Mock Test → Exam Prep Center → Board Papers → Formulas & Concepts
→ Exemplar Research → Learn More → Analytics → Leaderboard → Platform Walkthrough → Subscription →
Change Password (no group headers, just reordering).

- **Pros:** Zero new UI (no group-label component/CSS needed); order alone nudges the intended
  journey; lowest implementation risk.
- **Cons:** Still a 14-item list with no visual chunking — a student scanning the sidebar gets no
  "landmarks" to jump to, and the list is long enough (especially on a 13" laptop or tablet) that
  grouping meaningfully reduces scan time. Doesn't address "where is X" as directly as grouping.

### Option B — Grouped by student goal (Home / Learn / Practise & Prepare / Revision Tools / Progress / Help & Account)

The structure proposed in the task brief.

- **Pros:** Directly answers the seven orientation questions this audit is optimizing for ("what do
  I do today," "where do I learn," "where do I practise," "where do I prepare for an exam," "where
  do I revise," "where's my progress," "where's account/support"). Each group name maps to one of
  those questions. At most one level of grouping (no nested/expandable menus), so it doesn't add
  interaction cost — group labels are inert text, not accordions. Matches the "5±2 chunks" rule of
  thumb for short-term memory/scanning, especially valuable for CBSE Grade 5–8 students who
  benefit most from explicit chunking.
- **Cons:** Slightly more markup/CSS (group label styling) than Option A; a small risk that a
  6-group taxonomy reads as "more to learn" than a flat list to some students — mitigated by making
  group labels visually subtle (small, muted, uppercase, non-interactive) rather than prominent.

### Option C — Frequency-based (most-used features first, support/account last, no groups)

Sort by (estimated) click frequency: Dashboard, Lessons, Mock Test, Ask Doubt, Board Papers,
Exam Prep Center, Analytics, Formulas & Concepts, Leaderboard, Exemplar Research, Learn More,
Subscription, Change Password, Platform Walkthrough.

- **Pros:** Optimizes for the single next click for a "power user" who already knows the app.
- **Cons:** No natural session log exists to validate real frequency (frontend has no click-analytics
  instrumentation for nav items), so this ordering would be a guess dressed up as data — a real
  fairness/evidence problem for a change this visible. It also does nothing for discoverability of
  *unfamiliar* features (a big problem for competitive-exam students who may not know Exam Prep
  Center or Board Papers exist yet), and still doesn't chunk the list visually.

## Decision: Option B (grouped), using the group taxonomy proposed in the brief

**Scoring against the stated criteria:**

| Criterion | A (Journey, flat) | B (Grouped) | C (Frequency, flat) |
|---|---|---|---|
| Frequency of use | Partial (order helps) | Partial (order + grouping helps) | Best in theory, unverifiable in practice |
| Importance to learning | Good | Good | Weak (buries Exam Prep/Board Papers under guesswork) |
| Logical learning sequence | Good | Good (sequence *and* grouping) | Poor |
| Discoverability | Medium | **Best** — group labels act as signposts for unfamiliar features | Poor for unfamiliar features |
| Cognitive load | Medium (still one long list to scan) | **Best** — chunking reduces scan effort | Medium |
| Younger-student comprehension (Grade 5–8) | Medium | **Best** — explicit "Learn" / "Practise & Prepare" labels teach the mental model | Medium |
| Competitive-exam student needs | Good (Exam Prep near Mock Test) | **Good** (same adjacency, plus its own group signals "this matters") | Poor (order not guaranteed to surface it) |
| Desktop usability | Good | Good | Good |
| Mobile usability | Good | Good (groups still fit one drawer, no extra taps) | Good |
| Interactions required | 1 tap (unchanged) | **1 tap (unchanged — group labels are not clickable)** | 1 tap (unchanged) |
| Scroll to reach key features | Same content length as before | Same content length as before (grouping doesn't add height beyond label rows) | Same content length as before |

Option B wins on discoverability and cognitive load — the two axes this audit's screen-by-screen
review flagged most often — without costing anything on interaction count or requiring nested/
expandable menus. Option A is the safe fallback if group-label styling is ever rejected; Option C
was rejected for lacking any real usage evidence to justify reordering by "frequency."

## Selected structure

```
HOME
  1. Dashboard

LEARN
  2. Lessons
  3. Ask Doubt

PRACTISE & PREPARE
  4. Mock Test
  5. Exam Prep Center
  6. Board Papers

REVISION TOOLS
  7. Formulas & Concepts
  8. Exemplar Research
  9. Learn More

PROGRESS
  10. Analytics
  11. Leaderboard

HELP & ACCOUNT
  12. Platform Walkthrough
  13. Subscription
  14. Change Password

BOTTOM-PINNED
  15. Logout
```

This matches the brief's recommended initial candidate; the audit surfaced no evidence to override
it (if anything, the Walkthrough/Subscription/Change Password placement audit findings *confirm*
Help & Account is the right home for those three — see `docs/student-ux-audit.md`).

## Implementation notes (how this stays low-risk)

- Group membership is a plain `group: "Learn"` string field added to each page's config object in
  `Sidebar.jsx` — no new data model, no route changes, no permission changes.
- Group headers are rendered **only when `user.role === "student"`**. Admin, teacher, sales, and
  parent navigation is completely unaffected (still the flat list they already rely on), because
  none of those roles' page objects received a `group` field except the ones a student can also
  see (e.g. Exemplar Research, shared with teacher) — and rendering is gated on role, not on the
  presence of the field, so even shared entries never show a stray label to non-students.
- Group labels are a plain, non-interactive `<p className="sidebar-group-label">` — not a button,
  not a link, not `aria-expanded` — satisfying "at most one level of grouping, no repeated
  expansion for common features."
- Item order is achieved by reordering the existing config objects in the array; no page's `key`,
  `roles`, `hideForAdmin`, `gradeFilter`, or `testUsers` fields were touched, so permission and
  grade-gating behavior is byte-for-byte unchanged (see the route mapping table in the final report
  for a per-route diff).
- Since the app has no per-page URL routing (see the architectural note in
  `docs/student-ux-audit.md`), reordering/grouping the sidebar carries none of the "route
  changed" or "deep link broke" risk it would in a URL-routed app — there was never a URL to break.
