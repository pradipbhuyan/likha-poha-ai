# App Flow Document — Likha Poha AI

_Reverse-engineered from `backend/app/routes/`, `frontend/src/App.jsx`, `mobile/app/_layout.tsx`, and platform docs on 2026-07-18. All flows below reflect the code as currently implemented, not aspirational behavior._

---

## 1. Authentication Flows

### 1.1 Email/Password Signup (New Student or Parent)

```
User fills SignupPage (name, email, password[, grade for student])
  → POST /api/auth/signup-free
      → Create Supabase auth user (email_confirm=True)
      → Insert profile row (role, grade if student, board=CBSE, oauth_profile_complete=True)
      → Plan = Free Tier by default
      → Send welcome email (Resend; failure is non-fatal)
  → Client: supabase.auth.signInWithPassword(email, password)
  → Supabase issues JWT
  → GET /api/auth/me → { needs_role_selection: false } → route to role-appropriate dashboard
```
Child accounts (created by a parent, not self-signup) use a synthetic email `{username}@child.likhapoha.in`, `email_confirm=True` so the child can log in immediately, and a one-time temporary password shown once in the parent's UI (never stored in the profile).

### 1.2 Google OAuth — Web

```
App.jsx mounts
  → explicit supabase.auth.exchangeCodeForSession(window.location.href) attempted on mount (PKCE)
  → onAuthStateChange(SIGNED_IN)
      → reliability check: hasAppProfile = !!localStorage.getItem("tutor_user")
      → SIGNED_IN + no app profile → always treated as a fresh login (works across devices)
  → GET /api/auth/me
      → needs_role_selection=true (new OAuth user) → one-time role/grade picker
      → needs_role_selection=false → route to dashboard
  → SIGNED_OUT → /login
```
`POST /api/auth/oauth/complete-profile` sets `oauth_profile_complete=true`; returns `409 role_conflict` if the role is already set (blocks re-submission).

### 1.3 Google OAuth — Mobile (WebView, implicit flow)

```
handleGoogleLogin()
  → supabase.auth.signInWithOAuth({ redirectTo: "likhapoha://", queryParams: { prompt: "select_account" } })
  → Opens a NativeWebView modal (not Chrome Custom Tab — see TRD §7 for why)
  → User authenticates with Google
  → Redirect arrives as either:
      likhapoha://...#access_token=...   (implicit — normal path)
      https://likhapoha.in?code=...      (PKCE — fallback path, handled but not primary)
  → WebView.onShouldStartLoadWithRequest intercepts the redirect URL
  → handleOAuthSuccess() detects which flow arrived and branches:
      #access_token= present → supabase.auth.setSession({ access_token, refresh_token })
      ?code= present, no hash  → supabase.auth.exchangeCodeForSession(callbackUrl)
  → checkAuthState(session.access_token) called directly (NOT left to the onAuthStateChange listener,
    which has known timing conflicts)
      → needs_role_selection=true → router.replace("/auth/role-select")
      → needs_role_selection=false → router.replace("/(tabs)")
```

### 1.4 Mobile App Boot / Session Recovery

```
_layout.tsx bootstrap
  → supabase.auth.getSession()
  → session exists → GET /api/auth/me
      → needs_role_selection=true  → /auth/role-select
      → needs_role_selection=false → /(tabs)
      → backend unreachable        → fallback to /(tabs) (fail open on transient network issues)
  → no session → /auth/login
```
A `wasAuthenticated` ref guards against a known Supabase quirk: firing `SIGNED_OUT` then `SIGNED_IN` when a session is replaced mid-OAuth. Once auth state has reached `ready`/`needs_role`, a later spurious `unauthenticated` event is ignored — only an explicit `signOut()` call resets it.

## 2. Access-Decision Flow (every gated request)

```
Request + JWT
  → get_current_user()                         [401 if invalid/missing]
  → Subscription Resolver
      resolves canonicalPlanKey, accessLevel, hasFullAccess, expiresAt, childLimit, restrictions
      (normalizes legacy DB values — e.g. profiles.subscription_plan="free" → actually means Premium Nano)
  → Feature Authorization Service
      checks requested feature against resolved plan
      (DB-driven override for EXAM_PREP_CONTENT / EXEMPLAR / EXEMPLAR_RESEARCH via subscription_plan_settings)
  → allowed=true  → endpoint executes
  → allowed=false → 403 with { feature, canonicalPlanKey, reason, upgradeMessage }
  → Frontend renders allowed/restricted state (never assumes access from a plan string it read itself)
```

## 3. Payment / Upgrade Flow

