# UI/UX Design Document — Likha Poha AI

_Reverse-engineered from `frontend/src/pages/`, `frontend/src/components/`, `mobile/app/`, and the platform docs on 2026-07-18._

---

## 1. Design Principles

1. **Mobile-first is mandatory** — every admin/teacher/parent/student surface must remain usable on a phone screen, not just desktop.
2. **Backend decides, frontend renders.** UI never independently computes access — it renders the state returned by the canonical subscription/feature-authorization endpoints.
3. **No fabricated data.** Empty or unavailable data states show explicit copy — "Not available yet", "No activity during selected period", "Unable to load" — never blank panels or invented numbers.
4. **Plain business language, not implementation language.** Users see "Platform Access" / "Platform Access (Admin Override)", never "CBSE Access" or raw field names like `access_cbse`.
5. **Time-to-insight targets** drive layout priority:
   - Parent dashboard: understand child's status in **under 10 seconds**.
   - Student dashboard: know the next action in **under 5 seconds**.
   - Teacher dashboard: know who needs attention **without clicking a tab**.
6. **No emoji in the Exam Prep Center** (web or mobile) — use Lucide icons instead. (Other areas of the product do use emoji as informal accents, e.g. section-type icons on the Lessons page — this rule is specific to Exam Prep.)
7. **Graceful degradation everywhere** — every dashboard card handles missing/partial data without breaking layout.

## 2. Theming

- CSS custom properties drive light/dark mode, always with explicit light-mode fallbacks so components never render invisible/mismatched text:
  ```css
  background: var(--surface, #f8fafc);
  color: var(--text, #1e293b);
  border: 1px solid var(--border, #e2e8f0);
  ```
- Applies uniformly across admin form controls, dashboard cards, and panels.
- Brand color: `#6366f1` (indigo) — used as `BRAND_COLOR` in the mobile app constants.

## 3. Navigation Structure by Role

### Student (Web)
Not URL routes — the app is a single page that switches internal view state (`activePage`), so the browser URL doesn't change between them. View keys: `dashboard` · `lessons` · `doubt` · `analytics` · `examPrep` (Gr 11/12) · `subscriptionPlans`. (A `QuizPage.jsx` component exists in the codebase but is unreachable — not imported or routed anywhere; treat as dead code, not a real surface.) The handful of *actual* browser routes are auth/marketing pages: `/`, `/signup`, `/blog`, `/blog/:slug`, `/reset-password`, `/refund-policy`, `/privacy-policy`, `/terms-of-service`.

### Student (Mobile tabs, `mobile/app/(tabs)/`)
Visible in the tab bar: Home (`index.tsx`) · Lessons · Mock Test · Ask AI (Doubt) · Formula · Learn (WebView) · Exemplar (premium) — 7 tabs. Analytics, Exam Prep, and Account exist as screens but are hidden from the tab bar (`tabBarButton: () => null`) and reached via in-app navigation (e.g. a header icon or dashboard link), not tab icons.

### Parent
`/parent` — single dashboard entry point with drill-down child workspace (see §5).

### Teacher
`/teacher` — single-page command center with tab sections (Dashboard, Students, Classrooms, Invitations, Tasks) plus a drill-down Student Workspace.

### Admin
`/admin` — sectioned console: Overview, Accounts, Families & Access, Associations, Offers, AI & Settings, Operations, Bulk Tools, Support, Analytics, plus dedicated pages (Cache & Question Bank, AI Studio, Subscription Settings, Platform Chat, Issues, Payments, Learning Simulation, Lesson Repair, Syllabus Review, Performance Tests, Pricing Calculator, Product Catalogue).

Auth: `/login` · `/signup` (single-step, card-based, Parent/Student roles only — Teacher signup is not public).

## 4. Student Experience

