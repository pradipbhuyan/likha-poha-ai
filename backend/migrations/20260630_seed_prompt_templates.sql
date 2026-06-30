-- ─────────────────────────────────────────────────────────────────────────────
-- Seed default AI Prompt Templates for all 10 platform features
-- Run in Supabase SQL Editor after 20260629_ai_studio.sql
-- Safe to re-run (ON CONFLICT DO NOTHING)
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
DECLARE
    v_lesson_repair_id          TEXT;
    v_lesson_prewarm_id         TEXT;
    v_formula_generation_id     TEXT;
    v_formula_review_id         TEXT;
    v_mcq_generation_id         TEXT;
    v_lesson_quality_review_id  TEXT;
    v_ask_doubt_id              TEXT;
    v_ai_tutor_id               TEXT;
    v_summary_generation_id     TEXT;
    v_common_mistakes_id        TEXT;
BEGIN

-- ── Insert master template rows ───────────────────────────────────────────────
INSERT INTO ai_prompt_templates (feature_key, display_name, description, active_version)
VALUES
    ('lesson_repair',         'Lesson Repair',          'Repairs and improves poorly structured lesson content', 1),
    ('lesson_prewarm',        'Lesson Prewarming',       'Pre-generates lesson content for CBSE syllabus topics', 1),
    ('formula_generation',    'Formula Generation',      'Generates LaTeX-formatted formulas with explanations', 1),
    ('formula_review',        'Formula Review',          'Reviews and validates generated formula accuracy', 1),
    ('mcq_generation',        'MCQ Generation',          'Generates multiple-choice questions for CBSE topics', 1),
    ('lesson_quality_review', 'Lesson Quality Review',   'Audits lesson content quality against CBSE standards', 1),
    ('ask_doubt',             'Ask Doubt',               'Answers student doubts with step-by-step explanations', 1),
    ('ai_tutor',              'AI Tutor',                'Interactive AI tutoring for CBSE students', 1),
    ('summary_generation',    'Summary Generation',      'Generates concise chapter summaries', 1),
    ('common_mistakes',       'Common Mistakes',         'Identifies common student mistakes for a topic', 1)
ON CONFLICT (feature_key) DO NOTHING;

-- ── Fetch IDs ─────────────────────────────────────────────────────────────────
SELECT id INTO v_lesson_repair_id         FROM ai_prompt_templates WHERE feature_key = 'lesson_repair';
SELECT id INTO v_lesson_prewarm_id        FROM ai_prompt_templates WHERE feature_key = 'lesson_prewarm';
SELECT id INTO v_formula_generation_id    FROM ai_prompt_templates WHERE feature_key = 'formula_generation';
SELECT id INTO v_formula_review_id        FROM ai_prompt_templates WHERE feature_key = 'formula_review';
SELECT id INTO v_mcq_generation_id        FROM ai_prompt_templates WHERE feature_key = 'mcq_generation';
SELECT id INTO v_lesson_quality_review_id FROM ai_prompt_templates WHERE feature_key = 'lesson_quality_review';
SELECT id INTO v_ask_doubt_id             FROM ai_prompt_templates WHERE feature_key = 'ask_doubt';
SELECT id INTO v_ai_tutor_id              FROM ai_prompt_templates WHERE feature_key = 'ai_tutor';
SELECT id INTO v_summary_generation_id    FROM ai_prompt_templates WHERE feature_key = 'summary_generation';
SELECT id INTO v_common_mistakes_id       FROM ai_prompt_templates WHERE feature_key = 'common_mistakes';

-- ── Insert version 1 for each template ───────────────────────────────────────

