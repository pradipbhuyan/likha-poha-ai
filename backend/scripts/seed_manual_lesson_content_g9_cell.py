#!/usr/bin/env python3
"""
Seed Manual Lesson Content — Grade 9 Science, Chapter 2:
Cell: The Building Block of Life (Track A remediation, pilot #2)
==================================================================
See docs/LESSON_CONTENT_QUALITY_REVIEW_PLAN.md for full design context.

Content grounded word-by-word in iesc102.pdf (NCERT Grade 9 Science,
Chapter 2). Replaces the previous content which over-focused on
mitosis/meiosis (4 of 5 steps) and contained one fabricated numeric
worked example not present in the source text.

Usage:
    cd backend
    python3 scripts/seed_manual_lesson_content_g9_cell.py --dry-run
    python3 scripts/seed_manual_lesson_content_g9_cell.py --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.lesson_cache_service import make_lesson_cache_key, store_lesson_cache, get_cached_lesson  # noqa: E402

GRADE = "Grade 9"
SUBJECT = "Science"
CHAPTER = "Chapter 2: Cell: The Building Block of Life"
MODE = "CBSE"
BOARD = "CBSE"

LESSONS: dict[str, str] = {}

# -----------------------------------------------------------------------------
LESSONS["Concept introduction"] = """# Concept Introduction: Cell - The Building Block of Life

## What you will learn
You will learn what a cell is, how scientists study cells using microscopes,
and why the cell is called the basic structural and functional unit of all
living organisms.

## Simple explanation
All living organisms are made up of cells. Some organisms, such as bacteria
or yeast, consist of only one cell (unicellular), while others like plants,
fish, birds, or humans are made up of millions of cells (multicellular)
working together. A cell is usually too small to be seen by the unaided
eye - this is why microscopes are essential tools for studying cells.

## Step-by-step breakdown
- **Limit of resolution of the human eye**: when viewed from about 25 cm
  (the near point of the human eye), two points separated by about 0.1 mm
  can be seen as distinct; closer than that, they appear as a single point.
  This 0.1 mm value is called the limit of resolution of the human eye.
- **Why we need microscopes**: since a cell is much smaller than this
  limit of resolution, cell biologists use microscopes - a convex lens or
  combination of lenses (an objective lens and an eyepiece) - to magnify
  and resolve cell structures.
- **Robert Hooke (1665)**: the first person to observe a cell, using a
  self-designed microscope capable of about 200-300X magnification. While
  examining a thin slice of cork, he observed small box-like compartments
  and named them 'cells'.
- **Light microscopes vs electron microscopes**: light microscopes (used in
  school laboratories) use visible light and different objective lenses
  (e.g. 10X, 40X) for magnification and resolution. Electron microscopes use
  a beam of electrons instead of light, allowing scientists to see cell
  structure at the nanometre scale with much greater clarity.
- **From cells to tissues, organs, and organ systems**: a group of similar
  cells performing similar functions forms tissues; different tissues
  organise to form an organ; several organs work together to form an organ
  system (e.g. nasal pores, nasal cavity, trachea, and lungs form the
  respiratory system). Even so, the cell remains the fundamental unit of
  structure and function in all living organisms.

## Worked example
Question: In Activity 2.1, a student places a transparent ruler with
millimetre markings on the microscope stage and finds the diameter of the
circular field of view is 5 mm. After removing the ruler and placing an
onion peel slide, the student counts 25 cells along the diameter of the
field of view. Estimate the real size of one onion peel cell.

Solution:
- Step 1: Convert the field diameter to micrometres: 5 mm = 5 x 1000 =
  5000 micrometre (since 1 mm = 1000 micrometre).
- Step 2: Use the formula: estimated cell size = diameter of visible field
  (in micrometre) / number of cells along the diameter.
- Step 3: Estimated size = 5000 micrometre / 25 = 200 micrometre.
- Final answer: each onion peel cell is approximately 200 micrometre in
  size.

## Common mistake
A common mistake is forgetting to convert millimetres to micrometres
before dividing by the number of cells - always convert units first
(1 mm = 1000 micrometre) so the final answer is in the correct unit.

