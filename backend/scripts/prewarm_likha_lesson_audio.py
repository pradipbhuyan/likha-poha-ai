"""Prewarm cached Likha narration MP3s for Grades 5–8 English and Hindi.

Reads only existing stored chapter documents. It never generates lesson content.
For every stored document it creates audio for each milestone and optional
Wrap-up, skipping paths that already exist in Supabase Storage/cache.

Usage:
    python3 scripts/prewarm_likha_lesson_audio.py --dry-run
    python3 scripts/prewarm_likha_lesson_audio.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
sys.path.insert(0, str(BACKEND_DIR))

from app.services.audio_cache_service import get_cached_audio_url, store_audio
from app.services.chapter_doc_service import get_stored_chapter_doc
from app.services.prewarm_service import get_chapters_for_grade
from app.services.tts_service import clean_text_for_tts, generate_speech_file

GRADES = ("Grade 5", "Grade 6", "Grade 7", "Grade 8")
VOICES = {
    "english": "en-IN-NeerjaNeural",
    "hindi": "hi-IN-SwaraNeural",
}
RATE = "+5%"


def narration_text(milestone: dict) -> str:
    sections = [str(milestone.get("title") or "Lesson section")]
    for block in milestone.get("blocks") or []:
        block_type = block.get("type")
        if block_type == "hook":
            sections.append(str(block.get("text") or ""))
        elif block_type in ("concept", "watchout"):
            sections.extend([str(block.get("title") or ""), str(block.get("body_md") or "")])
        elif block_type == "example":
            sections.extend([str(block.get("question") or ""), str(block.get("body_md") or "")])
        elif block_type == "vocab":
            sections.extend(
                f"{word.get('term', '')} means {word.get('meaning', '')}."
                for word in block.get("words") or []
            )
        elif block_type in ("quickcheck", "freetext_qa"):
            sections.append(f"Quick check. {block.get('question') or ''}")
    return " ".join(part.strip() for part in sections if str(part).strip())


def chapter_paths(doc: dict) -> list[tuple[str, str]]:
    paths = []
    for index, milestone in enumerate(doc.get("milestones") or []):
        title = str(milestone.get("title") or f"Section {index + 1}").strip()
        paths.append((f"__avatar_narration__milestone_{index}_{title}"[:180], narration_text(milestone)))

    recap = (doc.get("recap") or {}).get("body_md")
    if recap and str(recap).strip():
        paths.append(("__avatar_narration__wrap_up_Wrap-up", f"Wrap-up. {recap}"))
    return paths


def prewarm_path(grade: str, subject: str, chapter: str, step_title: str, text: str, voice: str, dry_run: bool) -> str:
    if get_cached_audio_url(grade, subject, chapter, step_title, voice, RATE):
        return "skipped"

    if dry_run:
        return "pending"

    mp3_path = generate_speech_file(
        clean_text_for_tts(text),
        voice=voice,
        rate=RATE,
        pitch="+5Hz",
    )
    try:
        with open(mp3_path, "rb") as audio_file:
            store_audio(grade, subject, chapter, step_title, audio_file.read(), voice, RATE)
    finally:
        try:
            os.remove(mp3_path)
        except OSError:
            pass
    return "generated"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="List paths without generating/uploading MP3s.")
    parser.add_argument("--grade", choices=GRADES, help="Prewarm one grade only.")
    parser.add_argument("--subject", choices=("English", "Hindi"), help="Prewarm one subject only.")
    parser.add_argument("--delay", type=float, default=0.3, help="Seconds to wait between TTS requests.")
    args = parser.parse_args()

    totals = {"stored_docs": 0, "pending": 0, "skipped": 0, "generated": 0, "failed": 0}
    grades = (args.grade,) if args.grade else GRADES

    for grade in grades:
        for item in get_chapters_for_grade(grade):
            subject = str(item["subject"] or "").strip()
            if args.subject and subject != args.subject:
                continue
            voice = VOICES.get(subject.casefold())
            if not voice:
                continue

            chapter = str(item["chapter"] or "").strip()
            doc = get_stored_chapter_doc("CBSE", grade, subject, chapter, item["mode"])
            if not doc:
                continue

            totals["stored_docs"] += 1
            for step_title, text in chapter_paths(doc):
                if not text.strip():
                    continue
                try:
                    result = prewarm_path(grade, subject, chapter, step_title, text, voice, args.dry_run)
                    totals[result] += 1
                    print(f"{result:9} | {grade} | {subject} | {chapter} | {step_title}")
                except Exception as exc:
                    totals["failed"] += 1
                    print(f"FAILED    | {grade} | {subject} | {chapter} | {step_title}: {exc}")
                if not args.dry_run:
                    time.sleep(args.delay)

    print("\nPrewarm summary:", totals)


if __name__ == "__main__":
    main()
