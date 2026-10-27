# Likha Avatar Narration

## Scope

Likha narration is available for CBSE **Grades 5–8** in:

- English — `en-IN-NeerjaNeural`
- Hindi — `hi-IN-SwaraNeural`

The learner can choose one chapter path at a time:

1. Each stored chapter milestone
2. Wrap-up, when the chapter document includes a recap

Audio is requested only after the learner presses **Listen**. Scrolling does not change the selected narration path or interrupt active playback.

## First-visit welcome

On a learner's first visit to a grade/subject/chapter, the avatar presents **Tap to hear Likha's welcome**.

- English welcome uses the Neerja neural voice.
- Hindi welcome uses the Swara neural voice.
- Browser autoplay policies require the learner to tap the button.
- The button changes to **Getting Likha ready…** while the audio is loading.
- Completion is remembered in browser local storage per grade, subject, and chapter.

## Supabase audio caching

Narration MP3s are stored in the public Supabase Storage bucket configured by:

```env
LESSON_AUDIO_BUCKET=lesson-audio
```

The normal audio cache separates assets by:

- Grade
- Subject
- Chapter
- Chapter path / milestone
- Voice
- Rate

Supabase object paths also include the voice and rate. For example, Grade 5 Hindi
Swara audio is stored beneath:

```text
grade-5/hindi/<chapter>/hi-in-swaraneural/plus5percent/<milestone>.mp3
```

This prevents a Swara MP3 from overwriting another narrator's asset for the same
lesson path. A later request for the same path returns the cached Supabase URL
instead of generating audio again.

Shared welcome assets use fixed Storage paths:

- `likha/welcome/en-in-neerja.mp3`
- `likha/welcome/hi-in-swara.mp3`

When present, these shared files are returned immediately. If absent, the first successful welcome generation uploads the shared asset for subsequent instant playback.

## Corporate TLS / Zscaler setup

Edge TTS requires a trusted TLS certificate chain. On a network using TLS inspection, set `EDGE_TTS_CA_BUNDLE` to a PEM bundle containing the corporate root CA:

```env
EDGE_TTS_CA_BUNDLE=/absolute/path/to/corporate-ca-bundle.pem
```

Keep the PEM bundle out of Git. The backend `.gitignore` excludes local certificate bundles.

After changing this value, restart the backend. The TTS service keeps normal verified TLS behavior when the variable is unset.

## Prewarming narration

The admin-only API starts a background job for a specific grade and subject:

```http
POST /api/cache/prewarm/likha-narration
Content-Type: application/json

{
  "grade": "Grade 6",
  "subject": "English"
}
```

Requirements:

- Caller must be an authenticated admin.
- The backend must be restarted after deploying the endpoint.
- The job processes stored chapter documents only.
- It creates every milestone and Wrap-up MP3, skipping existing cached paths.
- English uses Neerja; Hindi uses Swara.

A local inspection/generation script is also available:

```bash
cd backend
python3 scripts/prewarm_likha_lesson_audio.py --grade "Grade 6" --subject English --dry-run
python3 scripts/prewarm_likha_lesson_audio.py --grade "Grade 6" --subject English

# Inspect Grade 5 Hindi narration scope without generating audio
python3 scripts/prewarm_likha_lesson_audio.py --grade "Grade 5" --subject Hindi --dry-run

# Generate/replace all Grade 5 Hindi Swara assets in their voice-specific paths
python3 scripts/prewarm_likha_lesson_audio.py --grade "Grade 5" --subject Hindi --force
```

Use the admin API for production prewarming because it runs within the configured backend process. The standalone script is useful for dry-run scope inspection.

To create or replace the two shared welcome assets:

```bash
cd backend
python3 scripts/prewarm_likha_welcome_audio.py
```

## Validation

Focused frontend coverage is in:

```bash
cd frontend
npm test -- --run src/tests/AvatarNarrator.test.jsx
```

It covers:

- Grades 5–8 English/Hindi visibility
- Neerja/Swara welcome requests
- Welcome loading feedback
- One-path-at-a-time selection
- Wrap-up selection
- Scroll-safe playback
- Browser fallback behavior