## Quick check question
Question: What is the limit of resolution of the human eye, and why do we
need microscopes to study cells?
Answer: The limit of resolution of the human eye is about 0.1 mm - two
points closer together than this appear as a single point.
Explanation: Since most cells are far smaller than 0.1 mm, they cannot be
seen with the unaided eye. Microscopes (light or electron) magnify and
resolve structures smaller than this limit, which is why they are
essential tools for studying cells.

## Summary
- All living organisms are made of cells; organisms can be unicellular or
  multicellular.
- The limit of resolution of the human eye is about 0.1 mm; cells are
  usually smaller than this, so microscopes are needed to study them.
- Robert Hooke first observed and named cells in 1665 using a self-built
  microscope.
- Light microscopes use visible light; electron microscopes use electron
  beams for much higher magnification and resolution.
- Even when organised into tissues, organs, and organ systems, the cell
  remains the basic unit of structure and function in living organisms.
"""

# -----------------------------------------------------------------------------
LESSONS["Core explanation"] = """# Core Explanation: The Cell Membrane, Cell Wall, and Osmosis

## What you will learn
You will learn about the structure and function of the cell membrane and
cell wall, and understand osmosis - the process by which water moves
across a selectively permeable membrane.

## Simple explanation
The cell membrane is a thin boundary that surrounds every cell, protects
its contents, and controls what substances can enter or leave - this is
why it is called selectively permeable. Some cells (plants, fungi,
bacteria) have an extra rigid layer outside the cell membrane called the
cell wall, which gives them structural support. Water moves across the
cell membrane by a special kind of diffusion called osmosis.

## Step-by-step breakdown
- **Cell membrane (plasma membrane)**: a thin boundary, about 7 to 10
  nanometres thick, made of lipids and proteins. The fluid-mosaic model
  describes its structure: a lipid bilayer (two layers of fat molecules,
  water-attracting heads outward and water-repelling tails inward) with
  proteins embedded in it. The molecules can move sideways, flip, and
  rotate - so the membrane is called 'fluid'. Because the proteins are
  arranged like tiles in a mosaic, the model is called the 'fluid-mosaic'
  model.
- **Diffusion vs osmosis**: diffusion is the net movement of particles
  from a higher to a lower concentration (occurs even without a membrane).
  Osmosis is specifically the diffusion of water across a selectively
  permeable membrane, from a region with more water (dilute/hypotonic) to
  a region with less water (concentrated/hypertonic), until concentrations
  become equal.
- **Isotonic, hypotonic, hypertonic solutions**: if the solute
  concentration outside a cell equals that inside, the solution is
  isotonic. If outside concentration is lower than inside, it is
  hypotonic (water moves into the cell). If outside concentration is
  higher than inside, it is hypertonic (water moves out of the cell).
- **Cell wall**: found in plants, fungi, and bacteria, outside the cell
  membrane. It is rigid but still permeable (water and dissolved minerals
  can pass through). The plant cell wall is made mainly of cellulose. It
  gives plants the structural support to withstand wind, rain, and helps
  leaves and flowers stay firm and upright, since plants cannot move to
  avoid such stresses.
- **Why plant cells don't shrink but animal cells do**: when a plant cell
  is placed in a concentrated sugar solution, it loses water by osmosis,
  but its rigid cell wall keeps its overall shape - only the inner
  content (cell membrane) shrinks away from the wall. Animal cells like
  cheek cells have no cell wall, so they shrink fully when they lose
  water.

## Worked example
Question (NCERT Activity 2.2): A potato is cut into two equal pieces. One
piece is placed in Beaker A with plain water, the other in Beaker B with
20 per cent salt solution. After an hour, the piece in Beaker A has
swelled and gained weight, while the piece in Beaker B has shrunk and
lost weight. Explain why.

Solution:
- Step 1: Identify the process involved - osmosis, since a selectively
  permeable cell membrane is involved and water is moving, not the
  solute.
- Step 2: In Beaker A (plain water), the water outside the potato cells
  has a lower solute concentration than inside the cells, so water moves
  INTO the cells by osmosis - the potato piece swells and gains weight.
- Step 3: In Beaker B (20% salt solution), the water outside has a higher
  solute concentration than inside the cells, so water moves OUT of the
  cells by osmosis - the potato piece shrinks and loses weight.
- Final answer: Beaker A's potato swells because water moves in
  (hypotonic external solution); Beaker B's potato shrinks because water
  moves out (hypertonic external solution).

