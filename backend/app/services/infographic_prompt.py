"""
Chapter Infographic Prompt Builder
==================================
Single source of the wording used to ask GPT-5.5 for a chapter revision poster
("Chapter at a Glance"). `prepare_gpt55_infographic_prompts.py` just calls
build_infographic_prompt() with grade, subject, chapter and the chapter's
already-authored lesson text — nothing grade- or subject-specific is hard-coded
in that script, mirroring how lesson_plan_pedagogy.py serves the lesson-plan
workflow.

See docs/CHAPTER_INFOGRAPHIC_FEATURE.md for the surrounding workflow.

The HARD RULES section is not boilerplate. Every rule there corresponds to a
defect observed in the first batch of generated posters (Grade 12 Biology,
2026-08-17): an off-topic "C3 vs C4 Plants" panel in a biotechnology poster, a
meta "Why Exemplar Questions are Harder?" panel that talked about exams rather
than the subject, and garbled lettering in DNA sequence diagrams. Dense
technical text is exactly where image generation fails, so the prompt pushes
toward fewer, larger, correctly-spelled labels.
"""

from __future__ import annotations

# Grounding text is truncated so a very long chapter cannot push the design
# instructions out of the model's effective attention window.
MAX_GROUNDING_CHARS = 14000


def grade_number(grade: str) -> int:
    """Extract the numeric grade, defaulting to 8 when unparseable."""
    digits = "".join(ch for ch in (grade or "") if ch.isdigit())
    try:
        return int(digits)
    except ValueError:
        return 8


def grade_band(grade: str) -> str:
    """Bucket a grade into the three design/reading-level bands."""
    n = grade_number(grade)
    if n <= 8:
        return "5-8"
    if n <= 10:
        return "9-10"
    return "11-12"


# Per-band design guidance. The bands differ in density, vocabulary and what a
# student is actually revising for — a Grade 5 poster that reads like a Grade 12
# one is useless, and vice versa.
BAND_GUIDANCE = {
    "5-8": {
        "audience": "a 10-14 year old CBSE student revising before a school test",
        "panels": "4 to 6",
        "density": (
            "- Short sentences, everyday words. Explain a term the first time it appears.\n"
            "- Lead with pictures: each panel should carry a simple, clearly-drawn diagram,\n"
            "  icon or labelled sketch, with text supporting the picture rather than the reverse.\n"
            "- At most 4 bullet points per panel, at most about 12 words per bullet.\n"
            "- Warm, encouraging tone. Bright, high-contrast colours."
        ),
        "extras": (
            "- Include a short 'Words to know' strip with 4-6 terms in plain language.\n"
            "- Include a 'Remember this' strip with 3-5 facts a student is most likely to forget."
        ),
    },
    "9-10": {
        "audience": "a 14-16 year old CBSE student revising for board-pattern exams",
        "panels": "5 to 7",
        "density": (
            "- Precise CBSE terminology, defined where it first appears.\n"
            "- Balance diagrams and text: every process or mechanism gets a labelled visual.\n"
            "- At most 5 bullet points per panel, at most about 16 words per bullet.\n"
            "- Include the formulae, definitions and labelled diagrams most often asked in exams."
        ),
        "extras": (
            "- Include a 'Key terms' strip with 5-8 term/definition pairs.\n"
            "- Include a 'Common mistakes' strip with 4-6 errors students actually make\n"
            "  in this chapter, phrased as the correction."
        ),
    },
    "11-12": {
        "audience": "a 16-18 year old CBSE student revising for board and competitive exams",
        "panels": "6 to 8",
        "density": (
            "- Full technical vocabulary; assume the chapter has been studied once already.\n"
            "- Include exact conditions, units, formulae, enzyme/reagent names and numeric\n"
            "  values where the source states them. Do not round or approximate.\n"
            "- At most 5 bullet points per panel, at most about 18 words per bullet.\n"
            "- Where the chapter describes a multi-step process, show it as a numbered strip."
        ),
        "extras": (
            "- Include a 'Key terms' strip with 6-10 term/definition pairs.\n"
            "- Include an 'Important points to remember' strip with 5-8 high-yield facts,\n"
            "  distinctions or exam traps drawn from the chapter."
        ),
    },
}


