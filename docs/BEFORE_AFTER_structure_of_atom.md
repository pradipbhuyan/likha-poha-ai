# BEFORE / AFTER — Grade 11 Chemistry: "Structure of Atom"
### Step: "Concept introduction" (one of 5 steps in this chapter)

This is a real, verbatim comparison pulled directly from Supabase
`lesson_cache` — not a mockup. It shows exactly what a student saw
**before** remediation and what they see **now**, after the Track A fix
described in `docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md`.

---

## ❌ BEFORE (original, LLM-generated, `source_type = "RAG"`)

```markdown
# Concept Introduction: Structure of Atom

## What you will learn
In this lesson, you will understand what an atom is, why atoms are the
basic building blocks of matter, and how scientists have studied atoms
over time. You will also learn the importance of the structure of atoms
in understanding chemistry.

## Simple explanation
Atoms are tiny particles that make up everything around us—like the air
we breathe, the water we drink, and the objects we see. They are so small
that we cannot see them with our eyes. Scientists have studied atoms to
understand what they are made of and how they behave. The structure of an
atom explains how atoms are built and how they interact with each other.

## Step-by-step breakdown
- **What is an atom?**
  An atom is the smallest unit of matter that retains the properties of
  an element. It is like a tiny building block of everything.
- **Why are atoms important?**
  Because all matter is made up of atoms, understanding atoms helps us
  understand the nature of everything around us.
- **Historical background:**
  Scientists like John Dalton proposed that atoms are indivisible
  particles. Later, with advanced experiments, it was found that atoms
  are made up of even smaller particles called electrons, protons, and
  neutrons.
- **Why study the structure of an atom?**
  Knowing the structure helps us understand how atoms bond to form
  molecules, how elements behave, and how chemical reactions happen.
- **How do scientists study atoms?**
  Using special tools like microscopes and experiments such as
  scattering of particles, scientists have uncovered the internal
  structure of atoms.

## Worked example
Question: The following data shows the mass of a substance and its
volume at standard temperature and pressure (STP). Calculate the density
of the substance.
Mass = 28 g
Volume = 41.9 mL

Solution:
- Step 1: Recall the formula for density: Density = Mass / Volume
- Step 2: Substitute the values: Density = 28 g / 41.9 mL
- Step 3: Calculate: Density ≈ 0.668 g/mL
- Step 4: Interpretation: The density of the substance is approximately
  0.668 g/mL, which helps us identify or compare it with known substances.

This example shows how measurements of mass and volume help us understand
the properties of substances, linking to the concept that atoms and
molecules have specific densities.

## Common mistake
A common mistake is confusing mass and weight. Remember, mass is the
amount of matter and remains constant everywhere, while weight depends on
gravity and can change from place to place. Also, when calculating
density, ensure units are consistent and use the correct formula.

## Quick check question
Why is it important to understand the structure of an atom in chemistry?

## Summary
In this lesson, we learned that atoms are the fundamental building
blocks of matter. They are tiny, indivisible units that make...
[content is truncated / incomplete in the original]
```

### 🔴 What is wrong with this (mapped to Tier A + manual review findings)

| Problem | Evidence in text above |
|---|---|
| **Contamination** — density is a "Some Basic Concepts of Chemistry" topic, not Structure of Atom | Entire "Worked example" section calculates density from mass/volume — has nothing to do with atomic structure |
| **Contamination** — mass-vs-weight is lab-measurement content from a different chapter | Entire "Common mistake" section |
| **0% syllabus coverage** — none of the chapter's actual content appears | No mention of cathode rays, Thomson, Rutherford, Bohr, Planck, quantum numbers, Aufbau, etc. — the manifest's `must_include_keywords` (22 terms) are **100% missing** |
| **Vague, unfalsifiable claims** | "Using special tools like microscopes and experiments such as scattering of particles" — vague, and microscopes are not the real historical method (cathode-ray tube + alpha-scattering are) |
| **Quick check has no answer** | "Why is it important..." — no answer, no explanation, no feedback |
| **Content is truncated mid-sentence** | Summary cuts off at "...make" |

---

## ✅ AFTER (manually authored, NCERT-grounded, `source_type = "MANUAL"`)

