# Likha Voice Tutor — Context and Implementation Plan

## Status

**Proposal only — no product implementation is included in this document.**

Likha Voice Tutor will be introduced as a dedicated student-facing destination in the application sidebar. It extends the existing, secure doubt-answering and Likha narration capabilities into a conversational experience:

```text
Student asks a question by typing or speaking
    ↓
Question transcript is visible and editable
    ↓
Existing authenticated doubt-answer pipeline selects the best answer
    ↓
DKB → textbook/LKB/RAG → eligible LLM fallback
    ↓
Likha displays the answer, source/trust information, and reads the answer aloud on request
```

The design deliberately avoids a second tutoring or retrieval pipeline. Likha Voice Tutor is a user experience layer over the current educational-answer infrastructure.

---

## Product objective

Give students a single, approachable place to ask academic questions and hear an accessible explanation from Likha.

The feature should help students who:

- learn more effectively by listening;
- find long written explanations difficult to process;
- want a calm, guided explanation after asking a doubt;
- prefer speaking a question instead of typing;
- need a quick spoken recap of a textbook-grounded answer.

Likha must remain an **optional, learner-controlled academic guide**. She should not auto-play, auto-record, interrupt lessons, or act as an unbounded general-purpose chatbot.

---

## Existing foundations

### Existing answer pipeline

The current authenticated endpoint is:

```http
POST /api/doubt/answer
```

The endpoint already enforces authentication, student access, grade/board restrictions, account standing, feature entitlement, quotas, and academic guardrails.

Answer-routing order:

1. **Doubt Knowledge Base (DKB)**
   - Direct lookup by `dkb_id` for suggested questions.
   - Text/semantic match for a typed question.
   - Fast and low-cost.
   - Used by all students.
   - Free tier is DKB-only.

2. **Textbook/LKB/RAG answer**
   - Searches grounded learning content.
   - Returns source metadata and textbook visuals when available.
   - Used for eligible students when DKB does not answer the question.

3. **Live LLM fallback**
   - Available only where entitlement rules allow it.
   - Retains source-type transparency.
   - Subject to existing paid-tier AI limits.

The route returns data already required by Voice Tutor:

```json
{
  "success": true,
  "answer": "…",
  "source_type": "DOUBT_KB | TEXTBOOK_EXCERPT | TEXTBOOK_EXCERPT_WEAK | WIDER_LLM_KNOWLEDGE | …",
  "sources": [],
  "textbook_visuals": [],
  "mentor_suggestions": [],
  "history_id": "…"
}
```

### Existing narration infrastructure

`AvatarNarrator.jsx` already provides:

- Likha avatar artwork and speaking state;
- neural speech with browser-speech fallback;
- English/Hindi voice selection;
- play, pause, resume, stop, replay, and speed controls;
- safe cancellation of active audio;
- accessible status updates;
- no audio triggered by scrolling.

Current voice mapping:

| Language | Likha voice |
|---|---|
| English | `en-IN-NeerjaNeural` |
| Hindi | `hi-IN-SwaraNeural` |

The existing chapter narration endpoint intentionally restricts audio generation to known chapter milestones and wrap-ups. It should remain restricted and must **not** be modified to accept arbitrary client text.

### Existing policies to preserve

- Free-tier doubt behavior remains DKB-only.
- Existing free/paid doubt limits remain the source of truth.
- Existing source labels and citations remain visible.
- Students may not ask outside their enrolled grade or board.
- Non-academic questions are redirected by the existing academic guardrail.
- No voice recording is stored by default.
- The written answer is the source of truth; audio must not invent additional content.

---

## Scope

### Phase 1: typed question plus spoken answer

This phase creates the dedicated **Likha Voice Tutor** sidebar page.

Included:

- Sidebar link and application route.
- Grade, subject, and chapter context controls.
- Typed academic question input.
- Existing `/api/doubt/answer` request flow.
- Displayed answer with existing source/trust metadata.
- Optional **“Listen to Likha”** response read-aloud.
- Playback controls and animated avatar states.
- Browser Speech Synthesis fallback if neural audio is unavailable.
- Suggested DKB questions.
- Responsive and keyboard-accessible UI.
- Focused frontend tests.

