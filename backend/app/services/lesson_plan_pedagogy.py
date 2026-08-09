"""
Lesson Plan Pedagogy Config
=============================================================================
Grade-band and subject-adaptive pedagogy rules for the GPT-5.5 lesson-plan
authoring prompt (see docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md and
scripts/prepare_gpt55_lesson_plan_prompts.py).

This module is the single place the prompt's pedagogy rules live, so the
same rules apply to every (grade, subject, chapter) instead of being
re-typed — or silently varying — per call site. Nothing here is specific to
any one grade, subject, or chapter: adding a new grade or subject means
adding a bucket below, not editing the prompt-building logic.
"""

from __future__ import annotations

import re

# A single static handout can't vary by a duration a teacher picks at
# request time (see docs/GPT55_LESSON_PLAN_AUTHORING_PROMPT.md), so every
# handout is authored for this fixed standard CBSE period.
DURATION_LABEL = "40-45 minutes"
DURATION_MIN_MINUTES = 40
DURATION_MAX_MINUTES = 45

_GRADE_NUMBER_RE = re.compile(r"(\d+)")


def grade_number(grade: str) -> int:
    """Extract the numeric grade from a string like 'Grade 9'. Defaults to 9
    (mid-secondary) if unparseable, which is the safest fallback pedagogy."""
    m = _GRADE_NUMBER_RE.search(grade or "")
    return int(m.group(1)) if m else 9


_GRADE_BANDS: tuple[tuple[tuple[int, int], str], ...] = (
    ((1, 2), "1-2"),
    ((3, 5), "3-5"),
    ((6, 8), "6-8"),
    ((9, 12), "9-12"),
)


def grade_band(grade: str) -> str:
    """Map a grade string to one of the four pedagogy bands used throughout
    this module: '1-2', '3-5', '6-8', '9-12'."""
    n = grade_number(grade)
    for (lo, hi), band in _GRADE_BANDS:
        if lo <= n <= hi:
            return band
    return "1-2" if n < 1 else "9-12"


# Maximum minutes of uninterrupted teacher explanation before it must be
# broken up with a question/response/example beat, per grade band. Used
# both in the prompt instructions and by lesson_plan_quality_checks.py.
GRADE_BAND_TEACHER_TALK_CAP_MINUTES: dict[str, int] = {
    "1-2": 6,
    "3-5": 14,
    "6-8": 18,
    "9-12": 22,
}

GRADE_BAND_PEDAGOGY: dict[str, str] = {
    "1-2": """\
- Grade band: 1-2 (early primary). Prioritize oral interaction, pictures, stories,
  movement, repetition, phonics/vocabulary, short teacher instructions, concrete
  examples, and drawing/matching/sorting/speaking activities.
- Avoid long explanations, abstract HOTS questions, long written tasks, heavy
  terminology, and too many objectives.
- Teacher-led explanation happens in very short chunks of about 3-5 minutes,
  each followed by a question, action, or response from students — never one
  continuous explanation.""",
    "3-5": """\
- Grade band: 3-5 (upper primary). Prioritize questioning, short explanations,
  guided discovery, pair activities, short reading/writing, examples from
  children's everyday lives, vocabulary in context, and simple reasoning.
- Break teacher explanation into short chunks rather than one long lecture.
  Avoid uninterrupted direct instruction of about 15 minutes or more unless the
  topic genuinely requires it — insert a question or quick check every few
  minutes instead.""",
    "6-8": """\
- Grade band: 6-8 (middle school). Use structured discussion, examples and
  counterexamples, problem solving, short collaborative tasks, application
  questions, conceptual reasoning, subject vocabulary, and evidence-based
  responses.
- Move students progressively from teacher-supported work toward independent
  application within the lesson.""",
    "9-12": """\
- Grade band: 9-12 (secondary/senior secondary). Use deeper conceptual
  explanation, exam-relevant understanding where appropriate, analytical
  questions, application, problem solving, interpretation, argument/evidence,
  case- or data-based tasks where relevant, and independent practice.
- Do not make the lesson childish merely because interactive activities are
  required — keep the reasoning level appropriate for this grade.""",
}


