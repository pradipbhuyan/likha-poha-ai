"""
Regression coverage for _is_valid_question's template-detection defenses in
scripts/ingest_gpt55_subjective_question_bank_output.py — previously
completely untested. Added after a live incident: a Grade 12 Biology batch
(97% of 260 questions, all 13 chapters) reused a handful of fixed sentence
skeletons ("Explain X and state its key features, mechanism or
significance.") with only the topic noun swapped in, and slipped past the
two existing template patterns (which were tuned to an earlier, differently
-worded incident) because the wording didn't match.
"""

import json

from scripts.ingest_gpt55_subjective_question_bank_output import (
    _is_valid_question,
    detect_cross_chapter_templating,
)


def _question(**overrides):
    base = {
        "question": "Why does the pistil reject incompatible pollen during self-incompatibility?",
        "marks": 3,
        "model_answer": "Self-incompatibility genes prevent the pollen tube from growing normally in the style when pollen is genetically similar to the pistil, blocking fertilisation.",
        "difficulty": "Medium",
    }
    base.update(overrides)
    return base


class TestSentenceSkeletonPattern:
    """The pattern added after the Grade 12 Biology templating incident."""

    def test_rejects_key_features_mechanism_significance_skeleton(self):
        ok, reason = _is_valid_question(_question(
            question="Explain pollen-pistil interaction and state its key features, mechanism or significance."
        ))
        assert ok is False
        assert "sentence skeleton" in reason

    def test_rejects_biological_relationship_skeleton(self):
        ok, reason = _is_valid_question(_question(
            question="Explain apomixis and polyembryony in detail, showing the biological relationship between them."
        ))
        assert ok is False
        assert "sentence skeleton" in reason

    def test_rejects_distinguish_linked_ideas_skeleton(self):
        ok, reason = _is_valid_question(_question(
            question="Explain chasmogamous and cleistogamous flowers and distinguish the linked ideas where relevant."
        ))
        assert ok is False

    def test_rejects_mechanism_evidence_examples_skeleton(self):
        ok, reason = _is_valid_question(_question(
            question="Give a detailed account of emasculation and bagging, including the mechanism, evidence, examples or consequences stated in the chapter."
        ))
        assert ok is False

    def test_rejects_major_points_relating_to_skeleton(self):
        # Second confirmed incident: a Grade 12 Business Studies batch used
        # this exact scaffold for 5/20 questions in every one of 11 chapters.
        ok, reason = _is_valid_question(_question(
            question="Explain the major points relating to coordination."
        ))
        assert ok is False

    def test_rejects_literary_analysis_skeletons(self):
        # Third confirmed incident: a Grade 12 English batch reused these
        # four literary-analysis scaffolds across all 19 prose/poetry
        # chapters, 58% of the batch, with just the topic swapped in.
        bad_questions = [
            "What role does the treatment of Bare feet play in the development of the scene?",
            "Why are the details associated with Pigeons significant in this episode?",
            "Compare the treatment of unusual silence and retrospective narration in The Last Lesson. What larger idea emerges when they are read together?",
            "Examine the relationship between migration and bare feet. Why is that relationship important to the meaning of Lost Spring?",
            # Three more variants found on a second read of the same batch —
            # the first four patterns alone still let ~30% of the remaining
            # questions through undetected.
            "What does the chapter reveal through the treatment of Initial attitude?",
            "How does the treatment of Writing copies contribute to the text’s meaning?",
            "What becomes clearer to the reader through the treatment of Past perfect?",
        ]
        for q_text in bad_questions:
            ok, reason = _is_valid_question(_question(question=q_text))
            assert ok is False, f"expected rejection for: {q_text!r}"
        assert "sentence skeleton" in reason

    def test_accepts_genuine_varied_cbse_style_question(self):
        ok, reason = _is_valid_question(_question(
            question="A farmer noticed only self-pollinated flowers on a plant failed to set seed. Explain this using the chapter's account of self-incompatibility."
        ))
        assert ok is True, reason

    def test_accepts_question_using_explain_as_a_verb_without_the_banned_scaffold(self):
        # "Explain" itself is fine and common in real CBSE papers — only the
        # surrounding reused sentence scaffold is the problem.
        ok, reason = _is_valid_question(_question(
            question="Explain why triple fusion is unique to flowering plants, with reference to the chapter's description of the process."
        ))
        assert ok is True, reason

    def test_rejects_geography_tail_matched_skeletons(self):
        # Fourth confirmed incident: a Grade 12 Geography batch (33% of 340
        # questions, all 17 chapters) reused these tails — matched on the
        # TAIL rather than the opener, since "Give a brief account of X" and
        # "What is the significance of X" are legitimate CBSE openers on
        # their own; only the fixed, repeated tail marks these as templated.
        bad_questions = [
            "Give a brief account of physical environment using two specific details from the text.",
            "Give a brief account of stage one of demographic transition, including the relevant definition, pattern or example.",
            "What is the significance of Griffith Taylor's neodeterminism in Human Geography: Nature and Scope? Support your answer with two facts.",
            "State two features, examples or implications associated with cultural landscape.",
            "What does the text state about crude birth rate? Give two relevant details.",
        ]
        for q_text in bad_questions:
            ok, reason = _is_valid_question(_question(question=q_text))
            assert ok is False, f"expected rejection for: {q_text!r}"

    def test_accepts_a_generic_opener_without_the_templated_tail(self):
        # The opener alone ("Give a brief account of...") must stay legal —
        # only the specific reused tail should trigger rejection.
        ok, reason = _is_valid_question(_question(
            question="Give a brief account of how the Green Revolution changed cropping patterns in Punjab, citing the two examples discussed in the chapter."
        ))
        assert ok is True, reason