## Common mistake
A common mistake is thinking that salt or sugar molecules move across the
membrane to cause the swelling/shrinking. In osmosis, it is WATER that
moves, not the solute - the cell membrane allows water through but not
the sugar or salt molecules.

## Quick check question
Question: A Rhoeo leaf peel is placed in a 20% sugar solution. After some
time, would you expect the outer boundary of the plant cell to shrink, or
just the inner content to pull away from the boundary? Why?
Answer: Only the inner content (cell membrane and cytoplasm) shrinks and
pulls away from the outer boundary; the overall cell boundary stays the
same size.
Explanation: The rigid cell wall maintains the cell's original shape even
as the cell loses water by osmosis - this is why plant cells do not
shrink in size the way animal cells (like cheek cells, which have no cell
wall) do.

## Summary
- The cell membrane is a thin, selectively permeable boundary made of a
  lipid bilayer with embedded proteins (fluid-mosaic model).
- Diffusion is movement of particles from high to low concentration;
  osmosis is specifically the diffusion of water across a selectively
  permeable membrane.
- Solutions can be isotonic, hypotonic, or hypertonic relative to a cell,
  determining whether water moves in, out, or not at all.
- The cell wall (in plants, fungi, bacteria) is a rigid but permeable
  layer outside the cell membrane, made mainly of cellulose in plants,
  and keeps the cell's shape even during osmotic water loss.
- Animal cells lack a cell wall and can change shape or shrink more
  easily than plant cells.
"""

# -----------------------------------------------------------------------------
LESSONS["Worked examples"] = """# Worked Examples: Cell Organelles and Their Functions

## What you will learn
You will learn about the individual organelles found inside a eukaryotic
cell - the nucleus, ribosomes, endoplasmic reticulum, Golgi apparatus,
lysosomes, mitochondria, plastids, and vacuoles - and practice identifying
them from their functions.

## Simple explanation
A eukaryotic cell is like a tiny living factory, where each organelle does
a specific job: some make proteins, some package and ship materials, some
produce energy, and some store food or waste. Learning each organelle's
job helps you understand how a cell works as a coordinated system.

## Step-by-step breakdown
- **Nucleus**: has a double-layered nuclear membrane with pores for
  material exchange with the cytoplasm; contains the nucleolus (where
  ribosomal subunits are made) and chromatin/chromosomes (DNA + proteins,
  carrying genetic information).
- **Ribosomes**: tiny structures, free in the cytoplasm or attached to
  the endoplasmic reticulum; they are the sites of protein synthesis.
- **Endoplasmic Reticulum (ER)**: a network spreading through the
  cytoplasm, continuous with the nuclear membrane. Rough ER (RER) has
  ribosomes attached and is mainly involved in protein synthesis and
  secretion; Smooth ER (SER) has no ribosomes and is involved in
  synthesis and storage of fats and hormones.
- **Golgi apparatus**: stacks of flattened, sac-like structures; acts
  like the cell's post office - it modifies, sorts, and packages proteins
  and lipids into vesicles for transport, secretion, or lysosome
  formation.
- **Lysosomes**: single membrane-bound sacs filled with enzymes that
  break down unwanted proteins, carbohydrates, fats, and damaged parts of
  the cell, keeping it clean and healthy.
- **Mitochondria**: the 'powerhouse of the cell' - surrounded by two
  membranes (outer smooth, inner folded into cristae); site of cellular
  respiration, which breaks down glucose to release energy stored as ATP
  (Adenosine Triphosphate).
- **Plastids**: found in plant cells - chloroplasts (contain chlorophyll,
  site of photosynthesis), chromoplasts (contain yellow/orange/red
  pigments, give colour to flowers/fruits), and leucoplasts (colourless,
  store starch/oils/proteins, e.g. in potato).
- **Vacuoles**: in mature plant cells, usually one large central vacuole
  filled with cell sap (water, minerals, sugars, waste) that helps
  maintain cell firmness (turgidity); animal cell vacuoles are smaller and
  used for temporary storage.

## Worked example
Question (based on NCERT end-of-chapter Q3 style): Match each organelle
with its function - (a) Nucleus, (b) Mitochondria, (c) Golgi apparatus -
to: (i) controls all activities of the cell, (ii) site of cellular
respiration, (iii) packs and stores materials received from the ER.

Solution:
- Step 1: Nucleus contains DNA and directs cell activities -> matches
  (i) controls all activities of the cell.