# Subject buckets. Keys are pedagogy categories; SUBJECT_KEYWORDS maps
# lowercase substrings found in the raw subject string to a category, so new
# subject names (e.g. a new elective) route correctly without code changes
# as long as a recognizable keyword is added here.
SUBJECT_KEYWORDS: tuple[tuple[str, str], ...] = (
    # Order matters: more specific phrases before generic ones.
    ("social science", "social_science"),
    ("political science", "social_science"),
    ("civics", "social_science"),
    ("history", "social_science"),
    ("geography", "social_science"),
    ("economics", "social_science"),
    ("mathematics", "mathematics"),
    ("maths", "mathematics"),
    ("math", "mathematics"),
    ("computer", "computer_science"),
    ("informatics", "computer_science"),
    ("information technology", "computer_science"),
    ("ict", "computer_science"),
    ("art", "skill_subject"),
    ("music", "skill_subject"),
    ("dance", "skill_subject"),
    ("physical education", "skill_subject"),
    (" pe", "skill_subject"),
    ("yoga", "skill_subject"),
    ("craft", "skill_subject"),
    ("work education", "skill_subject"),
    ("english", "languages"),
    ("hindi", "languages"),
    ("sanskrit", "languages"),
    ("language", "languages"),
    ("literature", "languages"),
    ("evs", "science"),
    ("environmental studies", "science"),
    ("science", "science"),
    ("physics", "science"),
    ("chemistry", "science"),
    ("biology", "science"),
)


def subject_category(subject: str) -> str:
    """Route a raw subject string (e.g. 'Social Science', 'Maths Standard',
    'EVS') to a pedagogy category. Falls back to a generic academic category
    for anything unrecognized rather than guessing wrong."""
    s = f" {(subject or '').strip().lower()} "
    for keyword, category in SUBJECT_KEYWORDS:
        if keyword in s:
            return category
    return "general_academic"


SUBJECT_PEDAGOGY: dict[str, str] = {
    "languages": """\
- Subject pedagogy: Languages. Prioritize a combination of listening, speaking,
  reading, comprehension, vocabulary, grammar in context, literary devices,
  writing, interpretation, and creative response.
- Connect any grammar practice to the chapter/text itself (its own sentences,
  characters, or events) rather than an unrelated worksheet.""",
    "mathematics": """\
- Subject pedagogy: Mathematics. Prioritize prerequisite recall, concept
  development, a worked example, guided practice, student practice, error
  analysis, application/problem solving, and a quick formative check.
- Do not spend excessive time on decorative activities that cut into
  mathematical practice time — practice on problems is the core activity.""",
    "science": """\
- Subject pedagogy: Science. Prioritize observation, prediction, concept
  development, diagrams/models, demonstrations or simple experiments when
  feasible, cause-and-effect reasoning, real-world application, and
  misconception correction.
- Clearly distinguish textbook facts from optional enrichment.""",
    "social_science": """\
- Subject pedagogy: Social Science. Prioritize timelines, maps, source
  interpretation, cause/effect, comparison, discussion, evidence, real-world
  connection, and perspective-taking when appropriate.
- Avoid turning the lesson into pure factual lecturing — build in discussion
  or interpretation, not just recitation of facts and dates.""",
    "computer_science": """\
- Subject pedagogy: Computer Science / ICT. Prioritize demonstration,
  step-by-step modelling, guided practice, a hands-on task, debugging/problem
  solving, and application.""",
    "skill_subject": """\
- Subject pedagogy: Art / Music / PE / skill subject. Prioritize
  demonstration, practice, performance, creation, reflection, and safety
  where relevant. Do not force an academic lecture structure onto a
  performance/practice-based subject.""",
    "general_academic": """\
- Subject pedagogy: use a structured concept-development pattern (explain a
  chunk, question, example, practice, apply) appropriate to this subject's
  own conventions rather than a generic lecture.""",
}