```markdown
# Concept Introduction: Structure of Atom

## What you will learn
In this lesson you will learn how scientists discovered that atoms are
not indivisible, how the electron, proton and neutron were discovered,
and how this led to the first atomic models (Thomson and Rutherford).
This is the foundation for everything else in this chapter — the Bohr
model, quantum numbers, and electronic configuration.

## Simple explanation
Atoms were once thought to be the smallest, indivisible particles of
matter — this was John Dalton's atomic theory (1808). But towards the end
of the nineteenth century, scientists discovered that atoms are actually
made of even smaller particles: electrons, protons and neutrons. This
discovery came mainly from experiments on electrical discharge through
gases (cathode-ray tubes), and later from experiments that measured the
mass and charge of these particles precisely.

## Step-by-step breakdown
- **Cathode-ray discharge tube experiments**: particles flow from cathode
  to anode, travel in straight lines, are deflected as negatively charged
  particles by electric/magnetic fields, and behave the same regardless
  of gas or electrode material — proving **electrons** are a basic
  constituent of all atoms.
- **Measuring the electron**: J.J. Thomson (1897) measured e/m_e =
  1.758820 × 10^11 C/kg. Millikan's oil drop experiment (1906–14)
  measured the charge: −1.602176 × 10^−19 C. Combined, mass of electron
  = 9.1094 × 10^−31 kg.
- **Discovery of proton and neutron**: canal rays → proton (1919, from
  hydrogen); Chadwick (1932) → neutron, from bombarding beryllium with
  alpha particles.
- **Why this matters**: these three particles set up the need for the
  atomic models covered next — Thomson's and Rutherford's.

## Worked example
Question: Calculate the number of protons, neutrons and electrons in
Br-80 (bromine-80), given atomic number Z = 35 and mass number A = 80.
(NCERT Problem 2.1)

Solution:
- Step 1: Neutral atom → protons = electrons = Z = 35.
- Step 2: Neutrons = A − Z = 80 − 35 = 45.
- Final answer: 35 protons, 35 electrons, 45 neutrons.

## Common mistake
A common mistake is confusing atomic number (Z, the number of protons)
with mass number (A, protons + neutrons). Remember: Z never changes for a
given element, but A can vary between isotopes of the same element.
Another common mistake is assuming a species is a neutral atom without
checking whether protons equal electrons — if they don't, it's an ion.

## Quick check question
Question: An atom has 6 protons and 6 neutrons. What is its mass number,
and what is its atomic number?
Answer: Atomic number Z = 6. Mass number A = 6 + 6 = 12.
Explanation: Atomic number always equals the proton count, and mass
number is the sum of protons and neutrons — this atom is carbon-12.

## Summary
- Atoms are made of three sub-atomic particles: electrons, protons and
  neutrons — discovered through cathode-ray, Millikan oil-drop, and
  Chadwick's neutron-discovery experiments.
- Atomic number (Z) = number of protons = number of electrons in a
  neutral atom.
- Mass number (A) = number of protons + number of neutrons.
- These discoveries set the stage for the atomic models covered next:
  Thomson's model and Rutherford's nuclear model.
```

### 🟢 Why this is correct (mapped to the manifest)

| Fixed problem | How the AFTER version addresses it |
|---|---|
| Contamination (density, mass-vs-weight) | Removed entirely — replaced with content about cathode rays, Thomson's electron measurement, Millikan, and Chadwick — all in `in_scope_units` of the manifest |
| 0% syllabus coverage | Now covers 6 of the manifest's 22 `must_include_keywords` in this one step alone (cathode ray, Thomson, Millikan, Chadwick, nucleus is implied via later steps) — remaining keywords (Bohr, Planck, Aufbau, etc.) are covered by the other 4 steps of the same chapter |
| Vague "microscopes" claim | Replaced with the actual historical method: cathode-ray discharge tube experiments |
| Quick check has no answer | Now has Question + Answer + Explanation, matching the platform's 8-section schema requirement |
| Content truncated | Complete, properly closed Summary section |
| Worked example irrelevant (density) | Replaced with NCERT Problem 2.1 (Br-80 proton/neutron/electron calculation) — directly reinforces this step's own concept |

