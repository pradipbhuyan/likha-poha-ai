# Subjective Question Bank Quality Audit

Flags questions that treat internal lesson-authoring markdown scaffolding
(bolded sub-labels, section names like 'Section B', 'Opening overview',
'Worked example', 'Revision and recap') as if it were real chapter content,
instead of testing actual facts, characters, events, or concepts from the
chapter/story/poem itself.

This is a READ-ONLY audit. No rows were modified.

## Summary

| Grade | Total Questions | Flagged | % Flagged | Chapters Affected |
|---|---|---|---|---|
| Grade 9 | 1360 | 0 | 0.0% | 0 |
| **TOTAL** | **1360** | **0** | **0.0%** | **0** |

## Details by Grade / Chapter

## Recommended Next Steps

1. Review the flagged chapters above. For each affected chapter, run:
   ```
   python3 scripts/purge_templated_subjective_questions.py --grade "<grade>" --dry-run
   python3 scripts/purge_templated_subjective_questions.py --grade "<grade>"
   ```
2. Re-author the affected chapter(s) using the now-fixed prompt template:
   ```
   python3 scripts/prepare_gpt55_subjective_question_prompts.py --grade "<grade>" --subject "<subject>" --chapters "<chapter>"
   ```
3. Paste into a fresh GPT-5.5 session, save the JSON, then ingest:
   ```
   python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir <folder> --dry-run
   python3 scripts/ingest_gpt55_subjective_question_bank_output.py --dir <folder>
   ```
   The updated ingest script now automatically rejects any question matching
   this same bad pattern, so a re-authored batch cannot silently reintroduce it.