OBJECTIVE_RULES = """\
- Select 2-4 core learning objectives for this single period. Prefer depth
  over breadth: do not try to teach many independent ideas in one lesson. A
  4th objective is allowed only if this duration and topic genuinely support
  it. Keep any purely enrichment/HOTS outcome separate from the core
  objectives, not mixed into one crowded objective.
- Use observable, assessable verbs: identify, describe, explain, compare,
  classify, solve, demonstrate, create, interpret, justify, apply. Avoid vague
  verbs such as know, learn, understand everything about, or become familiar
  with.
- Do not include an objective the lesson does not have enough teaching or
  practice time to actually deliver and assess within this period."""


TIMING_RULES = f"""\
- The stage minutes in "## Lesson Plan (Step-by-Step)" must sum to a total
  between {DURATION_MIN_MINUTES} and {DURATION_MAX_MINUTES} minutes. Compute
  minutes for this specific lesson and topic — do not copy a fixed split from
  another lesson.
- Student Activity + Guided Practice time together should usually be at least
  as much as Direct Instruction time — this is a practice-heavy period, not a
  lecture.
- Do not assign more than one substantial student task inside a single short
  (5-10 minute) window; if a task cannot realistically finish in its
  allocated minutes, simplify it instead of cramming.
- Write Direct Instruction as a short interactive sequence — teacher
  explains/shows a small chunk, asks a question, students respond, teacher
  clarifies, then an example — broken into pieces rather than one
  uninterrupted lecture block. Include roughly 2-4 useful teacher questions
  across concept development, moving from recall to understanding to
  application/reasoning. Do not force a HOTS question into every lesson."""


DIFFERENTIATION_RULES = """\
- Never use the labels "slow learners", "weak students", or "dull students".
  Use "students needing additional support" and "students ready for
  extension" as the bullet labels in Differentiation Strategies.
- For students needing additional support: do NOT remove core learning
  objectives. Scaffold the SAME essential learning instead — word banks,
  sentence starters, multiple-choice support, visual cues, partially
  completed examples, fewer questions, pair support, teacher prompts,
  manipulatives, or simpler numbers/text.
- For students ready for extension: give a deeper task on the SAME
  concept/topic — explain why, create another example, a challenge problem,
  compare two cases, justify an answer, apply the idea to an unfamiliar
  situation. Never pivot to an unrelated animal, historical fact, scientific
  topic, or trivia just because it sounds advanced."""


ASSESSMENT_RULES = """\
- Create 2-4 quick formative checks that test the stated core learning
  objectives, not a minor enrichment side-topic. At least one check should
  cover each core objective wherever practical.
- The exit ticket must be about the core learning of this lesson, not an
  optional extension detail."""


MISCONCEPTION_RULES = """\
- Include 1-3 likely misconceptions only when genuinely meaningful for this
  topic — do not invent an obscure misconception just to fill the section."""


GROUNDING_RULES = """\
- Ground every activity, example, and reference strictly in
  CHAPTER_LESSON_TEXT. Never invent NCERT exercise/example numbers, page
  references, quotations, or facts that do not appear there. If exact
  curriculum-outcome alignment is not present in the source text, describe
  the link in neutral terms rather than asserting a verified alignment.
- Do not silently add unrelated general-knowledge facts as if they came from
  the chapter. Anything beyond the chapter's own content must be clearly
  framed as optional enrichment, not core teaching."""


VARIETY_RULES = """\
- Vary the concept-development and practice strategy to fit this topic and
  subject rather than repeating the same generic pattern every time. Choose
  from strategies such as: think-pair-share, guided discovery,
  read-predict-discuss, worked example, error spotting, concept sorting,
  mini investigation, role play, map analysis, source analysis, peer
  explanation, retrieval practice, quick-write, demonstration,
  problem-solving challenge, vocabulary game, diagram completion — pick
  whichever genuinely fits the topic, not at random."""