- Step 2: Mitochondria break down glucose to release energy through
  cellular respiration -> matches (ii) site of cellular respiration.
- Step 3: Golgi apparatus modifies, sorts, and packages materials
  received from the ER -> matches (iii) packs and stores materials
  received from the ER.
- Final answer: (a)-(i), (b)-(ii), (c)-(iii).

## Common mistake
A common mistake is confusing the Golgi apparatus with the endoplasmic
reticulum - remember, the ER is the 'manufacturing factory' where
proteins/lipids are made, while the Golgi apparatus is the 'packaging and
shipping centre' that processes what the ER produces.

## Quick check question
Question: Which organelle is called the 'powerhouse of the cell', and
why?
Answer: The mitochondrion.
Explanation: Mitochondria carry out cellular respiration, breaking down
glucose and other molecules to release energy, which is stored as ATP
and used for most cellular activities - hence the name 'powerhouse'.

## Summary
- The nucleus houses genetic material (DNA/chromosomes) and controls cell
  activities.
- Ribosomes synthesise proteins; Rough ER has ribosomes and helps make/
  secrete proteins; Smooth ER makes/stores lipids and hormones.
- The Golgi apparatus packages and ships materials; lysosomes break down
  waste and damaged parts.
- Mitochondria produce energy (ATP) via cellular respiration.
- Plastids (chloroplast, chromoplast, leucoplast) are plant-specific
  organelles for photosynthesis, pigmentation, and food storage.
- Vacuoles store water, minerals, sugars, and waste, and help maintain
  cell firmness in plants.
"""

# -----------------------------------------------------------------------------
LESSONS["Exam-style problems"] = """# Exam-Style Problems: Prokaryotic vs Eukaryotic Cells, Cell Division, and Cell Theory

## What you will learn
You will practice NCERT exam-style questions covering the differences
between prokaryotic and eukaryotic cells, the basic concept of cell
division (mitosis and meiosis), and the classical Cell Theory.

## Simple explanation
Cells can be grouped into two broad types based on whether they have a
well-defined nucleus: prokaryotic cells (like bacteria) do not; eukaryotic
cells (like plant and animal cells) do. All cells arise from pre-existing
cells through cell division, which happens in two main ways depending on
the purpose - growth/repair (mitosis) or reproduction (meiosis). The Cell
Theory summarises these ideas into three unifying principles of biology.

## Step-by-step breakdown
- **Prokaryotic cells**: lack a well-defined nucleus and membrane-bound
  organelles; genetic material lies in a region called the nucleoid; most
  cellular activities happen directly in the cytoplasm; usually
  unicellular; typical diameter 1 to 10 micrometre.
- **Eukaryotic cells**: have a well-defined, membrane-bound nucleus and
  several membrane-bound organelles; can be unicellular or multicellular;
  typical diameter 10 to 100 micrometre.
- **Cell division - basic concept**: cell division is the process by
  which new cells form from pre-existing cells, allowing growth, tissue
  repair, and reproduction.
  - Mitosis: produces two genetically identical daughter cells from one
    parent cell, each with the same DNA and chromosome number as the
    parent - important for growth, repair, and asexual reproduction.
  - Meiosis: occurs only in reproductive cells (testes/ovaries in
    animals, anthers/ovaries in plants); the parent cell divides twice to
    form four daughter cells (gametes), each with half the chromosome
    number of the parent - important for sexual reproduction and genetic
    diversity.
- **Cell Theory**: Matthias Schleiden (1838) showed all plants are made
  of cells; Theodor Schwann (1839) showed all animals are made of cells;
  Rudolf Virchow (1855) added that new cells form only from pre-existing
  cells. Together: (1) all living organisms are made up of one or more
  cells, (2) the cell is the basic unit of structure and function in
  living beings, (3) all cells arise from pre-existing cells.
- **Cancer and contact inhibition**: normal animal cells usually stop
  dividing when they touch neighbouring cells (contact inhibition);
  cancer cells lose this control and keep dividing uncontrollably, forming
  tumours. Plant cells, due to their rigid cell walls, do not show contact
  inhibition and grow differently.

## Worked example
Question (NCERT end-of-chapter style): Indicate the presence or absence
of the following structures in bacterial and animal cells: chromosome,
nucleus, mitochondria, Golgi complex, chromoplasts.