### Dashboard (Option 1 — card-based layout)
1. **Hero row** — "Good morning, {Name}!" greeting only (a first-time-student welcome banner appears separately, below the hero).
2. **Quick Stats row** — Today's Goal · Lessons Left · Next Exam · XP Points.
3. **Main row (1 col)** — single "Up Next" card merging the resume-lesson CTA and today's task checklist (previously three separate cards — consolidated).
4. **Middle row (4 cols)** — Subject Progress · Recent Mock Tests · Weak Topics · Achievements (Day Streak now lives here, as one Achievements item, not a standalone hero card).
5. **Utility row (4 cols)** — Revision Center · AI Doubt Solver · Upcoming Exams · Quick Actions.
6. **Motivation card** — rotating motivational quote.

Responsive collapse: 4-col → 2-col (tablet) → 1-col (mobile).

### Lessons Page (July 2026 redesign)
- **Compact horizontal top bar** (replaced the old left sidebar): Grade selector · Subject selector · Chapter selector · Step N/N pill · Generate/Refresh action. Full page width goes to lesson content.
- **Workbook layout** — all sections render expanded inline with a colour-coded left border (not an accordion):

| Section type | Border colour | Icon |
|---|---|---|
| Introduction/Overview | Blue | 🎯 |
| Concept/Explanation | Amber | 📘 |
| Example/Worked | Green | 🧪 |
| Warning/Mistake | Orange | ⚠️ |
| Quick Check/Question | Red | ✅ |
| Summary/Recap | Purple | 📌 |

- **Floating TOC button** (`≡`, fixed to the right edge) opens a dark panel of section headings; clicking scrolls to and closes.
- **Listen to Lesson (TTS)** button — checks the pre-warmed audio cache first (instant CDN playback), falls back to live generation (~15–20s) with a loading state.
- **Feature flags** — `USE_TOP_BAR_LAYOUT` in `LessonsPage.jsx`; `USE_WORKBOOK_LAYOUT`/`USE_CARD_FEED_LAYOUT` in the child component `LessonSections.jsx`. The codebase keeps prior layout options behind flags rather than deleting them, useful for fast rollback.

### Ask Doubt Page
Mirrors the Lessons page's compact top bar; the "Mentor Context" sidebar is hidden and the doubt input takes full width.

### Formula Sheet
Chapter-wise, Grade 5–12. Free tier sees a preview (first 3 formulas/chapter: name + expression + description only); paid tier gets full expansion (examples, memory tips, MCQ practice) rendered with KaTeX. Upgrade prompt uses the same "Exemplar-style" modal pattern used elsewhere for premium gating, for UI consistency.

### Exam Prep Center (Grade 11/12 only)
- Grade 5–10 students see a grade-ineligible lock screen.
- Free/Nano on Grade 11/12 see a preview-only lock.
- Stream (PCM/PCB/PCMB) determines which exams (JEE Main, NEET UG, CUET UG, SAT, IELTS, TOEFL iBT) are eligible — shown as per-exam eligibility badges, not a single yes/no.
- Explanation text for questions is split into separate visually distinct steps (`Step N:`, `Option X:`, `Therefore`) rather than one dense paragraph.
- **Design intent is icons-only, no emoji** (§1) — **not currently met**: `ExamPrepPage.jsx` (web) and `examprep.tsx` (mobile) both use emoji extensively (exam-type icons, stream/subject icons, result feedback icons). This is a real gap between the stated guardrail and shipped code, not a doc error — worth a dedicated cleanup pass to swap these for Lucide icons.

## 5. Parent Experience

Component-driven dashboard, extracted for reuse and testability:

| Component | Purpose |
|---|---|
| `ParentHeroSummary` | Greeting, child count, plan chip, urgent banner, primary CTAs |
| `ParentChildStatusCard` | Status badge (Doing Well / Restricted / Inactive / Expiring), stats, progress bar, top recommendation |
| `ParentActionPlan` | "Things to Do Tonight" — synthesized from recommendations + notifications |
| `ParentNotificationGroups` | Grouped: Needs Attention / Good News / Upcoming / Platform Access, with mark-read |
| `ParentAccessExplanation` | Explains current plan using "Platform Access" terminology + feature badges |
| `ParentProgressStory` | Visual progress: subject bars, score trend, strengths, needs-practice list |
| `ParentChildWorkspace` | 9-tab drill-down drawer: Overview, Today's Plan, Progress, Strengths & Needs, Mock Tests, Homework & Exams, Notifications, Platform Access, Report |