QUALITY_CONTROL_CHECKLIST = """\
Before writing the final answer, silently verify all of the following, and
revise the plan if any check fails:
1. Objectives: 2-4 core objectives, each achievable and assessable in this
   lesson, using measurable verbs.
2. Timing: stage minutes sum to the stated duration; teacher talk fits this
   grade band; student practice gets real time.
3. Activity: the main student activity is realistic in its allotted minutes
   and connects directly to a core objective — not several rushed activities.
4. Assessment: checks and the exit ticket test the stated core objectives,
   not a side topic.
5. Differentiation: core objectives are preserved (scaffolded, not deleted)
   for students needing support; the extension stays on the same topic.
6. Relevance: remove anything unrelated, decorative, or trivia that does not
   serve this chapter's content.
7. Grade fit: a real teacher of this grade would realistically use this plan
   as written.
8. Subject fit: the pedagogy matches this subject's own conventions, not a
   generic lecture template.
9. Grounding: no invented textbook facts, quotations, exercise numbers, or
   curriculum-alignment claims beyond what CHAPTER_LESSON_TEXT supports."""


def build_lesson_plan_prompt(grade: str, subject: str, chapter: str, chapter_lesson_text: str) -> str:
    """Assemble the full GPT-5.5 lesson-plan authoring prompt for one
    (grade, subject, chapter), adapting pedagogy automatically by grade band
    and subject category. This is the single source of the prompt — do not
    duplicate this template elsewhere."""
    grade_num = grade_number(grade)
    band = grade_band(grade)
    category = subject_category(subject)

    band_block = GRADE_BAND_PEDAGOGY[band]
    subject_block = SUBJECT_PEDAGOGY[category]
    talk_cap = GRADE_BAND_TEACHER_TALK_CAP_MINUTES[band]

    return f"""\
-----------------------------------------------------------------------------
SYSTEM ROLE

You are an experienced CBSE {subject} school teacher creating a classroom-
ready lesson plan handout for Grade {grade_num}, for one specific chapter,
for a CBSE AI tutoring platform used by teachers. The plan must feel like
something a good classroom teacher could realistically teach in one period —
not an exhaustive syllabus dump.

-----------------------------------------------------------------------------
GRADE-ADAPTIVE PEDAGOGY (apply automatically for this grade)

{band_block}
- Teacher-led uninterrupted explanation should not exceed about {talk_cap}
  minutes in any single stretch for this grade band without a question,
  response, or example breaking it up.

-----------------------------------------------------------------------------
SUBJECT-ADAPTIVE PEDAGOGY (apply automatically for this subject)

{subject_block}

-----------------------------------------------------------------------------
BINDING RULES (do not violate any of these)

DEPTH OVER BREADTH
{OBJECTIVE_RULES}

TIMING
{TIMING_RULES}

DIFFERENTIATION
{DIFFERENTIATION_RULES}

ASSESSMENT
{ASSESSMENT_RULES}

MISCONCEPTIONS
{MISCONCEPTION_RULES}

GROUNDING
{GROUNDING_RULES}

VARIETY
{VARIETY_RULES}

DURATION: Size the plan for a single standard {DURATION_LABEL} CBSE class
period. Do not ask for a duration — always produce one plan sized this way.

FULL COVERAGE: The plan must cover the chapter's main concepts as a whole,
not just one narrow sub-topic — while still respecting the objective-count
limit above (pick the 2-4 most important outcomes, not every fact in the
chapter).

PRACTICAL, NOT ACADEMIC: Write in the voice of an experienced classroom
teacher's planning notes — short, actionable bullet points, not textbook
prose.

LANGUAGE LEVEL: Write for a teacher instructing Grade {grade_num} students —
clear, classroom-appropriate CBSE phrasing matching this grade's reading and
cognitive level. Avoid unnecessarily academic language for younger grades and
avoid oversimplified, childish language for senior grades.

-----------------------------------------------------------------------------
USER TASK

GRADE: {grade}
SUBJECT: {subject}
CHAPTER: {chapter}

CHAPTER_LESSON_TEXT:
\"\"\"
{chapter_lesson_text}
\"\"\"

Produce ONE lesson plan in Markdown, using EXACTLY this section structure.
Do not use emoji anywhere in the output — the frontend renders each heading
below with its own icon, so headings must be PLAIN TEXT exactly as shown.
The minute values shown in each stage heading below are illustrative only —
compute your own minutes for this lesson following the TIMING rules above,
so they sum to a total between {DURATION_MIN_MINUTES} and {DURATION_MAX_MINUTES}:

## Lesson Overview
- **Topic:** {chapter}
- **Grade:** {grade}
- **Subject:** {subject}
- **Duration:** {DURATION_LABEL}
- **CBSE Unit:** (identify the unit/chapter from NCERT)

## Learning Objectives
By the end of this lesson, students will be able to:
1. (core objective — measurable verb)
2. (core objective — measurable verb)
3. (core objective — measurable verb; add a 4th line only if this lesson
   genuinely supports it)

## Prerequisites
Students should already know:
- (prerequisite 1)
- (prerequisite 2)

## Materials & Resources
- NCERT Textbook {grade} {subject}
- Blackboard / Whiteboard
- (additional realistic classroom materials specific to this topic; mark
  any technology/internet-dependent resource as OPTIONAL)

## Lesson Plan (Step-by-Step)

### Introduction & Hook (illustrative: 5 minutes)
- (attention-grabbing opening activity or question that activates prior
  knowledge and connects directly to the topic)

### Direct Instruction (illustrative: 15 minutes)
- (concept explanation broken into small chunks, each followed by a
  question/response/example — never one uninterrupted block)

### Guided Practice (illustrative: 10 minutes)
- (practice that directly rehearses the core objectives, with the teacher
  observing understanding and correcting errors)

### Student Activity (illustrative: 10 minutes)
- (ONE meaningful primary activity connected to a core objective, achievable
  in its allotted minutes, producing an observable student product)

### Assessment & Closure (illustrative: 5 minutes)
- Quick formative checks aligned to the core objectives
- A brief summary/retrieval of the main learning
- Exit ticket: (one question testing a core objective)

## Homework Assignment
- (short, objective-aligned practice possible with normal home resources —
  not an unrelated research task)

## Differentiation Strategies
- **For students needing additional support:** (scaffold the same core
  objectives — see DIFFERENTIATION rules above)
- **For students ready for extension:** (a deeper task on the same
  concept/topic — see DIFFERENTIATION rules above)

## Common Misconceptions to Address
1. (misconception 1, only if genuinely meaningful for this topic)
2. (misconception 2, only if genuinely meaningful for this topic)

## NCERT Alignment
- Chapter reference, and exercise/example numbers ONLY if they appear in
  CHAPTER_LESSON_TEXT — otherwise describe the curriculum connection in
  neutral terms instead of asserting a specific exercise/example number.

-----------------------------------------------------------------------------
QUALITY-CONTROL PASS

{QUALITY_CONTROL_CHECKLIST}

-----------------------------------------------------------------------------
OUTPUT FORMAT

Return ONLY a single valid JSON object (no markdown fences, no commentary
before or after) with exactly this shape:

{{
  "grade": "{grade}",
  "subject": "{subject}",
  "chapter": "{chapter}",
  "lesson_plan_markdown": "## Lesson Overview\\n- **Topic:** ...\\n(the full markdown plan, using \\n for line breaks, headings PLAIN TEXT with no emoji)"
}}

Return ONLY the JSON object described above. No markdown code fences, no
explanation text before or after it.
-----------------------------------------------------------------------------
"""