Solution:
- Step 1: Bacterial cells - chromosome: present (as circular DNA in the
  nucleoid, not membrane-bound); nucleus: absent (no membrane-bound
  nucleus); mitochondria: absent; Golgi complex: absent; chromoplasts:
  absent (chromoplasts are plant-specific plastids).
- Step 2: Animal cells - chromosome: present (inside a membrane-bound
  nucleus); nucleus: present; mitochondria: present; Golgi complex:
  present; chromoplasts: absent (plastids are found only in plant cells).
- Final answer: Bacterial cells have genetic material (as a nucleoid, not
  true chromosomes/nucleus) and lack membrane-bound organelles; animal
  cells have a true nucleus and membrane-bound organelles but, like
  bacteria, never have chromoplasts since plastids are plant-specific.

## Common mistake
A common mistake is saying bacterial cells have "no genetic material" -
they do have DNA (in the nucleoid), just not enclosed by a nuclear
membrane. Another common mistake is assuming all cells have plastids -
plastids (chloroplast, chromoplast, leucoplast) are found only in plant
cells, never in bacterial or animal cells.

## Quick check question
Question: What are the three postulates of the classical Cell Theory, and
which scientist contributed the idea that new cells arise only from
pre-existing cells?
Answer: (1) All living organisms are made up of one or more cells,
(2) the cell is the basic unit of structure and function in living
beings, (3) all cells arise from pre-existing cells.
Explanation: Schleiden (1838) and Schwann (1839) established that plants
and animals respectively are made of cells; Rudolf Virchow (1855) added
the third postulate that new cells form only from pre-existing cells,
completing the classical Cell Theory.

## Summary
- Prokaryotic cells lack a well-defined nucleus (genetic material in a
  nucleoid) and membrane-bound organelles; eukaryotic cells have both.
- Mitosis produces two identical daughter cells (growth/repair); meiosis
  produces four gametes with half the chromosome number (reproduction).
- The Cell Theory: all living things are made of cells; the cell is the
  basic unit of structure and function; all cells arise from pre-existing
  cells (Schleiden, Schwann, Virchow).
- Normal cells show contact inhibition and stop dividing when in contact
  with neighbours; cancer cells lose this control and form tumours.
"""

# -----------------------------------------------------------------------------
LESSONS["Revision and recap"] = """# Revision and Recap: Cell - The Building Block of Life

## What you will learn
This section reviews the entire chapter: how cells are studied, the
structure of the cell membrane and cell wall, the organelles inside a
eukaryotic cell, how cells grow and divide, and the Cell Theory.

## Simple explanation
This chapter tells one connected story: cells are the basic units of all
life, too small to see with the naked eye, so scientists use microscopes
to study them. Every cell is bounded by a selectively permeable cell
membrane (and, in plants/fungi/bacteria, also a rigid cell wall). Inside
eukaryotic cells, distinct organelles - nucleus, ER, Golgi apparatus,
lysosomes, mitochondria, plastids, and vacuoles - each perform a specific
job, working together like a coordinated factory. Cells grow and divide
by mitosis (growth/repair) or meiosis (reproduction), and the classical
Cell Theory unifies all of this into three simple principles.

## Step-by-step breakdown
- **How to study cells**: the human eye's limit of resolution is about
  0.1 mm; since cells are usually smaller, light and electron microscopes
  are used. Robert Hooke first observed and named cells in 1665.
- **Cell membrane and cell wall**: the cell membrane (plasma membrane) is
  a thin, selectively permeable boundary (fluid-mosaic model - lipid
  bilayer with embedded proteins); the cell wall is an additional rigid,
  permeable layer found in plants, fungi, and bacteria, made mainly of
  cellulose in plants.
- **Osmosis**: the diffusion of water across a selectively permeable
  membrane, from a hypotonic (more water) to a hypertonic (less water)
  region, demonstrated by the potato experiment (Activity 2.2).
- **Prokaryotic vs eukaryotic cells**: prokaryotic cells (e.g. bacteria)
  lack a well-defined nucleus (genetic material in a nucleoid) and
  membrane-bound organelles; eukaryotic cells (plant and animal cells)
  have both.
