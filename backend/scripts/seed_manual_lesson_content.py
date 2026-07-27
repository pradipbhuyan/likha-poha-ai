#!/usr/bin/env python3
"""
Seed Manual Lesson Content (Track A remediation)
===================================================
Phase 3 / Track A of the Lesson Content Quality Review Plan
(see docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md).

Injects human-authored, chapter-manifest-grounded lesson content directly
into Supabase `lesson_cache`, bypassing live LLM generation entirely for
the given steps. This is the JSON-backed manual-content mechanism
equivalent to the one previously used for Q&A gap-filling.

Content authored in LESSONS below is grounded word-by-word in the NCERT
source PDF (kech102.pdf, Grade 11 Chemistry, Unit 2 — Structure of Atom)
per project Condition 7/8: no invented facts, only pedagogy/wording is
adapted for student-friendliness. Every numeric example is taken directly
from NCERT in-chapter or end-of-chapter problems (2.1–2.67), never invented.

Usage:
    cd backend
    python3 scripts/seed_manual_lesson_content.py --dry-run
    python3 scripts/seed_manual_lesson_content.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.lesson_cache_service import make_lesson_cache_key, store_lesson_cache, get_cached_lesson  # noqa: E402

GRADE = "Grade 11"
SUBJECT = "Chemistry"
CHAPTER = "Structure of Atom"
MODE = "CBSE"
BOARD = "CBSE"

LESSONS: dict[str, str] = {}

# ─────────────────────────────────────────────────────────────────────────────
LESSONS["Concept introduction"] = """# Concept Introduction: Structure of Atom

## What you will learn
In this lesson you will learn how scientists discovered that atoms are not
indivisible, how the electron, proton and neutron were discovered, and how
this led to the first atomic models (Thomson and Rutherford). This is the
foundation for everything else in this chapter — the Bohr model, quantum
numbers, and electronic configuration.

## Simple explanation
Atoms were once thought to be the smallest, indivisible particles of matter
— this was John Dalton's atomic theory (1808). But towards the end of the
nineteenth century, scientists discovered that atoms are actually made of
even smaller particles: electrons, protons and neutrons. This discovery came
mainly from experiments on electrical discharge through gases (cathode-ray
tubes), and later from experiments that measured the mass and charge of
these particles precisely.

## Step-by-step breakdown
- **Cathode-ray discharge tube experiments**: When a high voltage is applied
  across two electrodes sealed in a partially evacuated glass tube, a stream
  of particles flows from the cathode (negative electrode) to the anode
  (positive electrode). These particles travel in straight lines, are
  deflected by electric and magnetic fields as negatively charged particles,
  and behave the same way regardless of the gas used or the metal of the
  electrodes. This proved that **electrons** are a basic constituent of all
  atoms.
- **Measuring the electron**: J.J. Thomson (1897) measured the charge-to-mass
  ratio of the electron (e/m_e = 1.758820 × 10^11 C/kg) using a cathode-ray
  tube with perpendicular electric and magnetic fields. R.A. Millikan's oil
  drop experiment (1906–14) then measured the actual charge on the electron:
  −1.602176 × 10^−19 C. Combining these two results gives the mass of the
  electron: 9.1094 × 10^−31 kg.
- **Discovery of the proton and neutron**: Canal rays (positively charged
  particles) led to the discovery of the proton (characterised in 1919),
  the lightest positive ion, obtained from hydrogen. In 1932, Chadwick
  discovered the neutron by bombarding a thin sheet of beryllium with
  alpha particles.
- **Why this matters**: Once these three particles were known, scientists
  needed a model to explain how they are arranged inside the atom — this
  is what Thomson's model and later Rutherford's model attempted to do (you
  will study these in the next section, "Core explanation").

## Worked example
Question: Calculate the number of protons, neutrons and electrons in
Br-80 (bromine-80), given atomic number Z = 35 and mass number A = 80.
(NCERT Problem 2.1)

Solution:
- Step 1: The species is a neutral atom, so number of protons = number of
  electrons = Z = 35.
- Step 2: Number of neutrons = A − Z = 80 − 35 = 45.
- Final answer: 35 protons, 35 electrons, 45 neutrons.

## Common mistake
A common mistake is confusing atomic number (Z, the number of protons) with
mass number (A, protons + neutrons). Remember: Z never changes for a given
element, but A can vary between isotopes of the same element. Another
common mistake is assuming a species is a neutral atom without checking
whether the number of protons equals the number of electrons — if they are
not equal, the species is actually an ion, not a neutral atom.

