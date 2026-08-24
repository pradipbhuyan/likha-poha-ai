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

## Cards to fix (4)

### Card 1
id: 78a81c6c-abf6-44ca-b079-eb6c4eea73ef
question: Find the scalar product of vectors a and b.
current (corrupted) answer:
- ˆ ˆ ˆ ˆ ˆ ˆ (3 4 5 ) ( 2 3 ) 6 4 15 25 = − + − + − = − − − = − a b i j k i j k i
detected issues: ["repeated_phrase:['ˆ ˆ']", 'page_number_noise', 'short_token_run_x1']

### Card 2
id: ffef8b64-0b29-475c-b2db-c1b09cced4af
question: Find the vector product of vectors a and b.
current (corrupted) answer:
- ˆ ˆ ˆ ˆ ˆ ˆ 3 4 5 7 5 2 1 3 × = − = − − − − i j k a b i j k
detected issues: ["repeated_phrase:['ˆ ˆ']", 'short_token_run_x1']

### Card 3
id: 4f0a883a-9336-4418-b2eb-b16ed85b3549
question: What is the determinant form to remember for a × b?
current (corrupted) answer:
- a × b can be put in a determinant form which is easy to remember.
- ˆ ˆ ˆ ˆ ˆ ˆ x y z x y z a a a b b b × = i j k a b
detected issues: ["repeated_phrase:['ˆ ˆ']", 'short_token_run_x1']

### Card 4
id: 137e0a1d-4dd3-4058-9849-a04005661e45
question: What is the determinant form to remember for a × b?
current (corrupted) answer:
- ˆ ˆ ˆ ˆ ˆ ˆ x y z x y z a a a b b b × = i j k a b
detected issues: ["repeated_phrase:['ˆ ˆ']", 'short_token_run_x1']

---

## Textbook context (Grade 11 / Physics / Systems of Particles and Rotational Motion)

[No matching rag_documents entry found — regenerate from your own copy of the NCERT chapter text.]