def build_infographic_prompt(
    *,
    grade: str,
    subject: str,
    chapter: str,
    chapter_lesson_text: str,
) -> str:
    """Assemble the full GPT-5.5 image-generation prompt for one chapter."""
    band = grade_band(grade)
    guidance = BAND_GUIDANCE[band]

    grounding = (chapter_lesson_text or "").strip()
    truncated = len(grounding) > MAX_GROUNDING_CHARS
    if truncated:
        grounding = grounding[:MAX_GROUNDING_CHARS].rsplit("\n", 1)[0]

    truncation_note = (
        "\n[Content truncated for length. Summarise what is present; do not invent "
        "the remainder.]\n" if truncated else ""
    )

    return f"""\
You are an expert CBSE textbook illustrator. Produce ONE revision infographic
image — a "Chapter at a Glance" poster — for the chapter below.

GRADE:   {grade}
SUBJECT: {subject}
CHAPTER: {chapter}
READER:  {guidance['audience']}

================================================================================
HARD RULES — these come from real defects in earlier generated posters
================================================================================
1. GROUNDING. Every panel, label, figure and fact must come from CHAPTER_CONTENT
   below. Do not add a topic, example, formula or comparison that is not in it.
   A previous poster for a biotechnology chapter included a "C3 vs C4 Plants"
   table that belonged to a completely different chapter. That is the single
   worst failure mode — it teaches the student something irrelevant.

2. NO META PANELS. The poster is about the subject, never about studying,
   exams-as-a-topic, or the poster itself. A previous version wasted a panel on
   "Why Exemplar Questions are Harder" — do not do this.

3. LETTERING MUST BE CORRECT AND LEGIBLE. Every word, symbol, formula and
   sequence must be spelled correctly and rendered cleanly. Earlier posters
   produced garbled strings in sequence diagrams. Therefore:
   - Prefer FEWER, LARGER text labels over many small ones.
   - Do not render long strings of letters, digits or symbols inside a small
     diagram. If a sequence, formula or equation cannot be drawn large and
     perfectly legible, present it as a clean single line of text instead.
   - Check every label against CHAPTER_CONTENT before finalising.

4. NO INVENTED CITATIONS. Do not print NCERT page numbers, exercise numbers,
   figure numbers or "as per NCERT" claims unless they appear in CHAPTER_CONTENT.

5. SELF-CONTAINED. The poster must make sense on its own, with no reference to
   "the lesson above", "step 3", or anything outside the image.

================================================================================
LAYOUT SPEC
================================================================================
- Portrait orientation, aspect ratio between 4:5 and 3:4. It is displayed on
  phones, so avoid extreme height.
- Generous margins and clear separation between panels. White or very light
  background. Strong colour only for headers, accents and diagrams.
- Structure, top to bottom:
  a) Title bar: the chapter name, large and unambiguous.
  b) A one or two sentence definition/overview strip directly beneath it.
  c) {guidance['panels']} numbered concept panels, each with a short heading,
     a labelled diagram or icon, and its bullet points.
  d) If the chapter contains a sequential process, one full-width numbered
     strip showing that process end to end.
  e) The two closing strips described under CONTENT DEPTH.
- Every panel must be reachable in one glance: no panel should require the
  reader to zoom past the point where neighbouring panels are unreadable.

================================================================================
CONTENT DEPTH — tuned for {grade}
================================================================================
{guidance['density']}
{guidance['extras']}

================================================================================
CHAPTER_CONTENT — the ONLY permitted source of facts
================================================================================
{grounding}
{truncation_note}
================================================================================
BEFORE YOU FINISH — self-check
================================================================================
- Does every panel trace back to CHAPTER_CONTENT? Remove anything that does not.
- Is any lettering misspelled, garbled, cut off or too small to read?
- Is there a meta/study-skills panel? Remove it.
- Would this poster still be correct if a subject teacher marked it?

================================================================================
ALSO RETURN, AS PLAIN TEXT AFTER THE IMAGE
================================================================================
ALT: <one sentence describing the poster for a screen-reader user; state the
     chapter and the main areas covered; maximum 300 characters>
CAPTION: <one line shown beneath the poster in the app; maximum 300 characters>
"""
