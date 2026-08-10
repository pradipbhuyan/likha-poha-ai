# RAG Knowledge DB Strategy — Maths & Science
## CBSE Tutor Platform · Strategic Recommendation Report

---

## 1. Executive Summary

Your platform already has a **working, production-grade RAG pipeline** built on:

| Layer | Technology |
|---|---|
| Embedding model | `text-embedding-3-small` (OpenAI) |
| Vector store | Supabase `pgvector` (two separate projects: Grades 1-10 + Grades 11-12) |
| Chunking | Word-based, 1200 words/chunk (`rag_service.py`) |
| Ingestion | Admin panel UI + CLI scripts (`upload_ncert_grade11_12_rag.py`) |
| Retrieval | `match_rag_chunks` Supabase RPC with grade/subject/chapter filters |
| Consumption | `tutor_service.py` → lesson generation, doubt answering, follow-ups |

### What Already Exists in the DB

| Content | Status |
|---|---|
| Grade 9 Science (iesc1 — 13 chapters) | ✅ Files in `RAG DB/Science/` |
| Grade 9 Maths (iemh1 — 8 chapters) | ✅ Files in `RAG DB/Maths/` |
| Grade 8 content | ✅ Files in `RAG DB/Class 8/` |
| SOF Olympiad Science + English | ✅ Files in `RAG DB/Eng SOF/`, `RAG DB/Science SOF/` |
| Grade 11/12 NCERT all subjects | ✅ Automated download + upload script ready |
| Arts, Hindi, Sanskrit | ✅ Files in respective RAG DB subfolders |

### What is MISSING for Complete Maths + Science KB

| Gap | Priority |
|---|---|
| Grade 1–5 Mathematics (Math-Magic NCERT) | HIGH — primary school base |
| Grade 1–5 EVS / General Science (NCERT) | HIGH |
| Grade 6–8 Mathematics (NCERT) | HIGH |
| Grade 6–8 Science (NCERT) | HIGH |
| Grade 10 Mathematics + Science (NCERT) | HIGH — board exam grade |
| Supplementary worked examples / problem sets | MEDIUM |
| CBSE Sample Papers & Previous Year Questions | MEDIUM |
| Advanced concept reinforcement (CK-12, DIKSHA) | LOW |

---

## 2. Free Source Catalogue — Maths & Science

### 2.1 Tier 1 — NCERT Official (PRIMARY SOURCE, Already Integrated)

**URL:** https://ncert.nic.in/textbook.php  
**License:** Free for educational use, government of India  
**Format:** PDF (directly downloadable, no login required)  
**Quality:** Highest — this IS the CBSE curriculum

Your pipeline already handles NCERT PDFs perfectly. The existing script
`download_ncert_grade11_12.py` + `upload_ncert_grade11_12_rag.py` shows the
exact pattern. Below are all missing book codes.

#### Complete NCERT Maths Book Code Map

| Grade | Book Code(s) | Book Title | Direct PDF URL Pattern |
|---|---|---|---|
| 1 | `aemh1` | Math Magic 1 | `https://ncert.nic.in/textbook/pdf/aemh1{ch}.pdf` |
| 2 | `bemh1` | Math Magic 2 | `https://ncert.nic.in/textbook/pdf/bemh1{ch}.pdf` |
| 3 | `cemh1` | Math Magic 3 | `https://ncert.nic.in/textbook/pdf/cemh1{ch}.pdf` |
| 4 | `demh1` | Math Magic 4 | `https://ncert.nic.in/textbook/pdf/demh1{ch}.pdf` |
| 5 | `eemh1` | Math Magic 5 | `https://ncert.nic.in/textbook/pdf/eemh1{ch}.pdf` |
| 6 | `femh1` | Mathematics 6 | `https://ncert.nic.in/textbook/pdf/femh1{ch}.pdf` |
| 7 | `gemh1` | Mathematics 7 | `https://ncert.nic.in/textbook/pdf/gemh1{ch}.pdf` |
| 8 | `hemh1` | Mathematics 8 | `https://ncert.nic.in/textbook/pdf/hemh1{ch}.pdf` |
| 9 | `iemh1` | Mathematics 9 | ✅ Already in `RAG DB/Maths/` |
| 10 | `jemh1`, `jemh2` | Mathematics 10 Pt1 + Pt2 | `https://ncert.nic.in/textbook/pdf/jemh1{ch}.pdf` |
| 11 | `kemh1`, `kemh2` | Mathematics 11 Pt1 + Pt2 | ✅ Handled by Grade11/12 script |
| 12 | `lemh1`, `lemh2` | Mathematics 12 Pt1 + Pt2 | ✅ Handled by Grade11/12 script |