Not included:

- microphone capture;
- browser speech recognition;
- server-side transcription;
- voice recording retention;
- voice conversation history beyond existing doubt history;
- automatic audio playback;
- usage outside the dedicated page.

### Phase 2: browser voice input

Included:

- Browser `SpeechRecognition` / `webkitSpeechRecognition` feature detection.
- English/Hindi recognition language control.
- Microphone permission request only when the learner presses **Ask by voice**.
- Live/transcribed text shown in the input field.
- Transcript remains editable before sending.
- Typed fallback remains available at all times.
- Clear unsupported-browser and denied-permission states.

Not included:

- audio upload to backend;
- permanent audio storage;
- server-side transcription.

### Phase 3: secure server transcription fallback

Included only if browser support and real-device testing show it is necessary.

Included:

- Short, explicit microphone recording flow.
- Server-side speech-to-text provider abstraction.
- Transcription-specific rate limits.
- Maximum recording length.
- Audio discarded immediately after successful transcription unless a future, separately approved policy requires storage.
- Transcript confirmation before it reaches the academic-answer pipeline.
- Privacy notice suitable for student users.

### Phase 4: contextual integrations

After the standalone page is stable, reuse the same Voice Tutor component in selected high-value contexts:

1. **Doubt Solver** — “Listen to Likha explain this answer.”
2. **Mock test result review** — explain an incorrect answer aloud.
3. **Chapter journey** — ask a question constrained to the open chapter.
4. **Weak-topic revision** — short, targeted spoken concept refreshers.

Do not add Likha voice interactions inside active timed tests.

---

## UX design

### Sidebar entry

Add a student-only sidebar item:

```text
Likha Voice Tutor
```

Suggested icon: microphone, message-circle, or bot/volume icon.

Suggested tooltip/description:

```text
Ask a question and hear Likha explain it.
```

Placement:

- In the student learning tools section.
- Near **Lessons** and **AI Doubt Solver**.
- Do not expose it in parent, teacher, principal, sales, or admin navigation during Phase 1.

### Main page structure

1. **Header**
   - Avatar in idle state.
   - Heading: `Likha Voice Tutor`
   - Subheading: `Ask an academic question and hear Likha explain it clearly.`
   - Quiet status note: `Likha only speaks when you choose Listen.`

2. **Learning context**
   - Grade selector.
   - Subject selector.
   - Chapter selector.
   - Default context from authenticated user profile, matching current Doubt page behavior.
   - Context is visible before asking, so students can correct it.

3. **Question composer**
   - Text area.
   - Prompt: `What would you like Likha to explain?`
   - Primary action: `Ask Likha`.
   - Secondary/disabled-in-Phase-1 action: no microphone button until Phase 2.
   - Suggested DKB question chips below the composer.

4. **Thinking state**
   - Avatar switches to explaining/preparing state.
   - Status: `Likha is checking your learning materials…`
   - Do not claim textbook grounding until `source_type` is returned.

5. **Answer card**
   - Source label.
   - Written answer.
   - Textbook visuals/citations where returned.
   - Actions:
     - `Listen to Likha`
     - `Pause` / `Resume`
     - `Stop`
     - speed selector
     - `Ask a follow-up`
   - Suggested follow-up prompts from the existing backend response.

6. **Error and access states**
   - Existing backend message is shown without exposing internal system errors.
   - Free-tier DKB miss: show existing upgrade guidance.
   - Rate limit: show existing limit message.
   - Empty answer: clear recovery action to try again.

### Learner control rules

- Audio never starts automatically.
- Sending a new question stops active audio.
- Navigating away or unmounting stops active audio.
- Student can replay an answer.
- Student can choose speech speed.
- A visible written transcript remains available while audio is playing.
- No audio should be generated or spoken for an empty or failed response.

---

## Technical architecture

### Frontend components

Proposed files:

