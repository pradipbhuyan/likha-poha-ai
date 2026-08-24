You are fixing corrupted "Ask about this chapter" answer cards in a CBSE tutoring app.

Each card below has a QUESTION (keep as-is) and a CURRENT ANSWER that is corrupted —
either from duplicated/garbled characters (e.g. "NDERSTNDERST", "A RefundA RefundA
Refund") or from formulas that got flattened into disjointed symbol soup during
extraction (e.g. "GM R GM R GM R", "ˆ ˆ ˆ" for vectors).

Root cause, for context: the source NCERT PDFs render bold text (headings, some
table rows) as multiple stacked copies of the same glyphs in the PDF's text layer.
Any text extractor reproduces this as literally repeated words/letters. It is a
source-file artifact, not a transcription error — treat any run of an immediately
repeated word, phrase, or letter-cluster as ONE occurrence and ignore the repetition.

TEXTBOOK CONTEXT for this chapter follows the card list — it is the actual text the
app ingested for RAG grounding, with a best-effort automatic dedup pass already
applied. It may still contain minor residual noise (stray page numbers, a leftover
duplicated fragment); use only the substantive content and ignore anything that
looks like extraction noise rather than real chapter text.

For EACH card, write a corrected answer as 3-6 concise bullet points:
- Grounded strictly in the textbook context provided (no outside knowledge).
- Clear, well-formed prose — no leftover extraction artifacts.
- For formula-based cards, write the formula/derivation in plain readable notation
  (e.g. "U = 1/2 CV^2 = Q^2 / 2C" not scattered symbols), preserving the actual
  mathematical content from the context.
- If the context genuinely does not contain enough to answer a card, say so in the
  "note" field instead of guessing.

Return ONLY a JSON array, one object per card, in EXACTLY this schema:

[
  {
    "id": "<card id, copied exactly>",
    "answer": "- bullet one\n- bullet two\n- bullet three",
    "note": ""
  }
]

No markdown fences, no commentary outside the JSON array.

---

## Cards to fix (1)

### Card 1
id: 4b0ba94e-d5b8-4fb4-8b19-ab722e6898f5
question: What is the principle of conservation of mechanical energy?
current (corrupted) answer:
- From the principle of conservation of mechanical energy 1 2 4 2 v GM R GM R GM R GM R 2 − − = − − 5 or
- 2 1 5 4 2 2 R M G v 2 / 1 5 3 R M G v
detected issues: ["repeated_phrase:['GM R']", 'short_token_run_x1']

---

## Textbook context (Grade 11 / Physics / Physical World)

[No matching rag_documents entry found — regenerate from your own copy of the NCERT chapter text.]
