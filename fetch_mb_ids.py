import urllib.request, re, json, time

CHAPTERS_G11 = [
    # Hornbill Prose
    ("The Portrait of a Lady", "class 11 english hornbill portrait of a lady introduction"),
    ("We're Not Afraid to Die", "class 11 english hornbill we're not afraid to die"),
    ("Discovering Tut", "class 11 english hornbill discovering tut saga continues"),
    ("Landscape of the Soul", "class 11 english hornbill landscape of the soul"),
    ("The Ailing Planet", "class 11 english hornbill ailing planet green movement"),
    ("The Browning Version", "class 11 english hornbill browning version"),
    ("The Adventure", "class 11 english hornbill the adventure"),
    ("Silk Road", "class 11 english hornbill silk road"),
    # Hornbill Poetry
    ("A Photograph", "class 11 english hornbill a photograph poem explanation"),
    ("The Laburnum Top", "class 11 english hornbill laburnum top poem"),
    ("The Voice of the Rain", "class 11 english hornbill voice of the rain poem"),
    ("Childhood", "class 11 english hornbill childhood poem"),
    ("Father to Son", "class 11 english hornbill father to son poem"),
    # Snapshots
    ("Summer of the Beautiful White Horse", "class 11 english snapshots summer beautiful white horse"),
    ("The Address", "class 11 english snapshots the address"),
    ("Ranga's Marriage", "class 11 english snapshots ranga's marriage"),
    ("Albert Einstein at School", "class 11 english snapshots albert einstein at school"),
    ("Mother's Day", "class 11 english snapshots mother's day"),
    ("Ghat of the Only World", "class 11 english snapshots ghat only world"),
    ("Birth", "class 11 english snapshots birth a j cronin"),
    ("The Tale of Melon City", "class 11 english snapshots tale of melon city"),
]

CHAPTERS_G12 = [
    # Flamingo Prose
    ("The Last Lesson", "class 12 english flamingo the last lesson"),
    ("Lost Spring", "class 12 english flamingo lost spring"),
    ("Deep Water", "class 12 english flamingo deep water"),
    ("The Rattrap", "class 12 english flamingo the rattrap"),
    ("Indigo", "class 12 english flamingo indigo"),
    ("Poets and Pancakes", "class 12 english flamingo poets and pancakes"),
    ("The Interview", "class 12 english flamingo the interview"),
    ("Going Places", "class 12 english flamingo going places"),
    # Flamingo Poetry
    ("My Mother at Sixty-six", "class 12 english flamingo my mother at sixty six poem"),
    ("Elementary School Classroom", "class 12 english flamingo elementary school classroom slum"),
    ("Keeping Quiet", "class 12 english flamingo keeping quiet poem"),
    ("A Thing of Beauty", "class 12 english flamingo thing of beauty poem"),
    ("A Roadside Stand", "class 12 english flamingo roadside stand poem"),
    ("Aunt Jennifer's Tigers", "class 12 english flamingo aunt jennifer's tigers"),
    # Vistas
    ("The Third Level", "class 12 english vistas the third level"),
    ("The Tiger King", "class 12 english vistas the tiger king"),
    ("Journey to the End of the Earth", "class 12 english vistas journey end earth"),
    ("The Enemy", "class 12 english vistas the enemy"),
    ("Should Wizard Hit Mommy", "class 12 english vistas should wizard hit mommy"),
    ("On the Face of It", "class 12 english vistas on the face of it"),
    ("Evans Tries an O-Level", "class 12 english vistas evans tries o level"),
    ("Memories of Childhood", "class 12 english vistas memories of childhood"),
]

def find_magnet_brains_id(query):
    """Search YouTube for Magnet Brains video and return first video ID."""
    url = f"https://www.youtube.com/results?search_query=magnet+brains+{urllib.parse.quote_plus(query)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Extract initial data JSON
        match = re.search(r'var ytInitialData = ({.*?});</script>', html, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(1))
        # Walk JSON to find videoIds
        contents = (data.get("contents", {})
                       .get("twoColumnSearchResultsRenderer", {})
                       .get("primaryContents", {})
                       .get("sectionListRenderer", {})
                       .get("contents", []))
        for section in contents:
            items = (section.get("itemSectionRenderer", {}).get("contents", []))
            for item in items:
                vr = item.get("videoRenderer", {})
                if vr:
                    vid_id = vr.get("videoId")
                    # Check channel is Magnet Brains
                    channel = (vr.get("ownerText", {}).get("runs", [{}])[0].get("text", "") or
                               vr.get("longBylineText", {}).get("runs", [{}])[0].get("text", ""))
                    if "Magnet" in channel and vid_id:
                        return vid_id
                    elif vid_id:
                        return vid_id  # fallback: first result
        return None
    except Exception as e:
        return f"ERROR:{e}"

import urllib.parse

print("=== GRADE 11 ===")
for name, query in CHAPTERS_G11:
    vid_id = find_magnet_brains_id(query)
    print(f"  {name!r}: {vid_id!r}")
    time.sleep(0.5)

print("\n=== GRADE 12 ===")
for name, query in CHAPTERS_G12:
    vid_id = find_magnet_brains_id(query)
    print(f"  {name!r}: {vid_id!r}")
    time.sleep(0.5)