```text
frontend/src/pages/LikhaVoiceTutorPage.jsx
frontend/src/components/likha/LikhaVoicePlayer.jsx
frontend/src/components/likha/LikhaVoiceTutorComposer.jsx
frontend/src/api/likhaVoiceTutor.js
frontend/src/tests/LikhaVoiceTutorPage.test.jsx
```

The existing `AvatarNarrator.jsx` can be refactored later into shared primitives, but Phase 1 should avoid destabilizing chapter narration. Reuse patterns and assets first; extract shared logic only if duplication becomes difficult to maintain.

Suggested responsibilities:

| Component | Responsibility |
|---|---|
| `LikhaVoiceTutorPage` | page state, syllabus context, answer lifecycle, sidebar destination |
| `LikhaVoiceTutorComposer` | typed prompt, submit state, DKB suggestion chips |
| `LikhaVoicePlayer` | avatar state, neural audio request, browser TTS fallback, playback controls |
| `likhaVoiceTutor.js` | API calls only |

### Phase 1 API approach

#### Answer generation

Reuse exactly:

```http
POST /api/doubt/answer
```

The page sends the same context currently used by `DoubtPage.jsx`:

```json
{
  "username": "authenticated username",
  "grade": "Grade 6",
  "mode": "CBSE",
  "board": "CBSE",
  "subject": "Science",
  "chapter": "Light, Shadows and Reflections",
  "question": "Why is a shadow dark?",
  "display_question": "Why is a shadow dark?",
  "save_to_history": true
}
```

The backend must derive the canonical username from the authenticated profile as it does today.

#### Spoken-answer endpoint

Add a dedicated authenticated endpoint in a future Phase 1 implementation step:

```http
POST /api/likha/speak-doubt-answer
```

Do not accept arbitrary free-form `answer_text` as trusted input.

Preferred request:

```json
{
  "history_id": "answer record identifier",
  "language": "en-IN",
  "reply_style": "full"
}
```

Alternative for answers that are not saved:

```json
{
  "answer_token": "short-lived server-signed token",
  "language": "en-IN",
  "reply_style": "full"
}
```

The endpoint must:

1. Authenticate the caller.
2. Load and verify answer ownership using `history_id` or a server-issued token.
3. Derive `spoken_text` server-side from the saved answer.
4. Apply an answer-length ceiling.
5. Clean markdown, math delimiters, URLs, citation-only content, and visual-only sections using existing TTS cleanup.
6. Choose Neerja or Swara based on selected language/subject.
7. Generate neural MP3 when available.
8. Return an audio URL or a graceful fallback indicator.

Example response:

```json
{
  "success": true,
  "audio_url": "https://…",
  "voice": "en-IN-NeerjaNeural",
  "spoken_text": "A shadow is dark because…",
  "cached": false
}
```

### Why a dedicated endpoint is required

The existing endpoint:

```http
GET /api/lesson/chapter-narration
```

is designed for stable, pre-approved chapter milestones and wrap-ups. It must remain limited to those inputs. Allowing arbitrary text there would:

- turn a lesson endpoint into a general TTS service;
- make authorization difficult;
- make caching/privacy behavior unsafe;
- make abuse and cost control harder;
- risk speaking text that does not match the displayed academic answer.

The new endpoint must only speak an answer the server already knows and has authorized for that student.

---

## Answer and audio caching policy

| Answer origin | Audio policy |
|---|---|
| DKB response | Shared cache keyed by DKB record ID, language, voice, and reply style |
| Stable textbook/LKB response | Cache by approved answer/content hash, language, voice, and reply style |
| Live personalized LLM answer | Per-user short-lived cache only; never store publicly as a shared object |
| Browser fallback | No backend audio persistence |

Any cached shared object must not include a student name, private profile information, or personalized mentor-memory content.

---

## Access, safety, privacy, and cost controls

### Access

- Reuse existing `POST /api/doubt/answer` authorization.
- Expose initial feature to authenticated students only.
- Preserve free-tier DKB-only behavior.
- Preserve paid-tier limits.
- Do not implement a client-side entitlement bypass.

### Safety

