import re

FILE = '/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend/app/data/resources.py'

with open(FILE, encoding='utf-8') as f:
    src = f.read()

# Map: chapter_key -> (video_id, title)
ALL_CHAPTERS = {
    # ── Grade 11 Hornbill Prose ──────────────────────────────────────────────
    "The Portrait of a Lady": ("NoK4h6ovI-A", "The Portrait of a Lady Class 11 | Hornbill Chapter 1 Explanation | Magnet Brains"),
    "We're Not Afraid to Die... if We Can All Be Together": ("lrUa6TRGL44", "We Are Not Afraid to Die Class 11 | Hornbill Chapter 2 | Magnet Brains"),
    "Discovering Tut: the Saga Continues": ("x4FTlX1DAX8", "Discovering Tut Class 11 | Hornbill Chapter 3 Explanation | Magnet Brains"),
    "Landscape of the Soul": ("CyUISy5a_yY", "Landscape of the Soul Class 11 | Hornbill Chapter 4 Explanation | Magnet Brains"),
    "The Ailing Planet: the Green Movement's Role": ("7M5kbfis0b0", "The Ailing Planet Class 11 | Hornbill Chapter 5 Explanation | Magnet Brains"),
    "The Browning Version": ("xorNo6_IN3M", "The Browning Version Class 11 | Hornbill Chapter 6 Explanation | Magnet Brains"),
    "The Adventure": ("x1ZeWG5eee0", "The Adventure Class 11 | Hornbill Chapter 7 Explanation | Magnet Brains"),
    "Silk Road": ("7kfrLyEBN9k", "Silk Road Class 11 | Hornbill Chapter 8 Explanation | Magnet Brains"),
    # ── Grade 11 Hornbill Poetry ─────────────────────────────────────────────
    "A Photograph": ("g9IZ3TV4UC8", "A Photograph Class 11 | Hornbill Poem 1 Explanation | Magnet Brains"),
    "The Laburnum Top": ("R6nBT2SSfs0", "The Laburnum Top Class 11 | Hornbill Poem 2 Explanation | Magnet Brains"),
    "The Voice of the Rain": ("Y4HrfwihKYM", "The Voice of the Rain Class 11 | Hornbill Poem 4 Explanation | Magnet Brains"),
    "Childhood": ("qkVra0gBtW4", "Childhood Class 11 | Hornbill Poem 6 Explanation | Magnet Brains"),
    "Father to Son": ("BoDjDlcvrrY", "Father to Son Class 11 | Hornbill Poem 5 Explanation | Magnet Brains"),
    # ── Grade 11 Snapshots ───────────────────────────────────────────────────
    "The Summer of the Beautiful White Horse": ("5syylm7vr0M", "The Summer of a Beautiful White Horse Class 11 | Snapshots Chapter 1 | Magnet Brains"),
    "The Address": ("2kYeA0bslHw", "The Address Class 11 | Snapshots Chapter 2 Explanation | Magnet Brains"),
    "Ranga's Marriage": ("B4cSwUXM1ik", "Ranga's Marriage Class 11 | Snapshots Chapter 3 Explanation | Magnet Brains"),
    "Albert Einstein at School": ("smHugZgBulI", "Albert Einstein at School Class 11 | Snapshots Chapter 4 | Magnet Brains"),
    "Mother's Day": ("IEhxfEJ-QTc", "Mother's Day Class 11 | Snapshots Chapter 5 Explanation | Magnet Brains"),
    "The Ghat of the Only World": ("9_37-AWF-EU", "The Ghat of the Only World Class 11 | Snapshots Chapter 6 | Magnet Brains"),
    "Birth": ("8O7tp-FWxIw", "Birth Class 11 | Snapshots Chapter 7 Explanation | Magnet Brains"),
    "The Tale of Melon City": ("bSUp338R3vk", "The Tale of the Melon City Class 11 | Snapshots Chapter 8 | Magnet Brains"),
    # ── Grade 12 Flamingo Prose ──────────────────────────────────────────────
    "The Last Lesson": ("le_drhF4YeI", "The Last Lesson Class 12 | Flamingo Chapter 1 Explanation | Magnet Brains"),
    "Lost Spring": ("sI6T22M7WEA", "Lost Spring Class 12 | Flamingo Chapter 2 Explanation | Magnet Brains"),
    "Deep Water": ("oQLi31YxSOs", "Deep Water Class 12 | Flamingo Chapter 3 Explanation | Magnet Brains"),
    "The Rattrap": ("rvmaM-lMGdc", "The Rattrap Class 12 | Flamingo Chapter 4 Explanation | Magnet Brains"),
    "Indigo": ("lfQKLucj6Es", "Indigo Class 12 | Flamingo Chapter 5 Explanation | Magnet Brains"),
    "Poets and Pancakes": ("fZm3C5e3qlI", "Poets and Pancakes Class 12 | Flamingo Chapter 6 Explanation | Magnet Brains"),
    "The Interview": ("yvf3VU7tDPs", "The Interview Class 12 | Flamingo Chapter 7 Explanation | Magnet Brains"),
    "Going Places": ("PVM3MGQns_w", "Going Places Class 12 | Flamingo Chapter 8 Explanation | Magnet Brains"),
    # ── Grade 12 Flamingo Poetry ─────────────────────────────────────────────
    "My Mother at Sixty-six": ("hylaNZ0qV5o", "My Mother at Sixty Six Class 12 | Flamingo Poem 1 Explanation | Magnet Brains"),
    "An Elementary School Classroom in a Slum": ("T5uB6ObhayA", "An Elementary School Classroom in a Slum Class 12 | Flamingo Poem 2 | Magnet Brains"),
    "Keeping Quiet": ("71ZUoT-z0AI", "Keeping Quiet Class 12 | Flamingo Poem 3 Explanation | Magnet Brains"),
    "A Thing of Beauty": ("5hRxngpPaJM", "A Thing of Beauty Class 12 | Flamingo Poem 4 Explanation | Magnet Brains"),
    "A Roadside Stand": ("u7m5-x8ZBko", "A Roadside Stand Class 12 | Flamingo Poem 5 Explanation | Magnet Brains"),
    "Aunt Jennifer's Tigers": ("EJUvPaB1JjM", "Aunt Jennifer's Tigers Class 12 | Flamingo Poem 6 Explanation | Magnet Brains"),
    # ── Grade 12 Vistas ──────────────────────────────────────────────────────
    "The Third Level": ("MAm96heUqeY", "The Third Level Class 12 | Vistas Chapter 1 Explanation | Magnet Brains"),
    "The Tiger King": ("1CYyO7wEWiQ", "The Tiger King Class 12 | Vistas Chapter 2 Explanation | Magnet Brains"),
    "Journey to the End of the Earth": ("g_56IUJdj9c", "Journey to the End of the Earth Class 12 | Vistas Chapter 3 | Magnet Brains"),
    "The Enemy": ("oppE-JloUt0", "The Enemy Class 12 | Vistas Chapter 4 Explanation | Magnet Brains"),
    "Should Wizard Hit Mommy?": ("OFlciRaeysY", "Should Wizard Hit Mommy Class 12 | Vistas Chapter 5 | Magnet Brains"),
    "On the Face of It": ("NH4TFTLB0pA", "On the Face of It Class 12 | Vistas Chapter 6 Explanation | Magnet Brains"),
    "Evans Tries an O-Level": ("6WyZz8RmAgs", "Evans Tries an O-Level Class 12 | Vistas Chapter 7 Explanation | Magnet Brains"),
    "Memories of Childhood": ("XMjt1RbA9Ec", "Memories of Childhood Class 12 | Vistas Chapter 8 Explanation | Magnet Brains"),
}