### 3.1 Subscription Upgrade (existing user)
```
1. User opens Subscription Plans page, selects a plan
2. POST /api/payments/create-order { plan_key }
     → Backend creates Razorpay order server-side (amount from subscription_plan_settings, minus discount)
     → Returns { order_id, amount, key_id }
3. Client opens Razorpay checkout widget; user pays (UPI/card/etc.)
4. Razorpay returns payment_id + signature to the client
5. POST /api/payments/verify { order_id, payment_id, signature }
     → Backend verifies HMAC-SHA256 signature
     → Idempotency guard on razorpay_payment_id
     → Activates the intended plan (never the raw charged amount)
     → Updates profile: access_cbse=true, subscription_expires_at = now + duration_days
     → Writes audit event (audit_log_service)
     → Writes subscription_timeline event (idempotency key)
6. Subscription Resolver now reflects the new plan on next read
7. Client refreshes → GET /api/auth/me shows new access flags → lessons/doubts/exam prep unlock
```

### 3.2 Paid Signup (new user selecting a paid plan at signup)
```
1. POST /api/auth/signup-order { email, plan_key } → Razorpay order created
2. Client completes Razorpay checkout
3. POST /api/auth/complete-signup { razorpay_payment_id, signature, ... }
     → Verifies signature
     → Creates Supabase auth user + profile in one flow, with the paid plan already active
     → Records payment
```

### 3.3 Admin ₹1 Test Payment
Admin-only tool; charges ₹1 in the test flow but activates by the **intended plan ID**, not the ₹1 charged amount; preserves normal checkout pricing for real users; every use is audited.

## 4. Core Learning Flows

### 4.1 Generate an AI Lesson
```
1. Student opens Lessons (top bar: Grade/Subject/Chapter selectors + Step pill)
2. GET /api/auth/me → grade, stream, cbse_subjects (drives which subjects are selectable)
3. GET /api/syllabus → full grade→board→subject→chapter tree
4. GET /api/subscription/features → per-feature allowed flags (gates Exemplar chapters, etc.)
5. Student selects Grade → Subject → Chapter → Step, taps Generate
6. POST /api/lesson/generate { grade, subject, chapter, step_title }
     → If chapter name contains "Exemplar:" → authorize Feature.EXEMPLAR (403 for free users;
       admins/teachers/all-access test accounts exempt)
     → Check lesson_kb / lesson_cache → cache hit → return cached content instantly
     → Cache miss → build prompt from active AI Studio template → call primary LLM provider
       → on timeout/429 → automatic fallback provider retry
     → Parse/validate response → store in cache → return structured lesson markdown
7. Frontend renders Workbook-layout sections (colour-coded by type) + optional "Listen to Lesson" TTS
```

### 4.2 Ask a Doubt
```
1. Student submits a question on the Doubt page (full-width input, top bar pattern)
2. POST /api/doubt/answer { grade, subject, question, style_instruction? }
     → Feature authorization check (Free tier = limited)
     → Build contextual prompt (grade + subject + NCERT alignment), optionally RAG-grounded
     → Call LLM → response
     → Save to doubt_history
     → Return { success: true, answer: markdown }
3. LKB/DKB quick-doubt chips suggest common follow-ups (Lesson KB chips take priority over Doubt KB chips)
```

### 4.3 Mock Test → Analytics
```
1. POST /api/mock-test/generate → backend returns N MCQs with options {A,B,C,D} + answer key
2. Student answers all questions, taps Submit
3. Score computed (percentage, raw_score, max_score — never a raw "score" column, which does not exist)
4. POST /api/analytics/test-history { username, grade, subject, percentage, raw_score, max_score, ... }
     → Saved to test_history
5. Wrong answers optionally tracked in mock_test_wrong_answers
6. Analytics/Dashboard reflect the update on next load (via _normalize_score_pct() everywhere a score renders)
```

### 4.4 Exam Prep Access Check (Grade 11/12)
```
Frontend always calls GET /api/exam-prep/access-check — never infers access from a plan string.
Response: { grade_eligible, has_access, preview_only, reason, stream_missing,
            exam_eligibility: {jee_main, neet_ug, cuet_ug}, canonical_plan_key }

reason ∈ { full_access | free | nano | admin | test_user | grade_ineligible }

Grade 5–10           → grade_eligible=false → lock screen
Grade 11/12 Free/Nano → preview_only=true   → preview lock
Grade 11/12 Premium+  → stream-dependent per-exam eligibility
admin / test_user (akshita.teststudent) → full access, all exams eligible, overrides stream
```

## 5. Parent Flows