- The answer route stays responsible for academic guardrails.
- Voice output reads the already-generated answer; it does not produce new unsupported claims.
- Include the source type in the UI before/alongside audio.
- Ensure non-academic redirect responses can be read aloud only if that is desired; otherwise, disable speech for these redirects.
- Block spoken answer generation for `ERROR` responses.

### Privacy

- Phase 1 collects no microphone audio.
- Phase 2 browser speech recognition may process audio through the browser/OS provider; disclose this in the UI before recording.
- Phase 3 must not retain raw recordings by default.
- Never log raw audio in product analytics.
- Do not expose a student’s personalized answer as a public shared audio asset.

### Cost controls

- DKB remains the first answer source.
- Apply explicit maximum TTS character counts.
- Cache safe, stable answers.
- Add separate usage events for:
  - `likha_voice_answer_tts`;
  - `likha_voice_transcription` (Phase 3 only).
- Rate-limit dynamic speech generation separately from `/api/doubt/answer`.
- Use browser Speech Synthesis as a fallback when neural synthesis is unavailable.

---

## Implementation sequence

### Step 0 — local development safety

Before product changes:

1. Fix terminal `rtk` shell startup error.
2. Verify repository worktree state.
3. Create a local branch:

```text
feature/likha-voice-tutor
```

4. Do not push, merge, or modify `main`.
5. Maintain a short implementation journal in this document or a dedicated development note.

### Step 1 — navigation and route

1. Locate student sidebar navigation configuration.
2. Add `likhaVoiceTutor` page key.
3. Add `Likha Voice Tutor` sidebar item for students only.
4. Register `LikhaVoiceTutorPage` in `App.jsx`.
5. Ensure page does not appear for non-student roles.

**Acceptance criteria**

- Student sees the sidebar link.
- Clicking it renders a non-blank page.
- Existing routes and sidebar tests continue to pass.
- Parent, teacher, principal, sales, and admin users do not see the entry.

### Step 2 — typed answer experience

1. Implement the page with syllabus/default-selection utilities already used in `DoubtPage.jsx`.
2. Add contextual selectors.
3. Reuse existing answer API client behavior.
4. Render:
   - answer;
   - source type;
   - visuals;
   - errors;
   - suggestions;
   - loading state.
5. Add keyboard-safe form submission and appropriate `aria-live` status.

**Acceptance criteria**

- A valid typed question calls `/api/doubt/answer` with the expected context.
- The answer page exposes its source type.
- API failure remains recoverable.
- Existing doubt entitlements and messages are respected.

### Step 3 — spoken answer playback

1. Add the dedicated secured answer-speech backend route.
2. Add frontend API client call.
3. Build `LikhaVoicePlayer` using existing avatar assets and lifecycle patterns.
4. Add:
   - Listen;
   - Pause;
   - Resume;
   - Stop;
   - Replay;
   - speed control;
   - browser TTS fallback.
5. Ensure the audio lifecycle is cancelled on question replacement and unmount.

**Acceptance criteria**

- A displayed answer is spoken only after an explicit learner action.
- Audio request cannot be used to synthesize arbitrary client-provided text.
- Spoken text comes from the approved answer record.
- Playback controls work.
- Failure falls back or fails gracefully without breaking the written answer.

### Step 4 — Phase 2 speech recognition

1. Add browser capability detection.
2. Add explicit microphone button.
3. Support English and Hindi recognition language settings.
4. Populate the editable question input with the transcript.
5. Add denied/unsupported/error states.
6. Do not submit automatically.

**Acceptance criteria**

- Microphone access is requested only after a deliberate button press.
- Student can edit transcript before submit.
- Typed question entry always remains usable.
- Unsupported browsers receive a clear message and typed fallback.

### Step 5 — test and review

1. Add unit/component tests.
2. Run targeted tests.
3. Run existing avatar and sidebar regression tests.
4. Run lint/build tests as appropriate.
5. Manually review:
   - mobile layout;
   - keyboard navigation;
   - dark mode, if supported;
   - English/Hindi display;
   - long answers;
   - DKB answer;
   - textbook answer;
   - free-tier DKB miss;
   - quota reached;
   - neural audio failure;
   - unmount/navigation during playback.
