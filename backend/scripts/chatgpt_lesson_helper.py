"""
ChatGPT Lesson Helper — 2-step workflow to manually prewarm lessons.

STEP 1: Generate the prompt to paste into ChatGPT Desktop
    cd backend
    python3 scripts/chatgpt_lesson_helper.py prompt \
        --grade "Grade 5" \
        --subject "English" \
        --chapter "1. Papa's Spectacles" \
        --step "What We Learn"

    → Prints the full prompt. Paste it into ChatGPT desktop and copy the response.

STEP 2: Store the ChatGPT response in Supabase lesson_cache
    python3 scripts/chatgpt_lesson_helper.py store \
        --grade "Grade 5" \
        --subject "English" \
        --chapter "1. Papa's Spectacles" \
        --step "What We Learn" \
        --file lesson_output.txt

    OR pipe directly:
    pbpaste | python3 scripts/chatgpt_lesson_helper.py store \
        --grade "Grade 5" --subject "English" \
        --chapter "1. Papa's Spectacles" --step "What We Learn"
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from app.services.rag_service import search_textbook_content
from app.services.lesson_cache_service import make_lesson_cache_key, store_lesson_cache, get_cached_lesson
from app.services.tutor_service import (
    PROSE_LITERATURE_SYSTEM, POEM_SYSTEM, TUTOR_SYSTEM, DIAGRAM_HINT,
    detect_chapter_type,
)


def cmd_prompt(args):
    """Print the full prompt to paste into ChatGPT desktop."""
    grade = args.grade
    subject = args.subject
    chapter = args.chapter
    step = args.step
    mode = args.mode
    board = args.board

    # Fetch RAG chunks
    rag_results = search_textbook_content(
        query=f"{grade} {subject} {chapter} {step}",
        board=board, grade=grade, subject=subject, chapter=chapter,
        match_count=10,
    )
    if not rag_results:
        rag_results = search_textbook_content(
            query=f"{grade} {subject} {chapter}",
            board=board, grade=grade, subject=subject, chapter=None,
            match_count=10,
        )

    textbook_context = "\n\n".join(r.get("chunk_text", "") for r in rag_results)
    chapter_type = detect_chapter_type(subject, chapter)

    # Pick system prompt
    if chapter_type == "prose":
        system = PROSE_LITERATURE_SYSTEM
    elif chapter_type == "poem":
        system = POEM_SYSTEM
    else:
        system = TUTOR_SYSTEM

    # Determine step number
    default_steps = ["What We Learn", "Core Concepts", "Worked Examples", "Exam-style problems", "Revision"]
    step_num = default_steps.index(step) + 1 if step in default_steps else 1

    user_prompt = f"""
Grade: {grade}
Mode: {mode}
Subject: {subject}
Chapter: {chapter}
Current sub-topic: {step}

Teacher Persona: Standard CBSE tutor

Relevant textbook/RAG context:
{textbook_context if textbook_context else "No uploaded textbook context found."}

Create a focused step-wise lesson only for this sub-topic.
Do not cover unrelated topics.

Textbook coverage rules:
- Use the uploaded textbook context deeply.
- Extract and teach all important concepts.
- Include definitions, examples, and review questions.

Depth: Use simpler words and concrete examples for Class {grade.replace('Grade ', '')}.

{DIAGRAM_HINT}

Worked example: Start with "Question: <complete problem>", then step-by-step solution.
NEVER ask the student to draw or sketch.