## Quick check question
Question: An atom has 6 protons and 6 neutrons. What is its mass number,
and what is its atomic number?
Answer: Atomic number Z = 6 (number of protons). Mass number A = protons +
neutrons = 6 + 6 = 12.
Explanation: Atomic number always equals the proton count, and mass number
is the sum of protons and neutrons — this atom is carbon-12.

## Summary
- Atoms are made of three sub-atomic particles: electrons, protons and
  neutrons — discovered through cathode-ray, Millikan oil-drop, and
  Chadwick's neutron-discovery experiments.
- Atomic number (Z) = number of protons = number of electrons in a
  neutral atom.
- Mass number (A) = number of protons + number of neutrons.
- These discoveries set the stage for the atomic models covered next:
  Thomson's model and Rutherford's nuclear model.
"""

# ─────────────────────────────────────────────────────────────────────────────
LESSONS["Core explanation"] = """# Core Explanation: Atomic Models and the Path to Quantum Theory

## What you will learn
You will learn how the Thomson and Rutherford atomic models were proposed
and why Rutherford's model — although a major improvement — could not
explain the stability of the atom. You will also learn the key ideas that
led to the Bohr model: electromagnetic radiation, Planck's quantum theory,
and atomic line spectra.

## Simple explanation
J.J. Thomson (1898) proposed that an atom is a sphere of positive charge
with electrons embedded in it, like seeds in a watermelon — this is called
the "plum pudding" model. It explained why atoms are electrically neutral,
but Rutherford's famous gold-foil experiment (alpha-particle scattering)
proved it wrong. Rutherford's new "nuclear model" said that almost all of
an atom's mass and its entire positive charge are concentrated in a tiny
central nucleus, with electrons orbiting around it — but this model, too,
had a serious flaw: classical physics predicts that an orbiting electron
should lose energy and spiral into the nucleus almost instantly, which does
not happen. This contradiction is what eventually led Niels Bohr to propose
a new model based on quantised (fixed) energy levels.

## Step-by-step breakdown
- **Thomson's model (1898)**: Positive charge spread uniformly through a
  sphere (radius ~10^−10 m), with electrons embedded in it. Explained
  overall neutrality, but could not explain later scattering experiments.
- **Rutherford's alpha-particle scattering experiment**: A beam of
  alpha-particles was directed at a thin gold foil. Result: most particles
  passed straight through; a few were deflected at small angles; about
  1 in 20,000 bounced back almost 180 degrees. Rutherford concluded: (1)
  most of the atom is empty space; (2) a tiny, dense, positively charged
  nucleus exists at the centre; (3) electrons revolve around this nucleus
  in circular orbits, similar to planets orbiting the sun.
- **Drawback of Rutherford's model**: Classical electromagnetic theory says
  that an accelerating charged particle (like an orbiting electron) must
  radiate energy continuously. If this happened, the electron would lose
  energy, spiral inward, and crash into the nucleus within about 10^−8
  seconds. Since atoms are stable, this prediction is clearly wrong —
  Rutherford's model could not explain atomic stability, and it said
  nothing about how electrons are distributed or what their energies are.
- **Electromagnetic radiation**: Related by c = v × lambda, where c is the
  speed of light (~3.0 × 10^8 m/s), v is frequency, and lambda is
  wavelength.