6. Share screenshots/test results before any push or merge decision.

---

## Test plan

### Frontend

Suggested test file:

```text
frontend/src/tests/LikhaVoiceTutorPage.test.jsx
```

Test cases:

1. Student sidebar navigation exposes Likha Voice Tutor.
2. The page loads default grade/context safely.
3. Empty question cannot be submitted.
4. Typed question calls answer API with context.
5. Loading state is announced.
6. DKB answer shows the knowledge-base source label.
7. Textbook answer shows textbook grounding and visuals.
8. Error response is recoverable.
9. Listen action requests authorized audio only after answer exists.
10. Play/pause/resume/stop/replay work.
11. Browser TTS fallback activates when neural audio fails.
12. New question stops current audio.
13. Unmount stops current audio.
14. Non-student role does not see the sidebar link.

### Backend

Suggested tests:

```text
backend/tests/test_likha_voice_tutor.py
```

Test cases:

1. Unauthenticated speech request is rejected.
2. Request cannot speak arbitrary client-submitted text.
3. Student may only speak own stored answer.
4. Student may not use another student's `history_id`.
5. Unsupported language is rejected or normalized.
6. Overlength spoken text is shortened/rejected predictably.
7. DKB answer uses cache-safe audio key.
8. Personalized/live LLM response is not placed in shared public cache.
9. TTS provider failure returns a safe response.
10. Existing answer endpoint behavior remains unchanged.

---

## Metrics for a local pilot

Track aggregate events without raw audio:

| Event | Purpose |
|---|---|
| `likha_voice_tutor_opened` | Page discovery |
| `likha_voice_question_submitted` | Intent |
| `likha_voice_answer_received` | Answer success |
| `likha_voice_listen_started` | Audio adoption |
| `likha_voice_listen_completed` | Listen completion |
| `likha_voice_listen_stopped` | Friction or intentional control |
| `likha_voice_tts_fallback_used` | Neural voice reliability |
| `likha_voice_transcript_confirmed` | Phase 2 quality |
| `likha_voice_follow_up_clicked` | Learning depth |
| `likha_voice_error_shown` | Reliability monitoring |

Success indicators for Phase 1:

- Students can reliably submit and read answers.
- Spoken-answer initiation works without accidental playback.
- Audio completion rate is meaningfully above accidental starts.
- No increase in entitlement, quota, or privacy issues.
- Written-answer experience remains as usable as the existing Doubt page.

---

## Explicit non-goals

The first release will not:

- create an always-on voice assistant;
- listen continuously in the background;
- answer non-academic general chat;
- replace the existing Doubt Solver;
- bypass textbook grounding, DKB matching, limits, or feature gates;
- give assistance during timed mock tests;
- store voice recordings by default;
- expose generalized TTS for arbitrary user text;
- launch directly to main or production before local validation and review.

---

## Decisions needed before implementation

1. Should the initial sidebar page be student-only, or also visible to parent accounts acting on behalf of a child?
   - **Recommendation:** student-only in Phase 1.

2. Should Phase 1 include neural backend audio immediately, or ship browser speech fallback first?
   - **Recommendation:** implement the secure backend endpoint and fallback together, but keep the scope limited to spoken answer playback.

3. Should English/Hindi selection follow subject language or be explicitly selectable?
   - **Recommendation:** infer language from subject initially, with a visible override only if testing shows frequent mixed-language use.

4. Should the page use existing doubt history or retain its own Voice Tutor session history?
   - **Recommendation:** reuse existing doubt history first; do not create a duplicate history system.

5. What is the desired maximum spoken response length?
   - **Recommendation:** 1,200–1,800 characters for a full explanation, plus a concise mode around 500–700 characters.

---

## Recommended next action

Resolve the local terminal startup issue, create the local-only branch `feature/likha-voice-tutor`, then begin with:

1. sidebar route and a student-only page shell;
2. typed question flow using the existing secured doubt API;
3. answer display and source metadata;
4. secure read-aloud playback;
5. tests and local review.

No remote push or merge should occur until the local feature experience has been reviewed and approved.