End with a short next-step instruction, not a question.
"""

    print("=" * 70)
    print("STEP 1 OF 2 — COPY THE BLOCK BELOW AND PASTE INTO CHATGPT DESKTOP")
    print("=" * 70)
    print()
    print("━━━ SYSTEM PROMPT (paste as 'Custom Instructions' or first message) ━━━")
    print()
    print(system.strip())
    print()
    print("━━━ USER PROMPT ━━━")
    if chapter_type in ("prose", "poem"):
        print(f"You are teaching STEP {step_num} of a {'Prose/Literature' if chapter_type == 'prose' else 'Poem'} lesson.")
        print()
    print(user_prompt.strip())
    print()
    print("=" * 70)
    print("After ChatGPT responds, copy the FULL response.")
    print()
    print("Then run STEP 2 to store it:")
    print()
    safe_chapter = chapter.replace("'", "\\'").replace('"', '\\"')
    print(f"  # Option A: pipe from clipboard (macOS)")
    print(f"  pbpaste | python3 scripts/chatgpt_lesson_helper.py store \\")
    print(f'    --grade "{grade}" --subject "{subject}" \\')
    print(f'    --chapter "{chapter}" --step "{step}" --mode "{mode}"')
    print()
    print(f"  # Option B: save response to a file first")
    print(f"  python3 scripts/chatgpt_lesson_helper.py store \\")
    print(f'    --grade "{grade}" --subject "{subject}" \\')
    print(f'    --chapter "{chapter}" --step "{step}" \\')
    print(f"    --file lesson_output.txt")
    print("=" * 70)


def cmd_store(args):
    """Store the ChatGPT-generated lesson in Supabase lesson_cache."""
    grade = args.grade
    subject = args.subject
    chapter = args.chapter
    step = args.step
    mode = args.mode
    board = args.board

    # Read lesson content
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            lesson_content = f.read().strip()
        print(f"📂 Read {len(lesson_content)} chars from {args.file}")
    else:
        print("📋 Reading lesson content from stdin (paste content, then press Ctrl+D)...")
        lesson_content = sys.stdin.read().strip()

    if not lesson_content:
        print("❌ No lesson content provided. Aborting.")
        sys.exit(1)

    cache_key = make_lesson_cache_key(
        board=board, grade=grade, subject=subject, chapter=chapter,
        mode=mode, step_title=step, teacher_persona="",
    )

    # Determine source type
    rag_results = search_textbook_content(
        query=f"{grade} {subject} {chapter}",
        board=board, grade=grade, subject=subject, chapter=chapter,
        match_count=3,
    )
    source_type = "RAG" if rag_results else "LLM"

    # Check if already cached
    existing = get_cached_lesson(cache_key, grade=grade)
    if existing and not args.force:
        print(f"⚠️  Already cached for: {grade} | {subject} | {chapter} | {step}")
        print("   Use --force to overwrite.")
        sys.exit(0)

    store_lesson_cache(
        cache_key=cache_key,
        lesson_content=lesson_content,
        source_type=source_type,
        board=board, grade=grade, subject=subject, chapter=chapter,
        mode=mode, step_title=step, teacher_persona="",
        practice_questions=[],
    )

    print(f"✅ Stored in lesson_cache!")
    print(f"   Grade:    {grade}")
    print(f"   Subject:  {subject}")
    print(f"   Chapter:  {chapter}")
    print(f"   Step:     {step}")
    print(f"   Source:   {source_type}")
    print(f"   Chars:    {len(lesson_content)}")
    print(f"   Key:      {cache_key[:20]}...")
    print()
    print("Students will now get this pre-warmed lesson instantly (0 LLM tokens).")


def main():
    parser = argparse.ArgumentParser(description="ChatGPT Lesson Helper")
    sub = parser.add_subparsers(dest="command")

    # Shared args
    def add_common(p):
        p.add_argument("--grade",   required=True)
        p.add_argument("--subject", required=True)
        p.add_argument("--chapter", required=True)
        p.add_argument("--step",    required=True)
        p.add_argument("--mode",    default="CBSE")
        p.add_argument("--board",   default="CBSE")

    # prompt command
    p_prompt = sub.add_parser("prompt", help="Generate ChatGPT prompt")
    add_common(p_prompt)

    # store command
    p_store = sub.add_parser("store", help="Store ChatGPT output in lesson_cache")
    add_common(p_store)
    p_store.add_argument("--file",  default=None,  help="Read lesson from file (default: stdin)")
    p_store.add_argument("--force", action="store_true", help="Overwrite existing cache entry")

    args = parser.parse_args()

    if args.command == "prompt":
        cmd_prompt(args)
    elif args.command == "store":
        cmd_store(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
