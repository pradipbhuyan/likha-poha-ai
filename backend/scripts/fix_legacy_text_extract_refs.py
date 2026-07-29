#!/usr/bin/env python3
"""
Fix Legacy Text-Form extract-ref Blocks -> Real PDF Page-Image Popups
========================================================================
`ExtractPopupBlock.jsx` supports two JSON shapes for a fenced
```extract-ref``` block:
  1. Page-image form (current/preferred): includes `asset_url` (+
     `page_number`) and renders the ACTUAL scanned NCERT textbook page.
  2. Legacy text-extract form: only `extract_text`, no `asset_url` --
     renders a plain-text card instead of the real page. This is what
     was showing for a citation like "NCERT प्रश्न-अभ्यास 9" (see
     screenshot report): the popup never opens the actual PDF page.

This one-off script finds every remaining legacy-form block across the
whole platform (checked live: 14 total, in Grade 10 Hindi, Grade 9
Hindi, Grade 9 English and Grade 9 Advanced Science) and converts the
ones that DO have a real source PDF (i.e. have >=1 row in
rag_visual_assets for their rag_documents id) to the page-image form,
using a manually verified (lesson_cache_id -> document_id, page_number)
mapping table below -- built by grepping each target page's
`nearby_text` for the actual citation text, since these are Hindi/
legacy-font PDFs where automatic citation-to-page matching (as done by
inject_page_refs_universal.py) doesn't reliably match every case.

Grade 9 Advanced Science's 7 legacy blocks are NOT included here: their
rag_documents rows have ZERO rows in rag_visual_assets (no source PDF
was ever uploaded/rendered for that curriculum), so there is no real
page image to link to. Those must stay as legacy text-form blocks (or
be fixed manually in a future session if a source PDF becomes
available).

Usage:
    cd backend
    python3 scripts/fix_legacy_text_extract_refs.py --dry-run
    python3 scripts/fix_legacy_text_extract_refs.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auth_service import admin_client  # noqa: E402
from app.services.grade_db_router import get_content_db  # noqa: E402

_EXTRACT_REF_RE = re.compile(r"```extract-ref\s*\n(\{.*?\})\s*\n```", re.DOTALL)

# (lesson_cache.id, document_id, page_number) -- manually verified by
# reading each target page's rag_visual_assets.nearby_text and
# confirming it contains the numbered NCERT प्रश्न-अभ्यास / अभ्यास /
# Critical Reflection heading matching the citation in that row.
ROW_TO_PAGE = {
    # Grade 10 Hindi, अध्याय 1: सूरदास -- all 4 citations (प्रश्न-अभ्यास
    # 1, 6, 9, 12) are printed together on the single प्रश्न-अभ्यास page.
    "d5463e32-d910-4109-80fc-dc03cd2736f9": (410, 7),
    "806cd85f-ab40-47e6-b640-559820c1fb40": (410, 7),
    "d1f48bb8-c07c-4090-97a8-d64035905a27": (410, 7),
    "d977c5d0-fa24-45b3-9cbd-ef1fb733a155": (410, 7),
    # Grade 9 Hindi, अध्याय 8: पद -- अभ्यास "मेरे उत्तर मेरे तर्क" heading.
    "c7f59b3e-5e8d-4da3-82ad-221e5cac71b3": (389, 5),
    # Grade 9 English, Chapter 1: How I Taught My Grandmother to Read
    # -- both citations are on the same "Critical Reflection" page.
    "ed4ef1e0-8358-4909-8c58-d546d1f2638c": (374, 10),
    "049789f6-06b5-4e34-8a67-80e8a44d2875": (374, 10),
    # Grade 9 English, Chapter 3: Winds of Change -- "Critical Reflection" page.
    "11bb4209-4b6d-4ecf-ad75-ccc8982a1361": (376, 6),
    # Grade 10 Social Science (History), Chapter 1: The Rise of
    # Nationalism in Europe -- opening Activity citation is on the page
    # printing Fig. 1 (Sorrieu's print) and its caption; the four
    # "Discuss" questions are all printed together on the single
    # end-of-chapter Discuss page.
    "5539ad4a-5e1b-4f00-848c-e1274179f97e": (335, 3),
    "faca36db-6fe7-46ef-9fe9-4c6641f8a06f": (335, 28),
    "37ca9b49-c7e1-4b87-974b-0f2099cd4045": (335, 28),
    "a14108e9-d099-41a8-be73-969559e7c6d1": (335, 28),
    "20b380b9-9aef-4266-89ab-3029aaeebe46": (335, 28),
}


def fetch_asset_url(document_id: int, page_number: int) -> str | None:
    r = (
        admin_client.table("rag_visual_assets")
        .select("asset_url")
        .eq("document_id", document_id)
        .eq("page_number", page_number)
        .limit(1)
        .execute()
    )
    if r.data:
        return r.data[0]["asset_url"]
    return None


def convert_block(match_json: str, document_id: int, page_number: int, asset_url: str) -> str:
    d = json.loads(match_json)
    new_d = {
        "citation": d.get("citation", ""),
        "page_number": page_number,
        "asset_url": asset_url,
    }
    if d.get("note"):
        new_d["note"] = d["note"]
    return json.dumps(new_d, ensure_ascii=False)


def run(dry_run: bool) -> None:
    print(f"\n  Fix legacy text-form extract-ref blocks -> real PDF page images")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}\n")

    # These rows can live in either the CBSE-grade-9/10 shard or the
    # legacy shard depending on grade; try both content DBs since this
    # script spans Grade 9 and Grade 10 rows.
    dbs = []
    for g in ("Grade 9", "Grade 10"):
        try:
            dbs.append(get_content_db(g))
        except Exception:
            pass
    # De-duplicate identical client instances.
    seen_ids = set()
    unique_dbs = []
    for db in dbs:
        if id(db) not in seen_ids:
            seen_ids.add(id(db))
            unique_dbs.append(db)

    fixed = 0
    for row_id, (document_id, page_number) in ROW_TO_PAGE.items():
        asset_url = fetch_asset_url(document_id, page_number)
        if not asset_url:
            print(f"  [skip] {row_id}: no rag_visual_assets row for document_id={document_id} page={page_number}")
            continue

        found_row = None
        found_db = None
        for db in unique_dbs:
            r = db.table("lesson_cache").select("id,lesson_content").eq("id", row_id).execute()
            if r.data:
                found_row = r.data[0]
                found_db = db
                break

        if not found_row:
            print(f"  [skip] {row_id}: lesson_cache row not found in any content DB")
            continue

        text = found_row["lesson_content"] or ""

        def _replace(m):
            raw_json = m.group(1)
            try:
                d = json.loads(raw_json)
            except Exception:
                return m.group(0)
            if "asset_url" in d:
                return m.group(0)  # already page-image form, leave untouched
            new_json = convert_block(raw_json, document_id, page_number, asset_url)
            return f"```extract-ref\n{new_json}\n```"

        new_text, n = _EXTRACT_REF_RE.subn(_replace, text)
        if n == 0:
            print(f"  [skip] {row_id}: no extract-ref block matched (already fixed?)")
            continue

        print(f"  {row_id}: converting {n} block(s) -> document_id={document_id} page={page_number}")
        if not dry_run:
            found_db.table("lesson_cache").update({"lesson_content": new_text}).eq("id", row_id).execute()
        fixed += 1

    print(f"\n  {'Would fix' if dry_run else 'Fixed'} {fixed} lesson_cache row(s).")

    if not dry_run and fixed:
        print("\n  Invalidating chapter_doc caches for affected chapters...")
        affected_chapters = [
            ("Grade 10", "Hindi", "अध्याय 1: सूरदास"),
            ("Grade 9", "Hindi", "अध्याय 8: पद"),
            ("Grade 9", "English", "Chapter 1: How I Taught My Grandmother to Read"),
            ("Grade 9", "English", "Chapter 3: Winds of Change"),
            ("Grade 10", "Social Science", "Chapter 1: The Rise of Nationalism in Europe"),
        ]
        for grade, subject, chapter in affected_chapters:
            try:
                db = get_content_db(grade)
                db.table("lesson_chapter_doc").delete().eq("grade", grade).eq("subject", subject).eq("chapter", chapter).execute()
                print(f"    invalidated: {grade} / {subject} / {chapter}")
            except Exception as e:
                print(f"    [warn] could not invalidate {grade}/{subject}/{chapter}: {e}")

    print("\nDone.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix legacy text-form extract-ref blocks to real PDF page images")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