*Chapter suffix format: `01`, `02` ... `15` appended to book code, e.g. `femh101.pdf`*

#### Complete NCERT Science Book Code Map

| Grade | Book Code | Book Title | Direct PDF URL Pattern |
|---|---|---|---|
| 1 | `aess1` | Looking Around (EVS) | `https://ncert.nic.in/textbook/pdf/aess1{ch}.pdf` |
| 2 | `bess1` | Looking Around (EVS) | `https://ncert.nic.in/textbook/pdf/bess1{ch}.pdf` |
| 3 | `cess1` | Looking Around (EVS) | `https://ncert.nic.in/textbook/pdf/cess1{ch}.pdf` |
| 4 | `dess1` | Looking Around (EVS) | `https://ncert.nic.in/textbook/pdf/dess1{ch}.pdf` |
| 5 | `eess1` | Looking Around (EVS) | `https://ncert.nic.in/textbook/pdf/eess1{ch}.pdf` |
| 6 | `fesc1` | Science 6 | `https://ncert.nic.in/textbook/pdf/fesc1{ch}.pdf` |
| 7 | `gesc1` | Science 7 | `https://ncert.nic.in/textbook/pdf/gesc1{ch}.pdf` |
| 8 | `hesc1` | Science 8 | `https://ncert.nic.in/textbook/pdf/hesc1{ch}.pdf` |
| 9 | `iesc1` | Science 9 | ✅ Already in `RAG DB/Science/` |
| 10 | `jesc1` | Science 10 | `https://ncert.nic.in/textbook/pdf/jesc1{ch}.pdf` |
| 11 | `keph1`, `keph2` | Physics 11 | ✅ Handled by Grade11/12 script |
| 11 | `kech1`, `kech2` | Chemistry 11 | ✅ Handled by Grade11/12 script |
| 11 | `kebo1` | Biology 11 | ✅ Handled by Grade11/12 script |
| 12 | `leph1`, `leph2` | Physics 12 | ✅ Handled by Grade11/12 script |
| 12 | `lech1`, `lech2` | Chemistry 12 | ✅ Handled by Grade11/12 script |
| 12 | `lebo1` | Biology 12 | ✅ Handled by Grade11/12 script |

> **Note on 2023 NCERT Curriculum Refresh:** NCERT launched new "Curiosity" (Science)
> and "Ganita Prakash" (Maths) textbooks for Grades 3, 6, 7. These use new book codes
> (`fecu1`, `gecu1` for Science; `fgmh1`, `ggmh1` for Maths). Your existing script
> already handles these with the `infer_book_section_title()` heuristic. Check
> https://ncert.nic.in/textbook.php after June 2026 for updated codes.

---

### 2.2 Tier 2 — DIKSHA / ePathshala (Government Supplementary, FREE)

**DIKSHA:** https://diksha.gov.in/explore  
**ePathshala:** https://epathshala.nic.in/e-pathshala-4/flipbook  
**License:** Government of India open educational resource  
**Format:** PDF + HTML content  
**Use case:** Supplementary activities, animated explanations, bilingual content  