**Add Child modal** shows the credentials panel (login_id/login_email, one-time password) with copy buttons immediately after child creation, plus "what to do next" guidance. The "child limit reached" upgrade card only appears once the parent is genuinely at their plan's child limit — never on first open with zero children.

## 6. Teacher Experience — Command Center UX (Phase 3)

Single-page productivity layout (Notion × Linear × Google Classroom in tone):

- **Dashboard tab (default)** — hero greeting + KPI cards + attention queue + today's tasks + pending invitations + student preview, all visible without navigating away.
- **Students tab** — full roster, search, health indicators, opens `StudentWorkspace`.
- **Classrooms tab** — create/manage + `ClassroomAnalyticsCard` per classroom.
- **Invitations tab** — CRUD with status filter.
- **Tasks tab** — open/completed/dismissed with badge counts.

`StudentWorkspace` is a 7-section detail view: Overview, Progress, Assessments, Notes, Activity, Parent, Settings. Private notes are visually marked as teacher-only and never leak into student/parent-facing views.

`TeacherAssistantCard` — rule-based (no external AI call) summary surfacing: students needing attention, open high-priority tasks, pending/expiring invitations, recommended next actions.

`InterventionQueue` groups students into Critical / Needs Review / Low-Priority-Doing-Well, each row actionable (view student, create task, add note, reset password, email credentials if paid, message parent if linked).

## 7. Admin Experience

- Mobile-friendly Admin Console, tab-organized (not a dense single desktop table view).
- **Quick Actions, Global Search, Favorites/Pinned Actions, Recent Activity, Notification Center** — productivity affordances layered on top of the section tabs.
- **Cache & Question Bank Management** page: grade-by-grade and chapter-by-chapter prewarm controls with dynamic cost estimates, plus the Exam Prep question bank workflow (AI generation form → paste/import panel with per-question validation report → review/publish panel with bulk actions and a "Copy for AI Review" ChatGPT-prompt export).
- **AI Studio**: provider dropdown (9 providers) with model dropdown cascading from suggested models per provider, plus a free-text "✎ Enter custom…" escape hatch; per-feature model routing table; prompt template editor with version history.
- **Subscription Settings**: per-plan card editor (price, discount, duration, token limits, included/not-included feature lists, Exam Prep/Exemplar toggles, visibility) — changes apply immediately, no deploy.
- **View as User**: frontend-only read-only simulation (never issues a real user JWT), always shows a persistent banner, and blocks destructive/payment/admin actions while active.
- **Product Bugs page**: default-hides closed issues, per-row Close button, bulk toolbar (Close Selected / Won't Fix / "Copy All for Codex" prompt export) — designed to feed directly into an AI coding assistant workflow.

## 8. Mobile-Specific UX Notes

- Tab bar carries the Likha Poha logo in the header (`AppHeader.tsx`).
- Grade lock: free-tier students are locked to their enrolled grade throughout lessons/mock-test/doubt.
- Grade 11/12 subject filtering: `cbse_subjects` from the profile is primary; stream-derived subjects (PCM/PCB/PCMB/Commerce/Humanities) are the fallback, used only when `cbse_subjects` is empty.
- Loading state uses a branded thinking animation (`likhapohaai.gif`) rather than a generic spinner during AI generation waits.
- Admin Panel, Teacher Platform, and Sales tools are intentionally **not** built on mobile — those roles are expected to use the web app.

## 9. Accessibility & Error-State Conventions

User-facing copy is deliberately friendly and never leaks internals:

| Situation | Shown to user |
|---|---|
| Session expired / no token | "Your session has expired. Please sign in again." |
| 401/403 | "Your session has expired. Please sign in again." |
| 500 | "We're having trouble right now. Please try again in a moment." |
| Missing optional data | "Not available yet" / "No activity during selected period" |
| Business validation error (400) | Shown as-is (already user-appropriate) |

Never shown to users: raw JWTs, Supabase/RLS internals, bearer tokens, raw 500 stack traces.