- **Planck's quantum theory (1900)**: Energy is absorbed or emitted only in
  discrete packets called quanta, not continuously. E = h × v, where h
  (Planck's constant) = 6.626 × 10^−34 J s.
- **Atomic (line) spectra**: When atoms are excited (for example, by
  electric discharge), they emit light only at specific wavelengths, not a
  continuous range — producing a "line spectrum" unique to each element.
  This observation could not be explained by classical physics and was the
  second major clue Bohr used to build his model.

## Worked example
Question: What is the frequency of yellow light with wavelength 5800
angstrom? (Based on NCERT Problem 2.5 style)

Solution:
- Step 1: Convert wavelength to metres: 5800 angstrom = 5800 × 10^−10 m.
- Step 2: Use c = v × lambda, rearranged to v = c / lambda.
- Step 3: v = (3.0 × 10^8 m/s) / (5800 × 10^−10 m) is approximately 5.17 × 10^14 Hz.
- Final answer: The frequency is approximately 5.17 × 10^14 Hz.

## Common mistake
A common mistake is thinking Rutherford's model fully explains atomic
structure. It correctly located the nucleus but could not explain why
electrons do not spiral into it, and said nothing about electron
arrangement or energies — these gaps are exactly what the Bohr model
(next section) was built to fix.

## Quick check question
Question: Why can Rutherford's nuclear model not explain the stability of
the atom?
Answer: Because an orbiting (accelerating) electron should, according to
classical electromagnetic theory, continuously radiate energy and spiral
into the nucleus within about 10^-8 seconds — but atoms are observed to be
stable, so this prediction contradicts reality.
Explanation: This contradiction between classical physics and observed
atomic stability was one of the two major problems (along with atomic line
spectra) that motivated Bohr's new model.

## Summary
- Thomson's model: positive sphere with embedded electrons; explained
  neutrality but not scattering results.
- Rutherford's model: tiny dense positively-charged nucleus with electrons
  orbiting it, based on the alpha-particle scattering experiment.
- Rutherford's model could not explain atomic stability or electron
  arrangement/energies.
- Electromagnetic radiation (c = v x lambda) and Planck's quantum theory
  (E = h x v), together with atomic line spectra, provided the two key
  clues that led to the Bohr model.
"""

# -----------------------------------------------------------------------------
LESSONS["Worked examples"] = """# Worked Examples: Structure of Atom

## What you will learn
You will practice the core numerical skills of this chapter: finding
protons/neutrons/electrons from atomic number and mass number, working
with isotopes, calculating photon energy and frequency, and calculating
Bohr-model orbit energies for hydrogen and hydrogen-like species.

## Simple explanation
Every calculation in this chapter builds on a small set of formulas: Z =
protons = electrons (neutral atom), A = protons + neutrons, c = v x
lambda, E = h x v, and the Bohr energy formula E_n = -R_H x (Z^2/n^2). Once
you know which formula applies, these problems become straightforward
substitution exercises.

## Step-by-step breakdown
- Identify what is given (Z, A, wavelength, frequency, n, etc.) and what is
  being asked.
- Choose the correct formula: particle counts use Z and A; radiation
  problems use c = v x lambda or E = h x v; Bohr-model problems use
  E_n = -R_H x (Z^2/n^2) and r_n = a0 x (n^2/Z).
- Substitute values carefully, keeping track of units (convert angstrom to
  metres, nm to metres, etc. before calculating).
- State the final answer with correct units and, where relevant, its
  physical meaning.

## Worked example
Question: The number of electrons, protons and neutrons in a species are
18, 16 and 16 respectively. Assign the proper symbol to the species.
(NCERT Problem 2.2)

Solution:
- Step 1: Atomic number = number of protons = 16, so the element is
  sulphur (S).
- Step 2: Mass number = protons + neutrons = 16 + 16 = 32.
- Step 3: The species is not neutral, since protons (16) do not equal
  electrons (18). It is an anion with charge = 18 - 16 = 2 units negative.
- Final answer: The species is S^2- (sulphide ion), mass number 32,
  atomic number 16.

## Common mistake
A common mistake is writing the atomic-mass-number notation (superscript A,
subscript Z) without first checking whether the species is a neutral atom
or an ion. Always compare protons and electrons first: if they are equal,
it is a neutral atom (equation Z = protons = electrons applies directly);
if not, it is an ion, and you must state whether it is a cation (fewer
electrons than protons) or anion (more electrons than protons).

## Quick check question
Question: Calculate the energy of one photon of radiation whose frequency
is 5 x 10^14 Hz. (Based on NCERT Problem 2.6)
Answer: E = h x v = (6.626 x 10^-34 J s) x (5 x 10^14 s^-1) is approximately
3.313 x 10^-19 J.
Explanation: Planck's equation E = h x v directly gives the energy of a
single photon once frequency is known; no other information is needed.

## Summary
- Particle-count problems use Z = protons = electrons (neutral) and
  A = protons + neutrons.
- Always check whether a species is neutral or an ion before assigning a
  symbol or charge.
- Radiation-energy problems use E = h x v, and wavelength/frequency
  problems use c = v x lambda.
- Bohr-model problems for hydrogen-like species use E_n = -R_H x (Z^2/n^2)
  and r_n = a0 x (n^2/Z).
"""

# -----------------------------------------------------------------------------
LESSONS["Exam-style problems"] = """# Exam-Style Problems: Structure of Atom

## What you will learn
You will practice CBSE/NCERT exam-style questions covering sub-atomic
particles, atomic models, quantum theory, the Bohr model, and quantum
numbers - the same range of question types that appear in board exams for
this chapter.

## Simple explanation
Exam questions on this chapter typically fall into a few categories:
definition/concept questions (e.g. "What is an isotope?"), calculation
questions (particle counts, frequency/wavelength, Bohr energies), and
short-answer questions asking you to explain a model's postulates or
limitations. Practicing a mix of these prepares you for the actual exam.

## Step-by-step breakdown
- Concept questions: define atomic number, mass number, isotopes, isobars,
  quantum numbers, orbitals, in your own words with an example each.
- Numerical questions: practice particle-count, radiation, and Bohr-model
  calculations using the formulas from the "Worked examples" section.
- Explain-the-model questions: be ready to state Rutherford's conclusions
  from the alpha-scattering experiment, and Bohr's four postulates, in a
  clear, ordered list.
- Compare/contrast questions: be ready to compare Thomson, Rutherford, and
  Bohr models side by side (main idea, evidence, limitation).

## Worked example
Question: How many neutrons and protons are there in the nuclei of
Mg-24 (magnesium-24, atomic number 12)? (Based on NCERT Problem 2.3 style)

Solution:
- Step 1: Atomic number Z = 12, so protons = 12.
- Step 2: Mass number A = 24, so neutrons = A - Z = 24 - 12 = 12.
- Final answer: 12 protons and 12 neutrons.

## Common mistake
A common mistake in exams is giving an incomplete answer to "explain
Rutherford's model" by only mentioning the nucleus, without also stating
the drawback (it could not explain atomic stability). Full marks usually
require both the model's claims AND its limitation.

## Quick check question
Question: State one similarity and one difference between isotopes and
isobars.
Answer: Similarity: both are pairs/sets of atoms that differ in some way
while sharing another property. Difference: isotopes have the same atomic
number (same element) but different mass numbers, while isobars have the
same mass number but different atomic numbers (different elements).
Explanation: Isotopes example: carbon-12 and carbon-14 (both carbon, Z=6).
Isobars example: carbon-14 and nitrogen-14 (different elements, same mass
number 14).

## Summary
- Practice a mix of concept, numerical, and explain-the-model questions for
  this chapter.
- Always state both the claims and the limitations of a model when asked
  to explain it.
- Isotopes: same Z, different A. Isobars: same A, different Z.
- Review the worked-example formulas before attempting numerical exam
  questions.
"""

# -----------------------------------------------------------------------------
LESSONS["Revision and recap"] = """# Revision and Recap: Structure of Atom

## What you will learn
This section summarises the entire chapter: the discovery of sub-atomic
particles, the Thomson and Rutherford models, the developments leading to
the Bohr model, the Bohr model itself and its limitations, and the modern
quantum-mechanical model with quantum numbers and electronic configuration.

## Simple explanation
The chapter tells one connected story: atoms were once thought indivisible,
but experiments revealed electrons, protons and neutrons inside them. This
led to atomic models that tried to explain how these particles are
arranged - first Thomson's, then Rutherford's, then Bohr's, and finally the
modern quantum-mechanical model. Each model fixed a problem with the
previous one, but also had its own new limitation, until quantum mechanics
gave the most complete (though mathematically complex) picture we use
today.

## Step-by-step breakdown
- **Sub-atomic particles**: electron (Thomson e/m ratio, Millikan charge),
  proton (from canal rays), neutron (Chadwick, 1932).
- **Thomson model**: positive sphere with embedded electrons - explained
  neutrality, not scattering.
- **Rutherford model**: nucleus + orbiting electrons, from the alpha-
  scattering experiment - explained the nucleus, not stability.
- **Bohr model**: electrons move in fixed circular orbits (stationary
  states) with quantised energy and angular momentum; explains the
  hydrogen line spectrum well, but cannot explain multi-electron atom
  spectra or chemical bonding.
- **Quantum-mechanical model**: describes electrons using orbitals (three-
  dimensional probability regions from the Schrodinger equation), not
  fixed orbits. Each electron is described by four quantum numbers: n
  (shell/size), l (subshell/shape), m_l (orientation), m_s (spin).
- **Filling of orbitals**: governed by the Aufbau principle (fill lowest
  energy first, using the n+l rule), the Pauli exclusion principle (no two
  electrons in an atom share all four quantum numbers), and Hund's rule
  (electrons fill degenerate orbitals singly before pairing).

## Worked example
Question: Write the electronic configuration of iron (Fe, Z = 26) and give
its number of unpaired electrons.

Solution:
- Step 1: Fill orbitals in Aufbau order: 1s2 2s2 2p6 3s2 3p6 4s2 3d6.
- Step 2: Total electrons check: 2+2+6+2+6+2+6 = 26. Correct.
- Step 3: In the 3d6 subshell (5 orbitals), by Hund's rule, the first 5
  electrons fill each orbital singly, and the 6th electron must pair up
  with one of them.
- Final answer: Fe configuration is 1s2 2s2 2p6 3s2 3p6 4s2 3d6, with 4
  unpaired electrons (4 of the 5 d-orbitals have one unpaired electron
  each; one orbital has a pair).

## Common mistake
A common mistake is describing electrons as orbiting the nucleus in fixed
circular paths as a final, modern fact. This is only true for the Bohr
model. In the modern quantum-mechanical model, electrons occupy orbitals -
three-dimensional regions of space where there is a high probability of
finding the electron - not fixed circular tracks. Another common mistake
is forgetting exceptions like chromium (3d5 4s1, not 3d4 4s2) and copper
(3d10 4s1, not 3d9 4s2), which occur because half-filled and fully-filled
subshells have extra stability.

## Quick check question
Question: Write the increasing order of energies of orbitals up to 4s
according to the Aufbau principle.
Answer: 1s < 2s < 2p < 3s < 3p < 4s.
Explanation: The Aufbau principle fills orbitals in order of increasing
(n + l) value; when two orbitals have the same (n + l), the one with lower
n is filled first. This is why 4s (n+l = 4+0 = 4) is filled before 3d
(n+l = 3+2 = 5).

## Summary
- This chapter traces the atom from Dalton's indivisible particle, through
  the discovery of the electron, proton and neutron, to the Thomson,
  Rutherford, Bohr, and quantum-mechanical models.
- Each model solved a problem with the previous one: Rutherford fixed
  Thomson's lack of a nucleus; Bohr fixed Rutherford's stability problem;
  quantum mechanics fixed Bohr's inability to explain multi-electron atoms.
- Electrons are described by four quantum numbers (n, l, m_l, m_s) and fill
  orbitals according to the Aufbau principle, Pauli exclusion principle,
  and Hund's rule.
- Half-filled and fully-filled subshells (like Cr's 3d5 and Cu's 3d10) have
  extra stability due to symmetrical electron distribution and exchange
  energy.
"""


# ── Seeding logic ──────────────────────────────────────────────────────────────

def seed_all(dry_run: bool, force: bool) -> None:
    print()
    print("  Seed Manual Lesson Content — Track A Remediation")
    print(f"  Chapter: {GRADE} / {SUBJECT} / {CHAPTER}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE WRITE'}")
    print(f"  Steps to seed: {len(LESSONS)}")
    print()

    for step_title, content in LESSONS.items():
        cache_key = make_lesson_cache_key(
            board=BOARD, grade=GRADE, subject=SUBJECT, chapter=CHAPTER,
            mode=MODE, step_title=step_title, teacher_persona="",
        )
        existing = get_cached_lesson(cache_key, grade=GRADE)
        word_count = len(content.split())

        print(f"  [{step_title}] {word_count} words, cache_key={cache_key[:16]}...")

        if existing and not force:
            print(f"    -> Already cached. Skipping (use --force to overwrite).")
            continue

        if dry_run:
            print(f"    -> [DRY RUN] Would store {len(content)} chars as source_type=MANUAL.")
            continue

        store_lesson_cache(
            cache_key=cache_key,
            lesson_content=content,
            source_type="MANUAL",
            board=BOARD, grade=GRADE, subject=SUBJECT, chapter=CHAPTER,
            mode=MODE, step_title=step_title, teacher_persona="",
            practice_questions=[],
        )
        print(f"    -> Stored ({len(content)} chars).")

    print()
    print("  Done. Next step: re-run the Tier A audit to confirm 0 critical findings:")
    print('    python3 scripts/audit_chapter_boundary.py --grade "Grade 11" '
          '--subject Chemistry --chapter "Structure of Atom"')
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed manually-authored, NCERT-grounded lesson content into lesson_cache"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be written without writing")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing cached lessons for these steps")
    args = parser.parse_args()
    seed_all(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