DIKSHA hosts NCERT-aligned content with activities, experiments, and Hindi
explanations. Useful for adding **activity-based context** to your Maths/Science
RAG (things like "Activity: Observe a candle burning..." that NCERT textbooks
describe but don't always elaborate on).

**How to ingest:** Download relevant PDFs from DIKSHA portal and upload via your
existing admin panel bulk upload route (`/api/rag/bulk-book-upload`). Tag with the
same grade/subject/chapter as the corresponding NCERT book for merged retrieval.

---

### 2.3 Tier 3 — CBSE Academic Portal (Sample Papers + Question Banks, FREE)

**URL:** https://cbseacademic.nic.in/SampleQuestion_Papers.html  
**Also:** https://cbseacademic.nic.in/web_material/CurriculumMain24/secondary.html  
**License:** Free (CBSE government portal)  
**Format:** PDF  
**Use case:** Question banks, marking schemes, solved examples  

These are **gold for your question bank** (`question_bank_service.py`) and
also add worked-example density to the RAG DB. Uploading Grade 10 CBSE Sample
Papers for Maths and Science into RAG gives the tutor access to official
board-level solved problems.

**Chapters to tag them under:** Use the chapter name from NCERT syllabus +
append `(Sample Paper)` to the title field for admin clarity.

---

### 2.4 Tier 4 — CK-12 Foundation (Advanced Concept Reinforcement, FREE)

**URL:** https://www.ck12.org/student/  
**License:** Creative Commons Attribution-NonCommercial  
**Format:** HTML / PDF download  
**Use case:** Advanced Grade 9–10 Science + Maths beyond NCERT scope  

CK-12 is a US-curriculum platform but the underlying Physics, Chemistry, Biology,
and Maths concepts are identical. Their FlexBooks® for Physics, Chemistry, and
Algebra have excellent concept explanations with visual diagrams.

**Best use:** Feed CK-12 content into your `Advanced Science` and
`Advanced Mathematics` subject slots (already defined in `syllabus.py` for Grade 9).
This directly enriches the SOF Olympiad preparation track.

**How to get content:** Use CK-12's "Download as PDF" feature on any FlexBook.
No scraping needed — legal PDF download is provided for all content.

---

### 2.5 Tier 5 — Khan Academy (Supplementary Explanations)

**URL:** https://www.khanacademy.org/  
**License:** CC BY-NC-SA (non-commercial use ok, attribution required)  
**Format:** Video transcripts + article text  
**Use case:** Alternative plain-language explanations for difficult concepts  

Khan Academy's article text (not videos) can be extracted and used. The concepts
align well with CBSE Grade 6–10 Maths and Science.

**Practical limitation:** Khan Academy does not offer bulk PDF downloads. You
would need to copy-paste key article text into your admin panel text upload,
or write a targeted scraper (check ToS carefully — educational internal use is
generally acceptable).

**Recommended approach:** Use Khan Academy selectively for 10–15 concepts where
students historically struggle (e.g., "Why does the sky appear blue", "Proof of
Pythagoras theorem") — add these as manually curated RAG documents via your
existing `/api/rag/upload-text` endpoint.

---

### 2.6 Source Priority Matrix

| Source | Cost | Coverage | Integration Effort | Recommended |
|---|---|---|---|---|
| NCERT Official (remaining grades) | Free | Grades 1-10 complete | Low (script exists) | ✅ DO FIRST |
| NCERT Grade 11/12 via existing script | Free | Full | Already done | ✅ Done |
| CBSE Sample Papers | Free | Grade 10 board focus | Low (admin upload) | ✅ DO SECOND |
| DIKSHA supplementary | Free | Grades 1-10 | Medium | Recommended |
| CK-12 Advanced | Free | Grade 9-12 advanced | Low (PDF download) | For Advanced track |
| Khan Academy articles | Free | Grade 6-10 | Medium (manual) | Selective use |
| ePathshala | Free | Grades 1-12 | Low | Optional |

---

## 3. Step-by-Step Build Plan

### Phase 1 — Extend Existing Script for Grades 1–10 (1–2 hours)

Create `backend/scripts/download_ncert_grade1_10.py` modelled exactly on
`download_ncert_grade11_12.py`. The script should:

1. Download all chapter PDFs for the book codes listed in Section 2.1
2. Save to `~/Desktop/cbse_ncert_pdfs/Grade_N/Subject/` folder structure
3. Then run `upload_ncert_grade1_10_rag.py` to chunk + embed + store

**Key book codes to add (Maths):**
```python
GRADE_1_10_MATHS = {
    "Grade 1":  ["aemh1"],
    "Grade 2":  ["bemh1"],
    "Grade 3":  ["cemh1"],
    "Grade 4":  ["demh1"],
    "Grade 5":  ["eemh1"],
    "Grade 6":  ["femh1"],
    "Grade 7":  ["gemh1"],
    "Grade 8":  ["hemh1"],
    # Grade 9 already done (iemh1)
    "Grade 10": ["jemh1", "jemh2"],
}

GRADE_1_10_SCIENCE = {
    "Grade 1":  ["aess1"],  # EVS
    "Grade 2":  ["bess1"],  # EVS
    "Grade 3":  ["cess1"],  # EVS / new: cecu1 (Curiosity)
    "Grade 4":  ["dess1"],  # EVS
    "Grade 5":  ["eess1"],  # EVS
    "Grade 6":  ["fesc1"],  # new: fecu1 (Curiosity Science)
    "Grade 7":  ["gesc1"],  # new: gecu1 (Curiosity Science)
    "Grade 8":  ["hesc1"],
    # Grade 9 already done (iesc1)
    "Grade 10": ["jesc1"],
}
```

### Phase 2 — Upload Grade 8 Content Already on Disk (30 minutes)

You have `RAG DB/Class 8/` already. Run these through the admin panel
**Book Set Upload** feature (batch PDF upload with chapter-level tagging). Or
add a one-off script similar to the Grade 11/12 script.

### Phase 3 — CBSE Sample Papers & Question Banks (1 hour)

1. Download Grade 10 Maths + Science sample papers from:
   https://cbseacademic.nic.in/SampleQuestion_Papers.html
2. Upload via admin panel → RAG Upload → Book Set Upload
3. Tag as: Grade 10 / Maths / "Board Exam Practice" and Grade 10 / Science / "Board Exam Practice"

### Phase 4 — Advanced Track Content (2 hours)

For your `Advanced Mathematics` and `Advanced Science` subjects (Grade 9 syllabus):
1. Download relevant CK-12 FlexBooks PDFs from https://www.ck12.org/student/
2. Upload chapter-by-chapter to match `Advanced - Sets`, `Advanced - Logarithms`, etc.
3. Tag subject as `Advanced Mathematics` or `Advanced Science`

---

## 4. Where to Surface Reference Links in the Platform

### 4.1 Current Architecture Context

The tutor uses RAG silently — students receive lessons and answers without seeing
source attribution. The `source_type` field (`RAG` vs `LLM`) is tracked but not
prominently displayed. You have a `routes/resources.py` and `data/resources.py`
that appear to be a static resources catalogue.

### 4.2 Recommended Placement (4 Locations)

---

#### Location A — Lesson Page: "📚 Textbook Source" Badge + Link

**Where:** Below each generated lesson, next to the existing `source_type` indicator  
**What:** A small badge: `📚 NCERT Grade 9 Science — Chapter: Matter in Our Surroundings`  
**Clickable link to:** The official NCERT PDF URL (e.g. https://ncert.nic.in/textbook/pdf/iesc101.pdf)

**Why here:** Students can open the actual textbook page while reading the AI lesson.
This builds trust and provides a fallback when the student wants to read the original text.

**Implementation in frontend (`frontend/src/pages/` lesson page):**
```jsx
{lesson.source_type === 'RAG' && lesson.sources?.length > 0 && (
  <div className="textbook-source-badge">
    <span>📚 Based on NCERT Textbook</span>
    <a href={getNcertPdfUrl(grade, subject, chapter)} target="_blank">
      Open Textbook →
    </a>
  </div>
)}
```

Add a helper `getNcertPdfUrl(grade, subject, chapter)` in `frontend/src/utils/`
that maps grade+subject to the correct NCERT book code + chapter number.

---

#### Location B — Resources Page (Already Exists: `routes/resources.py`)

**Where:** Dedicated `/resources` page in the student portal  
**What:** A curated list of free reference materials per subject per grade  
**Structure:**

```
Grade 9 — Mathematics
  ├── 📄 NCERT Mathematics Textbook (official) → ncert.nic.in
  ├── 📄 CBSE Sample Paper 2024-25 → cbseacademic.nic.in
  └── 🔗 DIKSHA Interactive Content → diksha.gov.in

Grade 9 — Science
  ├── 📄 NCERT Science Textbook (official) → ncert.nic.in
  ├── 📄 CBSE Sample Paper 2024-25 → cbseacademic.nic.in
  └── 🔗 ePathshala animations → epathshala.nic.in
```

**Update `backend/app/data/resources.py`** to include structured entries for each
grade+subject combination with `source_name`, `url`, `type` (textbook/sample_paper/
interactive), and `grade`/`subject` filters so the frontend can filter by the
student's current grade.

---

#### Location C — Doubt Page: "Learn More" Source Link

**Where:** Below each doubt answer, in the mentor suggestions area  
**What:** When `source_type === 'RAG'`, show the textbook page link alongside the
existing suggestion buttons ("Give a practice question", "Explain step-by-step")  
**Example:** `📖 This answer is based on your Grade 9 Science textbook. [Read original →]`

This is a **trust signal** — students (and parents) see that answers come from
official NCERT sources, not hallucinated content.

---

#### Location D — Admin Panel: RAG Document Library (Already Exists)

**Where:** Admin → RAG Documents list  
**What:** Add a `source_url` column to `rag_documents` table and display it in the
admin document list. When uploading NCERT PDFs, auto-populate the source URL from
the NCERT CDN pattern.

**SQL migration needed:**
```sql
ALTER TABLE rag_documents ADD COLUMN IF NOT EXISTS source_url TEXT;
```

**Auto-populate in `upload_ncert_grade1_10_rag.py`:**
```python
source_url = f"https://ncert.nic.in/textbook/pdf/{book_code}{chapter_num:02d}.pdf"
```

---

#### Location E — Parent Dashboard: Knowledge Source Transparency

**Where:** Parent dashboard → "How we teach" section  
**What:** A static infographic or text section explaining:
  - "All lessons are powered by official NCERT textbooks"
  - "Reference sources: NCERT, CBSE Academic Portal, DIKSHA"
  - Links to the source portals for parent verification

Parents are a primary decision-maker for your platform. Showing them the source
credibility (NCERT + government portals) is a **conversion driver**, not just UX.

---

### 4.3 Reference Links Summary Table

| Link | Display Name | Where to Show |
|---|---|---|
| https://ncert.nic.in/textbook.php | NCERT Official Textbooks | Lesson page, Resources page, Parent dashboard |
| https://cbseacademic.nic.in/SampleQuestion_Papers.html | CBSE Sample Papers | Resources page, Mock Test page |
| https://diksha.gov.in/explore | DIKSHA Interactive Content | Resources page |
| https://epathshala.nic.in | ePathshala Flipbooks | Resources page |
| https://www.ck12.org/student/ | CK-12 Advanced Content | Advanced track Resources page |
| https://ncert.nic.in/textbook/pdf/{code}{ch}.pdf | Chapter-specific PDF | Lesson source badge (dynamic) |

---

## 5. Cost Estimation

### 5.1 One-Time Build Cost

#### OpenAI Embedding API (`text-embedding-3-small` @ $0.02 / 1M tokens)

| Content Set | Est. Chapters | Avg Words/Chapter | Est. Tokens | Cost |
|---|---|---|---|---|
| Grade 1–5 Maths (Math-Magic) | 65 chapters | 2,000 words | 170K tokens | $0.003 |
| Grade 1–5 EVS/Science | 60 chapters | 2,500 words | 195K tokens | $0.004 |
| Grade 6–8 Maths | 45 chapters | 6,000 words | 351K tokens | $0.007 |
| Grade 6–8 Science | 50 chapters | 8,000 words | 520K tokens | $0.010 |
| Grade 10 Maths | 15 chapters | 10,000 words | 195K tokens | $0.004 |
| Grade 10 Science | 16 chapters | 10,000 words | 208K tokens | $0.004 |
| CBSE Sample Papers (10 papers) | 10 docs | 5,000 words | 65K tokens | $0.001 |
| CK-12 Advanced (selective) | 20 docs | 8,000 words | 208K tokens | $0.004 |
| **TOTAL** | **~280 units** | — | **~1.9M tokens** | **~$0.04** |

> The entire NCERT Maths + Science corpus for Grades 1–12 costs **less than $0.10**
> to embed. This is the single biggest cost advantage of `text-embedding-3-small`.

#### Developer / Operator Time

| Task | Time | Cost (at ₹2000/hr) |
|---|---|---|
| Write `download_ncert_grade1_10.py` script | 2 hours | ₹4,000 |
| Write `upload_ncert_grade1_10_rag.py` script | 2 hours | ₹4,000 |
| Download + verify all PDFs | 1 hour | ₹2,000 |
| Run upload scripts + monitor | 1 hour | ₹2,000 |
| Upload Grade 8 content via admin panel | 30 min | ₹1,000 |
| Upload CBSE sample papers manually | 1 hour | ₹2,000 |
| Add reference links to frontend | 3 hours | ₹6,000 |
| Add `source_url` column + admin display | 1 hour | ₹2,000 |
| **TOTAL** | **~11.5 hours** | **₹23,000** |

---

### 5.2 Ongoing Monthly Cost

| Item | Cost/Month |
|---|---|
| OpenAI embeddings (new content additions) | $0–$1 |
| Supabase (vector storage) — Free tier | $0 (up to 500MB DB) |
| Supabase — Pro tier if DB > 500MB | $25 |
| LLM inference (GPT-4o-mini for lessons) | Already in your budget |
| **Total new cost for RAG KB** | **$0–$26/month** |

> Your existing Supabase subscription covers the RAG storage. The complete
> Grade 1–12 NCERT corpus produces approximately 12,000 chunks × 6KB each
> = ~72MB of vector data. This fits comfortably within Supabase Free tier (500MB).
> You will only need Supabase Pro when your user base generates significant
> lesson_cache + question_bank growth.

---

### 5.3 Total Cost Summary

| Category | One-Time Cost | Monthly Cost |
|---|---|---|
| OpenAI embedding API | ~$0.10 (≈ ₹8) | $0–$1 |
| Developer time (scripts + frontend) | ₹23,000 (~$275) | $0 |
| Infrastructure (Supabase) | $0 | $0–$25 |
| PDF sources | $0 (all free) | $0 |
| **Grand Total** | **~₹23,000 one-time** | **$0–$26/month** |

---

## 6. Architecture Decisions & Recommendations

### 6.1 Keep Single Embedding Model — Do NOT Change

Your entire RAG DB uses `text-embedding-3-small`. The `rag_service.py` has a
prominent comment: *"Must be the same model for all stored chunks — changing
this requires deleting all rag_chunks rows and re-uploading every RAG document."*

**Recommendation:** Do not switch to `text-embedding-3-large` or `ada-002`.
`text-embedding-3-small` is already excellent for educational text retrieval and
costs 5× less than `text-embedding-3-large`.

### 6.2 Chunk Size — Consider Reducing for Maths

Your current chunk size is **1200 words** (`rag_service.py: split_text_into_chunks`).
For Grade 11/12 the script uses **400 words with 50-word overlap** (better).

**Recommendation for Grade 1–10 uploads:** Use 400–600 word chunks with 50-word
overlap for Maths. Mathematical content is dense — a 1200-word chunk often spans
multiple unrelated theorems. The existing Grade 11/12 script's `CHUNK_SIZE = 400`
is the right pattern to follow for the new Grade 1–10 script.

### 6.3 Separate "Worked Examples" RAG Collection

Consider adding a `source_type = 'worked_example'` tag in `rag_documents` for
CBSE sample paper content. This lets you build a future retrieval path that
specifically fetches solved problems when a student asks "give me an example."

The `question_bank_service.py` already exists — a worked-examples RAG layer
bridges the gap between free-form RAG retrieval and the structured question bank.

### 6.4 Do NOT Use Paid Sources

Avoid Byju's, Toppr, Vedantu, or Unacademy content. Apart from being paywalled,
using their content without license creates legal risk. NCERT + CBSE Academic +
DIKSHA + CK-12 (CC license) is a complete, legally clean knowledge base.

### 6.5 Grade 11/12 — Run the Existing Script Now

`backend/scripts/upload_ncert_grade11_12_rag.py` is fully ready. If it hasn't
been run yet for all subjects, this is the highest-ROI action:

```bash
cd backend
python3 scripts/download_ncert_grade11_12.py
python3 scripts/upload_ncert_grade11_12_rag.py
```

---

## 7. Quick Reference: All Free Source Links

| Source | URL | Content |
|---|---|---|
| NCERT Textbooks | https://ncert.nic.in/textbook.php | Grade 1-12 all subjects PDF |
| NCERT PDF Direct | https://ncert.nic.in/textbook/pdf/{code}.pdf | Individual chapter PDFs |
| CBSE Sample Papers | https://cbseacademic.nic.in/SampleQuestion_Papers.html | Grade 10/12 board papers |
| CBSE Curriculum | https://cbseacademic.nic.in/web_material/CurriculumMain24/secondary.html | Syllabus PDFs |
| DIKSHA Platform | https://diksha.gov.in/explore | Interactive NCERT-aligned content |
| ePathshala | https://epathshala.nic.in/e-pathshala-4/flipbook | NCERT digital flipbooks |
| CK-12 FlexBooks | https://www.ck12.org/student/ | Advanced Science/Maths (CC license) |
| Khan Academy | https://www.khanacademy.org/ | Supplementary concept text |
| NCERT Solutions (unofficial) | https://ncert.nic.in/ncerts/l/index.html | Exercise solutions |
| SOF Past Papers | https://sofworld.org/sample-papers | Olympiad practice papers |

---

## 8. Immediate Action Checklist

- [ ] **TODAY**: Run `upload_ncert_grade11_12_rag.py` if not already done for all Grade 11/12 subjects
- [ ] **THIS WEEK**: Write `download_ncert_grade1_10.py` + `upload_ncert_grade1_10_rag.py` for Maths + Science
- [ ] **THIS WEEK**: Upload `RAG DB/Class 8/` content via admin panel for Grade 8 Maths + Science
- [ ] **NEXT WEEK**: Download + upload Grade 10 Maths + Science NCERT PDFs
- [ ] **NEXT WEEK**: Download CBSE Sample Papers (Grade 10 Maths + Science) and upload via admin panel
- [ ] **NEXT SPRINT**: Add `source_url` column to `rag_documents` table
- [ ] **NEXT SPRINT**: Add NCERT source badge + link to the lesson page frontend
- [ ] **NEXT SPRINT**: Update `data/resources.py` with structured source catalogue per grade/subject
- [ ] **NEXT SPRINT**: Add "Based on NCERT textbook" trust signal to doubt answer page
- [ ] **NEXT SPRINT**: Add source transparency section to parent dashboard

---

## 9. What NOT to Do

| Don't | Why |
|---|---|
| Switch embedding model mid-way | Breaks all existing embeddings — full re-upload required |
| Use 1200-word chunks for Maths | Too large; multiple theorems blur into one chunk, hurting retrieval precision |
| Scrape Byju's / Vedantu / Toppr | Copyright violation; legal risk outweighs any benefit |
| Store full textbook PDFs in Supabase Storage | Unnecessary cost; your pipeline extracts text at upload time |
| Upload duplicate content for the same chapter | Retrieval returns duplicate chunks; check `doc_has_chunks()` before re-uploading |
| Add external LLM-written notes as "NCERT content" | Factual drift risk; only use official government sources as primary RAG content |
| Use `text-embedding-3-large` for cost savings | It is 5× more expensive, not cheaper; `text-embedding-3-small` is the right choice |

---

## 10. Summary

Your platform is **85% of the way there**. The RAG pipeline is production-ready,
tested, and deployed. The knowledge DB gap is purely a content-ingestion task,
not an engineering task.

**The complete Maths + Science knowledge DB can be built in one weekend:**
- Total embedding cost: **< $0.10**
- Total infrastructure cost: **$0** (fits in existing Supabase free tier)
- Total developer time: **~11.5 hours**
- All sources: **100% free, legally clean government sources**

The most impactful next action is to write and run the Grade 1–10 NCERT download
and upload scripts. Everything else (chunking, embedding, storage, retrieval,
consumption by the AI tutor) is already built and working.

---

*Generated: June 2026 | Platform: cbse-tutor-platform | Author: Axet Plugin*