---

## How the "fusion" between current and missing content actually works

You asked: **how do we plug the gap between the current rendered lesson
and what should be there — how do old and new content get "fused"?**

The honest answer: **for Tier 1 "golden" chapters (like this one), there
is no fusion — it is a full, deliberate replacement**, not a patch or
merge. Here is why, and what the actual mechanics are:

### Why replacement, not fusion, for Tier 1 chapters
The original content wasn't *missing a few facts* — it was **structurally
wrong** (wrong topics mixed in, a scientifically incorrect claim, a broken
worked example). You cannot "fuse" correct content with contaminated
content and get something good — the contaminated parts (density
calculation, mass-vs-weight discussion) have to be removed, not blended
in. Trying to salvage/patch individual sentences from the original would
have been slower and riskier than authoring a clean, NCERT-grounded
version from scratch using the same 8-section template.

### The actual mechanical steps (what really happens under the hood)
1. **`lesson_cache` row already exists** for
   `(Grade 11, Chemistry, Structure of Atom, "Concept introduction")`,
   keyed by a deterministic SHA-256 `cache_key` computed from those five
   fields (`make_lesson_cache_key()` in `lesson_cache_service.py`).
2. **`seed_manual_lesson_content.py` computes the exact same `cache_key`**
   for the same five fields — this is what lets it target the *same* row,
   not create a duplicate.
3. It calls **`store_lesson_cache()`** with the new content and
   `source_type="MANUAL"`. Internally this does an **UPDATE** on the
   existing row (not an insert) — see `store_lesson_cache()`'s
   "Step 1: check if any row with this cache_key already exists... UPDATE"
   logic. The row's `id`, `cache_key`, and `access_count` are preserved;
   only `lesson_content` and `source_type` change.
4. **The student-facing app doesn't change at all.** `get_cached_lesson()`
   is called by the same lesson-serving code path exactly as before — it
   still does `SELECT lesson_content WHERE cache_key = ... AND status =
   'active'`. It has no idea whether the content came from a live LLM call
   or from our manual seed script. **This is exactly why Track A works
   with zero application-code changes** — we are replacing data, not
   logic.
5. **Immediately after the update**, any student opening this lesson step
   sees the new content — no cache purge, no redeploy needed, because the
   row was updated in place.

### What "fusion" *would* look like for Tier 2 chapters (the other 3,000+ chapters that stay on live generation)
For chapters that are **not** promoted to Tier 1, the "gap-plugging" is
different — it happens **at generation time, not after the fact**:
- The chapter's manifest (`in_scope_units`, `banned_topics`,
  `must_include_keywords`) gets injected into the **live** system prompt
  (`TUTOR_SYSTEM` in `tutor_service.py`) as explicit constraints, in
  addition to the RAG-retrieved textbook chunks that are already injected
  today.
- This doesn't touch old cached content directly — but the **next time**
  that chapter/step is regenerated (cache miss, or marked stale after a
  RAG re-upload), the LLM call now includes "ONLY use these topics, NEVER
  mention these banned topics, MUST include these keywords" — so the
  *newly generated* content is the fused/corrected version, produced by
  the LLM itself under tighter guardrails, rather than hand-written.
- This is Phase 4 ("Prevent regression") in the main plan document —
  not yet implemented, planned as the next phase after Tier A is wired
  into the admin dashboard.

### Summary table: two different gap-plugging mechanisms

| | Tier 1 (golden chapters) | Tier 2 (everything else) |
|---|---|---|
| Where the gap is closed | Directly in `lesson_cache`, per step | In the LLM prompt, before generation |
| Mechanism | `store_lesson_cache()` UPDATE, bypasses LLM entirely | Manifest injected into `TUTOR_SYSTEM` prompt as constraints |
| Old content | Fully replaced (not fused) | Regenerated fresh on next cache miss/staleness, guided by manifest |
| Effort per chapter | High (author full content) — but one-time | Low (author manifest only) — reusable forever |
| Verification | Tier A audit re-run → 0 findings (already proven) | Tier A audit run periodically on regenerated content |
