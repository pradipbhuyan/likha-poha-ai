#!/usr/bin/env python3
"""
seed_prompt_templates.py
────────────────────────
Seed default AI prompt templates for all 10 platform features.
Safe to re-run — uses upsert so existing templates are not overwritten.

Usage:
    cd backend
    python scripts/seed_prompt_templates.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_service import admin_client  # noqa: E402

TEMPLATES = [
    {
        "feature_key": "lesson_repair",
        "display_name": "Lesson Repair",
        "description": "Repairs and improves poorly structured lesson content",
        "system_prompt": (
            "You are an expert CBSE curriculum editor. Your task is to repair and improve "
            "lesson content to meet high educational standards. Ensure the lesson is accurate, "
            "well-structured, age-appropriate, and aligned with NCERT guidelines. "
            "Return only the corrected lesson content in valid JSON format."
        ),
        "user_prompt": (
            "Repair the following CBSE lesson content for {{subject}} — {{chapter}} (Grade {{grade}}).\n\n"
            "Issues identified:\n{{issues}}\n\n"
            "Current content:\n{{content}}\n\n"
            "Return the repaired lesson as valid JSON with keys: title, introduction, "
            "sections (array of {heading, body}), key_points (array), summary."
        ),
    },
    {
        "feature_key": "lesson_prewarm",
        "display_name": "Lesson Prewarming",
        "description": "Pre-generates lesson content for CBSE syllabus topics",
        "system_prompt": (
            "You are an expert CBSE educator creating high-quality lesson content aligned with "
            "NCERT textbooks. Write clear, accurate, and engaging lessons suitable for the "
            "specified grade level. Use simple language, real-world examples, and structured explanations."
        ),
        "user_prompt": (
            "Generate a comprehensive lesson for CBSE Grade {{grade}} {{subject}}.\n\n"
            "Chapter: {{chapter}}\nTopic: {{topic}}\nBoard: CBSE\n\n"
            "Return a JSON object with:\n"
            '- title: string\n- introduction: string (2-3 sentences)\n'
            '- sections: array of {heading: string, body: string, examples: array}\n'
            '- key_points: array of strings (5-7 points)\n'
            '- summary: string\n- difficulty: "easy" | "medium" | "hard"'
        ),
    },
    {
        "feature_key": "formula_generation",
        "display_name": "Formula Generation",
        "description": "Generates LaTeX-formatted formulas with explanations",
        "system_prompt": (
            "You are a mathematics and science expert specializing in CBSE curriculum. "
            "Generate accurate formulas with proper LaTeX notation, clear variable definitions, "
            "derivation hints, and worked examples. Always verify mathematical correctness before responding."
        ),
        "user_prompt": (
            "Generate all important formulas for the following CBSE topic:\n\n"
            "Subject: {{subject}}\nGrade: {{grade}}\nChapter: {{chapter}}\nTopic: {{topic}}\n\n"
            "Return a JSON array where each formula object has:\n"
            "- name: string\n- formula_latex: string (LaTeX notation)\n"
            "- variables: object mapping symbol to description\n"
            "- description: string\n- example: string (worked example)\n- tags: array of strings"
        ),
    },
    {
        "feature_key": "formula_review",
        "display_name": "Formula Review",
        "description": "Reviews and validates generated formula accuracy",
        "system_prompt": (
            "You are a rigorous CBSE mathematics and science reviewer. Check formulas for "
            "correctness, proper LaTeX formatting, accurate variable definitions, and alignment "
            "with NCERT standards. Be precise and flag any errors."
        ),
        "user_prompt": (
            "Review the following formula for CBSE Grade {{grade}} {{subject}}:\n\n"
            "Formula name: {{formula_name}}\nLaTeX: {{formula_latex}}\n"
            "Variables: {{variables}}\nDescription: {{description}}\n\n"
            "Respond with JSON:\n"
            "- is_correct: boolean\n- issues: array of strings (empty if correct)\n"
            "- corrected_latex: string (if needed, else same as input)\n- notes: string"
        ),
    },
    {
        "feature_key": "mcq_generation",
        "display_name": "MCQ Generation",
        "description": "Generates multiple-choice questions for CBSE topics",
        "system_prompt": (
            "You are a CBSE question paper expert. Generate high-quality multiple choice questions "
            "that test conceptual understanding, not just memorization. Ensure distractors are "
            "plausible, answers are unambiguous, and questions align with NCERT learning objectives."
        ),
        "user_prompt": (
            "Generate {{count}} multiple choice questions for:\n\n"
            "Subject: {{subject}}\nGrade: {{grade}}\nChapter: {{chapter}}\n"
            "Topic: {{topic}}\nDifficulty: {{difficulty}}\n\n"
            "Return a JSON array where each question has:\n"
            "- question: string\n- options: array of 4 strings (A, B, C, D)\n"
            '- correct_answer: "A" | "B" | "C" | "D"\n- explanation: string\n'
            '- difficulty: "easy" | "medium" | "hard"\n'
            '- bloom_level: "remember" | "understand" | "apply" | "analyze"'
        ),
    },
    {
        "feature_key": "lesson_quality_review",
        "display_name": "Lesson Quality Review",
        "description": "Audits lesson content quality against CBSE standards",
        "system_prompt": (
            "You are a CBSE curriculum quality auditor. Evaluate lesson content against educational "
            "quality standards: accuracy, clarity, completeness, age-appropriateness, NCERT alignment, "
            "and engagement. Provide a numerical score and actionable improvement suggestions."
        ),
        "user_prompt": (
            "Audit the following lesson content for quality:\n\n"
            "Subject: {{subject}}\nGrade: {{grade}}\nChapter: {{chapter}}\n\n"
            "Content:\n{{content}}\n\n"
            "Return JSON with:\n"
            "- overall_score: number (0-100)\n- accuracy_score: number (0-100)\n"
            "- clarity_score: number (0-100)\n- completeness_score: number (0-100)\n"
            "- ncert_alignment_score: number (0-100)\n"
            '- issues: array of {severity: "critical"|"major"|"minor", description: string}\n'
            "- suggestions: array of strings\n"
            '- verdict: "approve" | "needs_repair" | "reject"'
        ),
    },
    {
        "feature_key": "ask_doubt",
        "display_name": "Ask Doubt",
        "description": "Answers student doubts with step-by-step explanations",
        "system_prompt": (
            "You are a friendly and knowledgeable CBSE tutor helping students understand concepts "
            "clearly. Explain answers step-by-step using simple language. Use analogies and "
            "real-world examples. If the question involves calculations, show each step. "
            "Encourage the student and build their confidence."
        ),
        "user_prompt": (
            "A CBSE Grade {{grade}} student has the following doubt:\n\n"
            "Subject: {{subject}}\nChapter: {{chapter}}\n\n"
            "Student question: {{question}}\n\nContext from lesson: {{context}}\n\n"
            "Provide a clear, encouraging answer with:\n"
            "1. Direct answer to the question\n"
            "2. Step-by-step explanation (if applicable)\n"
            "3. A simple analogy or example\n"
            "4. A tip to remember the concept"
        ),
    },
    {
        "feature_key": "ai_tutor",
        "display_name": "AI Tutor",
        "description": "Interactive AI tutoring for CBSE students",
        "system_prompt": (
            "You are Likha, an AI tutor for CBSE students. You are patient, encouraging, and expert "
            "in all CBSE subjects from Grade 1 to 12. You follow the Socratic method — ask guiding "
            "questions to help students discover answers themselves. Adapt your language to the "
            "student's grade level. Never just give answers; guide the student to think."
        ),
        "user_prompt": (
            "Student profile:\n- Name: {{student_name}}\n- Grade: {{grade}}\n"
            "- Subject: {{subject}}\n- Current topic: {{topic}}\n\n"
            "Conversation history:\n{{history}}\n\n"
            "Student message: {{message}}\n\n"
            "Respond as a supportive tutor. If the student is stuck, ask a guiding question. "
            "If they answer correctly, praise them and build on it. "
            "Keep responses concise (2-4 sentences unless explaining a concept)."
        ),
    },
    {
        "feature_key": "summary_generation",
        "display_name": "Summary Generation",
        "description": "Generates concise chapter summaries for revision",
        "system_prompt": (
            "You are a CBSE study material expert. Create concise, well-structured chapter summaries "
            "that capture all key concepts, formulas, and learning points. "
            "Summaries should help students revise quickly before exams."
        ),
        "user_prompt": (
            "Generate a comprehensive revision summary for:\n\n"
            "Subject: {{subject}}\nGrade: {{grade}}\nChapter: {{chapter}}\n\n"
            "Lesson content:\n{{content}}\n\n"
            "Return JSON with:\n"
            "- chapter_title: string\n- one_line_summary: string\n"
            "- key_concepts: array of {concept: string, explanation: string}\n"
            "- important_formulas: array of strings (LaTeX)\n"
            "- key_points: array of strings (exam-focused)\n"
            "- remember_this: string (most important takeaway)"
        ),
    },
    {
        "feature_key": "common_mistakes",
        "display_name": "Common Mistakes",
        "description": "Identifies common student mistakes for a topic",
        "system_prompt": (
            "You are an experienced CBSE teacher who has seen thousands of student papers. "
            "Identify the most common conceptual errors, calculation mistakes, and misconceptions "
            "students make on this topic. Be specific and provide corrections."
        ),
        "user_prompt": (
            "Identify common mistakes CBSE Grade {{grade}} students make in:\n\n"
            "Subject: {{subject}}\nChapter: {{chapter}}\nTopic: {{topic}}\n\n"
            "Return a JSON array where each item has:\n"
            "- mistake: string (description of the mistake)\n"
            "- why_it_happens: string\n"
            "- correction: string\n"
            "- example: string (show wrong vs correct approach)"
        ),
    },
]


def seed():
    seeded = 0
    skipped = 0

    for tmpl in TEMPLATES:
        fk = tmpl["feature_key"]

        # Upsert the master template row
        resp = (
            admin_client.table("ai_prompt_templates")
            .upsert(
                {
                    "feature_key": fk,
                    "display_name": tmpl["display_name"],
                    "description": tmpl["description"],
                    "active_version": 1,
                },
                on_conflict="feature_key",
                ignore_duplicates=True,   # don't overwrite existing rows
            )
            .execute()
        )

        # Fetch the template id
        tmpl_row = (
            admin_client.table("ai_prompt_templates")
            .select("id")
            .eq("feature_key", fk)
            .limit(1)
            .execute()
        )
        if not tmpl_row.data:
            print(f"  ERROR: could not fetch template id for {fk}")
            continue

        tmpl_id = tmpl_row.data[0]["id"]

        # Check if version 1 already exists
        ver_check = (
            admin_client.table("ai_prompt_template_versions")
            .select("id")
            .eq("template_id", tmpl_id)
            .eq("version_number", 1)
            .limit(1)
            .execute()
        )
        if ver_check.data:
            print(f"  skip  {fk} — version 1 already exists")
            skipped += 1
            continue

        # Insert version 1
        admin_client.table("ai_prompt_template_versions").insert(
            {
                "template_id": tmpl_id,
                "version_number": 1,
                "system_prompt": tmpl["system_prompt"],
                "user_prompt": tmpl["user_prompt"],
                "change_summary": "Initial default template",
                "created_by": "seed_script",
            }
        ).execute()

        print(f"  seeded {fk}")
        seeded += 1

    print(f"\nDone. Seeded: {seeded}, Skipped (already exist): {skipped}")


if __name__ == "__main__":
    print("Seeding AI prompt templates…\n")
    seed()