-- Lesson Repair
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_lesson_repair_id, 1,
    'You are an expert CBSE curriculum editor. Your task is to repair and improve lesson content to meet high educational standards. Ensure the lesson is accurate, well-structured, age-appropriate, and aligned with NCERT guidelines. Return only the corrected lesson content in valid JSON format.',
    'Repair the following CBSE lesson content for {{subject}} — {{chapter}} (Grade {{grade}}).\n\nIssues identified:\n{{issues}}\n\nCurrent content:\n{{content}}\n\nReturn the repaired lesson as valid JSON with keys: title, introduction, sections (array of {heading, body}), key_points (array), summary.',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- Lesson Prewarming
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_lesson_prewarm_id, 1,
    'You are an expert CBSE educator creating high-quality lesson content aligned with NCERT textbooks. Write clear, accurate, and engaging lessons suitable for the specified grade level. Use simple language, real-world examples, and structured explanations.',
    'Generate a comprehensive lesson for CBSE Grade {{grade}} {{subject}}.\n\nChapter: {{chapter}}\nTopic: {{topic}}\nBoard: CBSE\n\nReturn a JSON object with:\n- title: string\n- introduction: string (2-3 sentences)\n- sections: array of {heading: string, body: string, examples: array}\n- key_points: array of strings (5-7 points)\n- summary: string\n- difficulty: "easy" | "medium" | "hard"',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- Formula Generation
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_formula_generation_id, 1,
    'You are a mathematics and science expert specializing in CBSE curriculum. Generate accurate formulas with proper LaTeX notation, clear variable definitions, derivation hints, and worked examples. Always verify mathematical correctness before responding.',
    'Generate all important formulas for the following CBSE topic:\n\nSubject: {{subject}}\nGrade: {{grade}}\nChapter: {{chapter}}\nTopic: {{topic}}\n\nReturn a JSON array where each formula object has:\n- name: string\n- formula_latex: string (LaTeX notation)\n- variables: object mapping symbol to description\n- description: string\n- example: string (worked example)\n- tags: array of strings',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- Formula Review
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_formula_review_id, 1,
    'You are a rigorous CBSE mathematics and science reviewer. Check formulas for correctness, proper LaTeX formatting, accurate variable definitions, and alignment with NCERT standards. Be precise and flag any errors.',
    'Review the following formula for CBSE Grade {{grade}} {{subject}}:\n\nFormula name: {{formula_name}}\nLaTeX: {{formula_latex}}\nVariables: {{variables}}\nDescription: {{description}}\n\nRespond with JSON:\n- is_correct: boolean\n- issues: array of strings (empty if correct)\n- corrected_latex: string (if needed, else same as input)\n- notes: string',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- MCQ Generation
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_mcq_generation_id, 1,
    'You are a CBSE question paper expert. Generate high-quality multiple choice questions that test conceptual understanding, not just memorization. Ensure distractors are plausible, answers are unambiguous, and questions align with NCERT learning objectives.',
    'Generate {{count}} multiple choice questions for:\n\nSubject: {{subject}}\nGrade: {{grade}}\nChapter: {{chapter}}\nTopic: {{topic}}\nDifficulty: {{difficulty}}\n\nReturn a JSON array where each question has:\n- question: string\n- options: array of 4 strings (A, B, C, D)\n- correct_answer: "A" | "B" | "C" | "D"\n- explanation: string\n- difficulty: "easy" | "medium" | "hard"\n- bloom_level: "remember" | "understand" | "apply" | "analyze"',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- Lesson Quality Review
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_lesson_quality_review_id, 1,
    'You are a CBSE curriculum quality auditor. Evaluate lesson content against educational quality standards: accuracy, clarity, completeness, age-appropriateness, NCERT alignment, and engagement. Provide a numerical score and actionable improvement suggestions.',
    'Audit the following lesson content for quality:\n\nSubject: {{subject}}\nGrade: {{grade}}\nChapter: {{chapter}}\n\nContent:\n{{content}}\n\nReturn JSON with:\n- overall_score: number (0-100)\n- accuracy_score: number (0-100)\n- clarity_score: number (0-100)\n- completeness_score: number (0-100)\n- ncert_alignment_score: number (0-100)\n- issues: array of {severity: "critical"|"major"|"minor", description: string}\n- suggestions: array of strings\n- verdict: "approve" | "needs_repair" | "reject"',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- Ask Doubt
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_ask_doubt_id, 1,
    'You are a friendly and knowledgeable CBSE tutor helping students understand concepts clearly. Explain answers step-by-step using simple language. Use analogies and real-world examples. If the question involves calculations, show each step. Encourage the student and build their confidence.',
    'A CBSE Grade {{grade}} student has the following doubt:\n\nSubject: {{subject}}\nChapter: {{chapter}}\n\nStudent question: {{question}}\n\nContext from lesson: {{context}}\n\nProvide a clear, encouraging answer with:\n1. Direct answer to the question\n2. Step-by-step explanation (if applicable)\n3. A simple analogy or example\n4. A tip to remember the concept',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- AI Tutor
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_ai_tutor_id, 1,
    'You are Likha, an AI tutor for CBSE students. You are patient, encouraging, and expert in all CBSE subjects from Grade 1 to 12. You follow the Socratic method — ask guiding questions to help students discover answers themselves. Adapt your language to the student''s grade level. Never just give answers; guide the student to think.',
    'Student profile:\n- Name: {{student_name}}\n- Grade: {{grade}}\n- Subject: {{subject}}\n- Current topic: {{topic}}\n\nConversation history:\n{{history}}\n\nStudent message: {{message}}\n\nRespond as a supportive tutor. If the student is stuck, ask a guiding question. If they answer correctly, praise them and build on it. Keep responses concise (2-4 sentences unless explaining a concept).',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- Summary Generation
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_summary_generation_id, 1,
    'You are a CBSE study material expert. Create concise, well-structured chapter summaries that capture all key concepts, formulas, and learning points. Summaries should help students revise quickly before exams.',
    'Generate a comprehensive revision summary for:\n\nSubject: {{subject}}\nGrade: {{grade}}\nChapter: {{chapter}}\n\nLesson content:\n{{content}}\n\nReturn JSON with:\n- chapter_title: string\n- one_line_summary: string\n- key_concepts: array of {concept: string, explanation: string}\n- important_formulas: array of strings (LaTeX)\n- key_points: array of strings (exam-focused)\n- remember_this: string (most important takeaway)',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

-- Common Mistakes
INSERT INTO ai_prompt_template_versions (template_id, version_number, system_prompt, user_prompt, change_summary)
VALUES (
    v_common_mistakes_id, 1,
    'You are an experienced CBSE teacher who has seen thousands of student papers. Identify the most common conceptual errors, calculation mistakes, and misconceptions students make on this topic. Be specific and provide corrections.',
    'Identify common mistakes CBSE Grade {{grade}} students make in:\n\nSubject: {{subject}}\nChapter: {{chapter}}\nTopic: {{topic}}\n\nReturn a JSON array where each item has:\n- mistake: string (description of the mistake)\n- why_it_happens: string\n- correction: string\n- example: string (show wrong vs correct)',
    'Initial default template'
) ON CONFLICT (template_id, version_number) DO NOTHING;

END $$;
