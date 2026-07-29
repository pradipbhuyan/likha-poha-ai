# How to Add YouTube Video Resources to resources.py

## Context

`backend/app/data/resources.py` is the single source of truth for all curated learning resources served to students. Each grade/subject/chapter entry holds a list of YouTube video dicts:

```python
{
    "title": "Human-readable title",
    "type": "youtube",          # "youtube" = embeds with thumbnail; "website" = external link (no thumbnail)
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Critical:** `"type": "youtube"` with a `watch?v=` URL is the only format that renders a clickable thumbnail in the platform. `youtube.com/results` search URLs do NOT produce thumbnails.

---

## The Problem We Solved (July 2026)

Grade 11 and Grade 12 English chapters were added with `youtube.com/results` search URLs (no thumbnails). We needed to replace them with real `watch?v=` video IDs from Magnet Brains, matching the quality bar set by Maths and Physics.

---

## Step 1 — Choose the Right Channel

For CBSE English (Grades 11 & 12), **Magnet Brains** (14.4M subscribers) is the gold standard:
- Complete NCERT/CBSE 2023-24 board-exam series for all chapters
- Hornbill, Snapshots, Flamingo, Vistas — all covered
- High view counts (100k–4.7M per video), consistent quality
- Channel: https://www.youtube.com/@magnetbrains

Other subject–channel mappings already in use:
| Subject | Grade | Primary Channel |
|---------|-------|-----------------|
| Science / Physics | 9, 10 | Physics Wallah + Magnet Brains |
| Chemistry | 9, 10 | Alakh Pandey (PW) + Magnet Brains |
| Maths | 9 | Jain Tutor (new book), PW Foundation |
| Maths | 10 | Magnet Brains + Ritik Mishra |
| English | 8 | Magnet Brains (Poorvi book) |
| English | 9 | Magnet Brains (Kaveri book) |
| English | 10 | Magnet Brains (First Flight + Footprints) |
| English | 11 | **Magnet Brains (Hornbill + Snapshots)** ← new |
| English | 12 | **Magnet Brains (Flamingo + Vistas)** ← new |

---

## Step 2 — Find Video IDs (Browser Method)

Because YouTube search pages require JavaScript, terminal-based scraping (`curl`, `urllib`) returns no video IDs. The only reliable method is the **Puppeteer browser** built into Axet Plugin.

### Method A — Playlist / Course Page (Batch)
1. Search: `magnet brains class 11 english hornbill complete course`
2. Click "View full course" on the playlist result
3. The playlist page lists all chapter videos in order
4. Click each "Introduction / Explanation" video in the list
5. After clicking, the browser's console error log contains:
   ```
   dc_ref=http://www.youtube.com/video/VIDEO_ID
   ```
   or
   ```
   utvid=VIDEO_ID
   ```
   — both give you the currently-playing video's ID

### Method B — Per-Chapter Direct Search (Faster for individual chapters)
1. Navigate to: `https://www.youtube.com/results?search_query=magnet+brains+class+12+english+flamingo+the+last+lesson`
2. Click the first Magnet Brains result thumbnail
3. Read `utvid=VIDEO_ID` from the first CORS error in the console log — this is the video ID **before the ad even finishes**
4. You do NOT need to skip the ad or click Share to get the ID this way

### Method C — Share Dialog (Most Reliable)
1. Click the video thumbnail (any method)
2. Scroll down to see the video description
3. Click **Share** button
4. The share dialog shows: `https://youtu.be/VIDEO_ID`

---

## Step 3 — The Python Update Script

Once you have the video IDs, use this pattern to batch-update `resources.py`:

```python
# fix_video_ids.py  (adapt for any subject/grade)
import re

FILE = '/path/to/backend/app/data/resources.py'

with open(FILE, encoding='utf-8') as f:
    src = f.read()

# Dict: chapter_key_in_resources_py -> (video_id, display_title)
CHAPTERS = {
    "The Last Lesson": (
        "le_drhF4YeI",
        "The Last Lesson Class 12 | Flamingo Chapter 1 Explanation | Magnet Brains"
    ),
    "Lost Spring": (
        "sI6T22M7WEA",
        "Lost Spring Class 12 | Flamingo Chapter 2 Explanation | Magnet Brains"
    ),
    # ... add all chapters
}

replaced = 0

for chapter, (vid_id, title) in CHAPTERS.items():
    escaped = re.escape(chapter)
    new_entry = (
        f'{{"title": "{title}", "type": "youtube", '
        f'"url": "https://www.youtube.com/watch?v={vid_id}"}}'
    )

    # Matches a chapter key followed by 1–2 existing entries (search URLs or old watch URLs)
    pattern = (
        r'("' + escaped + r'":\s*\[)\s*\n'
        r'(?:\s*\{"title":[^\n]*"url":[^\n]*youtube(?:\.com/results|be\.com|\.com/watch)[^\n]*\},?\n){1,2}'
        r'(\s*\],)'
    )
    replacement = r'\1\n            ' + new_entry + r',\n        \2'
    new_src, count = re.subn(pattern, replacement, src)
    if count:
        src = new_src
        replaced += count
        print(f'  OK: {chapter!r}')
    else:
        print(f'  MISS (manual fix needed): {chapter!r}')

print(f'\nTotal replacements: {replaced}')
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(src)
print('Saved.')
```

### Key Rules for the Script
- **Chapter keys must exactly match** the keys in `GRADE_11_RESOURCES` / `GRADE_12_RESOURCES` in `resources.py` — including apostrophes, colons, capitalization
- The regex matches 1 or 2 existing entries per chapter (handles both single-entry and double-entry patterns)
- After running, verify with `get_learning_resources()` that `watch?v=` URLs are returned

---

## Step 4 — Verify Before Committing

```python
import sys; sys.path.insert(0, 'backend')
from app.data.resources import get_learning_resources

checks = [
    ('English', 'The Last Lesson', 'Grade 12'),
    ('English', 'A Photograph', 'Grade 11'),
    # add more spot checks
]
for subj, chap, grade in checks:
    res = get_learning_resources(subj, chap, grade)
    assert 'youtube.com/watch' in res[0]['url'], f"FAIL: {chap}"
    print(f"OK: {chap} -> {res[0]['url'].split('=')[-1]}")
```

---

## Step 5 — Git Commit Format

```bash
git add backend/app/data/resources.py
git commit -m "feat: add verified Magnet Brains video IDs for Grade 12 English

Grade 12 — Flamingo Prose (8), Poetry (6), Vistas (8) = 22 chapters
Channel: Magnet Brains (14.4M subs, NCERT/CBSE 2023-24 board-exam series)

All lookup tests passed: watch?v= URLs confirmed."
git pull --rebase origin main
git push origin main
```

---

## Appendix A — Confirmed Video IDs (July 2026)

### Grade 11 English (Magnet Brains, NCERT 2023-24)

**Hornbill Prose**
| Chapter | Video ID |
|---------|----------|
| The Portrait of a Lady | `NoK4h6ovI-A` |
| We're Not Afraid to Die... if We Can All Be Together | `lrUa6TRGL44` |
| Discovering Tut: the Saga Continues | `x4FTlX1DAX8` |
| Landscape of the Soul | `CyUISy5a_yY` |
| The Ailing Planet: the Green Movement's Role | `7M5kbfis0b0` |
| The Browning Version | `xorNo6_IN3M` |
| The Adventure | `x1ZeWG5eee0` |
| Silk Road | `7kfrLyEBN9k` |

**Hornbill Poetry**
| Poem | Video ID |
|------|----------|
| A Photograph | `g9IZ3TV4UC8` |
| The Laburnum Top | `R6nBT2SSfs0` |
| The Voice of the Rain | `Y4HrfwihKYM` |
| Childhood | `qkVra0gBtW4` |
| Father to Son | `BoDjDlcvrrY` |

**Snapshots**
| Chapter | Video ID |
|---------|----------|
| The Summer of the Beautiful White Horse | `5syylm7vr0M` |
| The Address | `2kYeA0bslHw` |
| Ranga's Marriage | `B4cSwUXM1ik` |
| Albert Einstein at School | `smHugZgBulI` |
| Mother's Day | `IEhxfEJ-QTc` |
| The Ghat of the Only World | `9_37-AWF-EU` |
| Birth | `8O7tp-FWxIw` |
| The Tale of Melon City | `bSUp338R3vk` |