- **Cell organelles**: nucleus (genetic control centre), ribosomes
  (protein synthesis), ER (manufacturing - RER for proteins, SER for
  lipids/hormones), Golgi apparatus (packaging/shipping), lysosomes
  (clean-up/digestion), mitochondria (energy production via cellular
  respiration), plastids (chloroplast/chromoplast/leucoplast in plants),
  and vacuoles (storage, turgidity in plants).
- **Cell growth and division**: cell division allows growth, repair, and
  reproduction. Mitosis produces two identical daughter cells; meiosis
  produces four gametes with half the chromosome number. Cell division is
  controlled - normal cells show contact inhibition, while cancer cells
  divide uncontrollably, forming tumours.
- **Cell Theory**: Schleiden (plants, 1838), Schwann (animals, 1839), and
  Virchow (cells arise from pre-existing cells, 1855) together established
  that all living organisms are made of cells, the cell is the basic unit
  of structure and function, and all cells arise from pre-existing cells.

## Worked example
Question: A student compares onion peel cells and human cheek cells under
a microscope after placing both in a 20% sugar solution. Explain the
difference in what happens to each type of cell, linking your answer to
cell structure.

Solution:
- Step 1: Recall that onion peel cells (plant cells) have a rigid cell
  wall outside the cell membrane, while human cheek cells (animal cells)
  do not have a cell wall.
- Step 2: In the 20% sugar solution (hypertonic to the cell interior),
  both cell types lose water by osmosis.
- Step 3: In the onion peel cells, the rigid cell wall maintains the
  overall cell boundary/shape even as the cell membrane and cytoplasm
  shrink away from the wall.
- Step 4: In the cheek cells, with no cell wall to resist shrinkage, the
  whole cell shrinks considerably in size.
- Final answer: Onion peel cells keep their original outer shape (only
  the inner content shrinks) because of their rigid cell wall, while
  cheek cells shrink completely because they lack a cell wall.

## Common mistake
A common mistake is thinking prokaryotic cells have no DNA at all -
prokaryotic cells DO have DNA (as a single circular molecule in the
nucleoid region), they simply lack a membrane-bound nucleus to enclose
it, unlike eukaryotic cells.

## Quick check question
Question: Name any three cell organelles that are surrounded by their own
membrane (membrane-bound organelles), and state one function of each.
Answer: (1) Mitochondria - site of cellular respiration/energy (ATP)
production. (2) Endoplasmic reticulum - synthesis and transport of
proteins/lipids. (3) Lysosomes - breakdown of waste and damaged cell
parts (digestion/clean-up).
Explanation: Membrane-bound organelles are a key feature of eukaryotic
cells (absent in prokaryotic cells) - each is enclosed by its own
membrane, allowing it to carry out a specialised function separately from
the rest of the cytoplasm.

## Summary
- Cells are the basic structural and functional unit of all living
  organisms; microscopes are needed to study them due to their small size.
- The cell membrane (selectively permeable) and, in some cells, the cell
  wall (rigid but permeable) together control what enters/leaves a cell.
- Osmosis is the diffusion of water across a selectively permeable
  membrane, explaining swelling/shrinking behaviour in different
  solutions.
- Eukaryotic cells contain distinct membrane-bound organelles (nucleus,
  ER, Golgi apparatus, lysosomes, mitochondria, plastids, vacuoles) that
  work together; prokaryotic cells lack these.
- Cells grow and divide by mitosis (identical daughter cells) or meiosis
  (four gametes with half chromosome number); division is normally
  controlled, and loss of this control can cause cancer.
- The Cell Theory (Schleiden, Schwann, Virchow) unifies all of biology:
  all living things are made of cells, the cell is the basic unit of life,
  and all cells arise from pre-existing cells.
"""


# ── Seeding logic ──────────────────────────────────────────────────────────────

def seed_all(dry_run: bool, force: bool) -> None:
    print()
    print("  Seed Manual Lesson Content — Grade 9 Science, Cell: The Building Block of Life")
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
    print("  Done. Next step: re-run the Tier A audit to confirm findings improved:")
    print('    python3 scripts/audit_chapter_boundary.py --grade "Grade 9" '
          '--subject Science --chapter "Chapter 2: Cell: The Building Block of Life"')
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed manually-authored, NCERT-grounded lesson content for Grade 9 Science Ch.2 into lesson_cache"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be written without writing")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing cached lessons for these steps")
    args = parser.parse_args()
    seed_all(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