### 5.1 Add Child
```
1. Parent opens Add Child modal (child count shown; upgrade card only appears if already at plan limit)
2. Parent submits name/username/grade (Grade 5–10 only)
3. Backend: create Supabase auth user + profile in one atomic operation
     → If profile insert silently fails → rollback the just-created auth user → return 500
       (prevents orphaned auth users with no profile)
4. Response includes login_id + login_email
5. Frontend shows credentials panel (copy buttons) once, plus "what to do next" instructions
6. New child always starts on Free Tier, access_cbse=false — parentId alone never implies paid access
```

### 5.2 Parent Dashboard Load
```
GET /api/parent/dashboard/summary
  → children list with subscription state, feature badges (from get_feature_summary(), never raw access_cbse),
    recent activity, recommendations, notifications
GET /api/parent/children/{id}/detail | /analytics | /academic-insights | /progress-report
  → all endpoints enforce _verify_child_ownership(parent_id, child_id)
  → progress-report never includes teacher-private notes
```

## 6. Teacher Flows

### 6.1 Dashboard Load (Command Center)
```
GET /api/teacher/dashboard/summary (implied canonical summary)
  → roster, invitations, classrooms, tasks, interventions rendered without further tab navigation
GET /api/teacher/interventions        → prioritized queue (Critical/Review/Low)
GET /api/teacher/tasks                → open/completed/dismissed
GET /api/teacher/students/{id}/timeline → unified student activity timeline
```

### 6.2 Intervention → Action
```
Teacher sees a student flagged in InterventionQueue
  → View Student (opens StudentWorkspace)
  → Create Task (POST /api/teacher/tasks, optionally pre-filled via SuggestedTaskModal from the intervention)
  → Add private Note (POST /api/teacher/students/{id}/notes — visibility=teacher_private, never shown to
    students or parents)
  → Reset Password / Email Credentials (credential email is paid-plan-only)
  → Message Parent (POST /api/teacher/students/{id}/message-parent, if a parent link exists;
    GET .../parent-contact returns has_email only — never the raw email address)
All of the above write a sanitized audit event.
```

## 7. Admin Flows

### 7.1 Question Bank — AI Generation
```
Admin selects Exam/Grade/Subject/Topic/Count/Publish-mode/Difficulty-mix
  → POST /api/admin/exam-prep/question-bank/prewarm
  → All generated questions saved as draft, unless publish_mode=auto_publish AND validation passes
  → Admin reviews in the Review & Publish panel → per-question or bulk Publish/Archive
```

### 7.2 Question Bank — Paste & Import (ChatGPT/Custom GPT)
```
Admin pastes a JSON array generated externally
  → POST /api/admin/exam-prep/questions/import-bulk
  → 6-tier validation pipeline:
      1. Required fields present
      2. Field values valid (exam_type, difficulty, correct_option, options A-D)
      3. GPT self-invalidation phrase detection
      4. Answer-mismatch detection (stated conclusion ≠ correct_option) → imported_with_warning
      5. Exact dedup via MD5(question_text)
      6. Passing rows saved as draft
  → Grade/source_type/marks auto-sanitized before insert (DB constraint only allows "Grade 11"/"Grade 12")
  → Returns per-question report: imported / warnings / skipped_duplicate / skipped_invalid
  → Review panel auto-refreshes
```

### 7.3 Expiry Sweep (background/admin-triggered)
```
Expiry Job Service
  → finds paid subscriptions past subscription_expires_at
  → falls back each to Free Tier or valid offer-code access
  → never touches admin-granted access
  → idempotent — safe to re-run
  → status/last-run visible on the Admin Operations Dashboard, with a manual "run now" control
```

## 8. Platform Chat Flow

```
GET /api/chat/settings — always called before showing the chat widget; access never inferred from plan string.

Access logic (evaluated in this order):
  global_enabled=false                    → nobody can chat (admin kill-switch wins)
  role ∈ {admin, teacher}                 → always enabled
  user_id ∈ admin_settings.chat_access_users → enabled (manual grant)
  subscription_plan != free               → auto-enabled
  otherwise                               → disabled

Attachments: images >2MB auto-compressed client-side; all files served via a 1-hour signed Supabase URL
(never public); voice messages recorded via the browser MediaRecorder API (WebM).
```

## 9. Data-Flow Summary Diagrams

### Dashboard KPI loading (all roles)
```
Role dashboard mounts → GET /api/{role}/dashboard/summary (single canonical endpoint)
  → avoids N independent duplicate KPI queries
  → frontend renders cards, showing "Not available yet" for any field the backend marks unavailable
```

### TTS Playback
```
Frontend requests audio for a lesson step
  → GET /api/tts/cached-url
      → cached=true  → play Supabase CDN URL directly (instant)
      → cached=false → POST /api/tts/generate → Edge TTS (~15-20s) → play, and the result
        is written to lesson_audio_cache for future instant hits
```