---

### Grade 12 English (Magnet Brains, NCERT 2022-23 / 2023-24)

**Flamingo Prose**
| Chapter | Video ID |
|---------|----------|
| The Last Lesson | `le_drhF4YeI` |
| Lost Spring | `sI6T22M7WEA` |
| Deep Water | `oQLi31YxSOs` |
| The Rattrap | `rvmaM-lMGdc` |
| Indigo | `lfQKLucj6Es` |
| Poets and Pancakes | `fZm3C5e3qlI` |
| The Interview | `yvf3VU7tDPs` |
| Going Places | `PVM3MGQns_w` |

**Flamingo Poetry**
| Poem | Video ID |
|------|----------|
| My Mother at Sixty-six | `hylaNZ0qV5o` |
| An Elementary School Classroom in a Slum | `T5uB6ObhayA` |
| Keeping Quiet | `71ZUoT-z0AI` |
| A Thing of Beauty | `5hRxngpPaJM` |
| A Roadside Stand | `u7m5-x8ZBko` |
| Aunt Jennifer's Tigers | `EJUvPaB1JjM` |

**Vistas**
| Chapter | Video ID |
|---------|----------|
| The Third Level | `MAm96heUqeY` |
| The Tiger King | `1CYyO7wEWiQ` |
| Journey to the End of the Earth | `g_56IUJdj9c` |
| The Enemy | `oppE-JloUt0` |
| Should Wizard Hit Mommy? | `OFlciRaeysY` |
| On the Face of It | `NH4TFTLB0pA` |
| Evans Tries an O-Level | `6WyZz8RmAgs` |
| Memories of Childhood | `XMjt1RbA9Ec` |

---

## Appendix B — Dead Link Fixes Applied (Same Session)

These broken video URLs were also fixed during the same work session:

| Grade/Subject | Chapter | Old (Dead) ID | New (Working) ID | Root Cause |
|---|---|---|---|---|
| Gr12 Chemistry | Electrochemistry | `lQ6FBA1HM3s` | `1tvvSUySfls` | URL was a CrashCourse video, not KA |
| Gr12 Chemistry | Solutions | `3ROWXs3jtBU` | `qFHYnSY1h9I` | Video removed (404) |
| Gr12 Mathematics | Matrices | `kqWCgIVDRBo` | `xyAuNHPsq-g` | Video removed (404) |
| Gr12 Mathematics | Determinants | `Ip3X9LOh2iI` | `Ip3X9LOh2dk` | Typo in last 2 chars |

---

## Appendix C — How to Find Video IDs for Any New Subject

### Quick Recipe

```
1. Open browser to: https://www.youtube.com/results?search_query=magnet+brains+class+{GRADE}+{SUBJECT}+{CHAPTER_NAME}

2. Click first Magnet Brains result thumbnail

3. Read from first console error:
   utvid=VIDEO_ID    ← this is the ID (appears even before ad finishes)
   OR
   dc_ref=http://www.youtube.com/video/VIDEO_ID

4. Verify: navigate to https://www.youtube.com/watch?v=VIDEO_ID
   - Confirm it's Magnet Brains channel
   - Confirm chapter name is visible in title/thumbnail
```

### Identifying the Right Video When Multiple Exist
- Prefer videos with **NCERT/CBSE 2023-24** or **BOARD EXAMS 2023-24** badge in thumbnail
- Prefer **"Full Chapter Explanation"** or **"Introduction"** over **"Summary & Q&A"** or **"MCQs"**
- Higher view count = more reliable (usually the canonical version)

### Batch Collection Tip
If a channel has a playlist covering all chapters of a book:
1. Search for `magnet brains class 12 english flamingo vistas complete course`
2. Click "View full course"
3. Scroll through the playlist items
4. Click each chapter Introduction video → read `utvid` from console error
5. Each click gives one video ID with ~2 browser interactions instead of ~4