class TestExistingTemplatePatterns:
    """Basic smoke coverage for the two pre-existing patterns (previously untested)."""

    def test_rejects_lesson_scaffolding_meta_reference(self):
        ok, reason = _is_valid_question(_question(
            question="Explain the chapter point about Faithfulness and connect it with another idea from the exam-style activities."
        ))
        assert ok is False

    def test_rejects_glossary_template_phrasing(self):
        ok, reason = _is_valid_question(_question(
            question="What does mitosis mean, and how is it used in this topic?"
        ))
        assert ok is False


class TestBasicSchemaValidation:
    def test_rejects_missing_question_text(self):
        ok, reason = _is_valid_question(_question(question=""))
        assert ok is False
        assert "question text" in reason

    def test_rejects_non_positive_marks(self):
        ok, reason = _is_valid_question(_question(marks=0))
        assert ok is False
        assert "marks" in reason

    def test_rejects_invalid_difficulty(self):
        ok, reason = _is_valid_question(_question(difficulty="Impossible"))
        assert ok is False
        assert "difficulty" in reason


def _write_chapter_file(tmp_path, filename, chapter, openers):
    """Write a minimal GPT-5.5-shaped JSON file with one question per opener."""
    questions = [
        {
            "question": f"{opener} in {chapter}?",
            "marks": 3,
            "model_answer": "A real, specific, grounded explanation of the topic in question.",
            "difficulty": "Medium",
        }
        for opener in openers
    ]
    path = tmp_path / filename
    path.write_text(json.dumps({
        "manifest": {"grade": "Grade 12", "subject": "Test Subject", "chapter": chapter},
        "questions": questions,
    }))
    return path


class TestCrossChapterTemplatingDetector:
    """
    Regression coverage for the second, more subtle incident: a re-authored
    Grade 12 Biology batch used no single repeated phrase within a chapter
    (so _SENTENCE_SKELETON_PATTERN found nothing), but a fixed roster of ~11
    question openers each appeared in all 13 chapters, once each — the whole
    paper was a reused template with only the topic swapped per slot.
    """

    def test_flags_openers_reused_across_almost_every_chapter(self, tmp_path):
        shared_openers = [
            "State two important points about",
            "Give the main defining features of",
            "Identify the main mechanism of",
        ]
        paths = [
            _write_chapter_file(tmp_path, f"ch{i}.json", f"Chapter {i}", shared_openers)
            for i in range(1, 6)  # 5 chapters, same 3 openers in every one
        ]

        flagged = detect_cross_chapter_templating(paths)

        assert "state two important points" in flagged
        assert flagged["state two important points"] == 5

    def test_does_not_flag_genuinely_varied_batches(self, tmp_path):
        paths = [
            _write_chapter_file(tmp_path, "ch1.json", "Chapter 1", [
                "Why does the pistil reject", "Compare fixed and fluctuating capital",
            ]),
            _write_chapter_file(tmp_path, "ch2.json", "Chapter 2", [
                "State the statutory rate of", "Distinguish a defect in goods",
            ]),
            _write_chapter_file(tmp_path, "ch3.json", "Chapter 3", [
                "A farmer noticed that seeds", "Justify the statement that management",
            ]),
        ]

        flagged = detect_cross_chapter_templating(paths)

        assert flagged == {}

    def test_skips_the_check_for_small_batches(self, tmp_path):
        # Fewer than 3 chapters isn't enough signal — must never false-positive
        # on a single-chapter or two-chapter ingest.
        shared_openers = ["Explain the same thing every time"]
        paths = [
            _write_chapter_file(tmp_path, "ch1.json", "Chapter 1", shared_openers),
            _write_chapter_file(tmp_path, "ch2.json", "Chapter 2", shared_openers),
        ]

        flagged = detect_cross_chapter_templating(paths)

        assert flagged == {}

    def test_a_naturally_occurring_repeated_opener_below_threshold_is_not_flagged(self, tmp_path):
        # "Distinguish between" is a normal, common CBSE opener — reused in
        # only 1 of 5 chapters here should not trip the detector.
        paths = [
            _write_chapter_file(tmp_path, "ch1.json", "Chapter 1", ["Distinguish between two things"]),
            _write_chapter_file(tmp_path, "ch2.json", "Chapter 2", ["Why does this happen"]),
            _write_chapter_file(tmp_path, "ch3.json", "Chapter 3", ["What is the reason"]),
            _write_chapter_file(tmp_path, "ch4.json", "Chapter 4", ["How does this differ"]),
            _write_chapter_file(tmp_path, "ch5.json", "Chapter 5", ["Give an example of"]),
        ]

        flagged = detect_cross_chapter_templating(paths)

        assert flagged == {}