replaced = 0

for chapter, (vid_id, title) in ALL_CHAPTERS.items():
    escaped = re.escape(chapter)
    new_entry = f'{{"title": "{title}", "type": "youtube", "url": "https://www.youtube.com/watch?v={vid_id}"}}'

    # Pattern: "Chapter": [\n    {search_url_entry1},\n    {search_url_entry2},\n        ],
    pattern = (
        r'("' + escaped + r'":\s*\[)\s*\n'
        r'(?:\s*\{"title":[^\n]*"url":[^\n]*youtube(?:\.com/results|be\.com)[^\n]*\},?\n){1,2}'
        r'(\s*\],)'
    )
    replacement = r'\1\n            ' + new_entry + r',\n        \2'
    new_src, count = re.subn(pattern, replacement, src)
    if count:
        src = new_src
        replaced += count
        print(f'  OK: {chapter!r}')
    else:
        print(f'  MISS: {chapter!r}')

print(f'\nTotal replacements: {replaced}')

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(src)
print('Saved.')

# Quick verify
import sys; sys.path.insert(0, '/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend')
import importlib
import app.data.resources as r
importlib.reload(r)
from app.data.resources import get_learning_resources

checks = [
    ('English', 'The Portrait of a Lady', 'Grade 11'),
    ('English', 'Silk Road', 'Grade 11'),
    ('English', 'Childhood', 'Grade 11'),
    ('English', 'The Tale of Melon City', 'Grade 11'),
    ('English', 'The Last Lesson', 'Grade 12'),
    ('English', 'Keeping Quiet', 'Grade 12'),
    ('English', 'The Third Level', 'Grade 12'),
    ('English', 'Memories of Childhood', 'Grade 12'),
]
print('\nVerification:')
all_ok = True
for subj, chap, grade in checks:
    res = get_learning_resources(subj, chap, grade)
    ok = len(res) >= 1 and 'youtube.com/watch' in res[0]['url']
    status = 'OK' if ok else 'FAIL'
    if not ok:
        all_ok = False
        print(f'  [{status}] {grade} {chap} -> {res[0]["url"] if res else "EMPTY"}')
    else:
        vid = res[0]['url'].split('=')[-1]
        print(f'  [{status}] {grade} {chap} -> {vid}')
print('All OK!' if all_ok else 'SOME FAILED!')
