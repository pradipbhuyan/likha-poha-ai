import sys, re

FILE = 'backend/app/data/resources.py'
with open(FILE, encoding='utf-8') as f:
    src = f.read()

G11_ENTRIES = [
    ("नमक का दरोगा", "नमक का दरोगा | Class 11 Hindi Aroh Ch 1 | Magnet Brains", "TL0_M2qWB9g"),
    ("मियाँ नसीरुद्दीन", "मियाँ नसीरुद्दीन | Class 11 Hindi Aroh Ch 2 | Magnet Brains", "U9GNH0LN_I0"),
    ("अपू के साथ ढाई साल", "अपू के साथ ढाई साल | Class 11 Hindi Aroh Ch 3 | Magnet Brains", "xE1x0FXsTC0"),
    ("विदाई-संभाषण", "विदाई संभाषण | Class 11 Hindi Aroh Ch 4 | Magnet Brains", "91pjJf5GuDQ"),
    ("गलता लोहा", "गलता लोहा | Class 11 Hindi Aroh Ch 5 | Magnet Brains", "KQfrb-ULT7g"),
    ("स्पीति में बारिश", "स्पीति में बारिश | Class 11 Hindi Aroh Ch 6 | Magnet Brains", "s5m-GfBYcHc"),
    ("रजनी", "रजनी | Class 11 Hindi Aroh Ch 7 | Magnet Brains", "_k9TN15OZGc"),
    ("जामुन का पेड़", "जामुन का पेड़ | Class 11 Hindi Aroh Ch 8 | Magnet Brains", "JrSzOUTEPNs"),
    ("भारत माता", "भारत माता | Class 11 Hindi Aroh Ch 9 | Magnet Brains", "tP-p7HDB8yA"),
    ("आत्मा का ताप", "आत्मा का ताप | Class 11 Hindi Aroh Ch 10 | Magnet Brains", "OU_IY9enHC8"),
    ("कबीर के पद", "कबीर के पद | Class 11 Hindi Aroh Kavya | Magnet Brains", "8nuezsYi2Cg"),
    ("पथिक", "पथिक | Class 11 Hindi Aroh Kavya | Magnet Brains", "sZWQOAA2p2Q"),
    ("वे आँखें", "वे आँखें | Class 11 Hindi Aroh Kavya | Magnet Brains", "gELNQeUIjpE"),
    ("घर की याद", "घर की याद | Class 11 Hindi Aroh Kavya | Magnet Brains", "11xmCStzwBs"),
    ("चंपा काले काले अच्छर नहीं चिन्हती", "चंपा काले काले | Class 11 Hindi Aroh Kavya | Magnet Brains", "KoAL0yqnzHI"),
    ("गजल", "गजल (Dushyant Kumar) | Class 11 Hindi Aroh Kavya | Magnet Brains", "6FlI3DIDsg0"),
    ("हे भूख! मत मचल", "हे भूख मत मचल | Class 11 Hindi Aroh Kavya | Magnet Brains", "imbaL8TwgMk"),
    ("सबसे खतरनाक", "सबसे खतरनाक | Class 11 Hindi Aroh Kavya | Magnet Brains", "fqtB-8eXC8I"),
    ("भारतीय गायिकाओं में बेजोड़ : लता मंगेशकर", "लता मंगेशकर | Class 11 Hindi Vitan Ch 1 | Magnet Brains", "XIexKf7h8DQ"),
    ("राजस्थान की रजत बूँदें", "राजस्थान की रजत बूँदें | Class 11 Hindi Vitan Ch 2 | Magnet Brains", "2boSuacLzTM"),
    ("आलो-आँधारि", "आलो आँधारि | Class 11 Hindi Vitan Ch 3 | Magnet Brains", "Do7gctB54E0"),
]

G12_ENTRIES = [
    ("आत्मपरिचय", "आत्मपरिचय / एक गीत | Class 12 Hindi Aroh Ch 1 | Magnet Brains", "mxioFBY5JP4"),
    ("पतंग", "पतंग | Class 12 Hindi Aroh Ch 2 | Magnet Brains", "SLEeJ9DeLJ8"),
    ("कविता के बहाने", "कविता के बहाने | Class 12 Hindi Aroh Ch 3 | Magnet Brains", "60uPLagY3y8"),
    ("कैमरे में बंद अपाहिज", "कैमरे में बंद अपाहिज | Class 12 Hindi Aroh Ch 4 | Magnet Brains", "wVwAfQmCvYQ"),
    ("सहर्ष स्वीकारा है", "सहर्ष स्वीकारा है | Class 12 Hindi Aroh Ch 5 | Magnet Brains", "YgS1KjNoBLE"),
    ("उषा", "उषा | Class 12 Hindi Aroh Ch 6 | Magnet Brains", "zXxfmci3nBI"),
    ("बादल राग", "बादल राग | Class 12 Hindi Aroh Ch 7 | Magnet Brains", "z2Zi6cv4VJU"),
    ("कवितावली", "कवितावली | Class 12 Hindi Aroh Ch 8 | Magnet Brains", "gcsjtvfcLrM"),
    ("रुबाइयाँ", "रुबाइयाँ और गजल | Class 12 Hindi Aroh Ch 9 | Magnet Brains", "D8BREPWfQec"),
    ("गज़ल", "रुबाइयाँ और गजल | Class 12 Hindi Aroh Ch 9 | Magnet Brains", "D8BREPWfQec"),
    ("भक्तिन", "भक्तिन | Class 12 Hindi Aroh Ch 11 | Magnet Brains", "lfMr0crAczk"),
    ("बाज़ार दर्शन", "बाज़ार दर्शन | Class 12 Hindi Aroh Ch 12 | Magnet Brains", "x4u2V8oJOU8"),
    ("काले मेघा पानी दे", "काले मेघा पानी दे | Class 12 Hindi Aroh Ch 13 | Magnet Brains", "IAmIGVFu4vA"),
    ("पहलवान की ढोलक", "पहलवान की ढोलक | Class 12 Hindi Aroh Ch 14 | Magnet Brains", "qwaiRSkP1LI"),
    ("शिरीष के फूल", "शिरीष के फूल | Class 12 Hindi Aroh Ch 17 | Magnet Brains", "MWIlbGoeIx8"),
    ("श्रम-विभाजन और जाति-प्रथा", "श्रम विभाजन और जाति प्रथा | Class 12 Hindi Aroh Ch 18 | Magnet Brains", "zr-fyEXOgv0"),
    ("मेरी कल्पना का आदर्श समाज", "श्रम विभाजन और जाति प्रथा | Class 12 Hindi Aroh Ch 18 | Magnet Brains", "zr-fyEXOgv0"),
    ("सिल्वर वेडिंग", "सिल्वर वेडिंग | Class 12 Hindi Vitan Ch 1 | Magnet Brains", "ELIxb3ctkoI"),
    ("जूझ", "जूझ | Class 12 Hindi Vitan Ch 2 | Magnet Brains", "h-540EgMP4c"),
    ("अतीत में दबे पाँव", "अतीत में दबे पाँव | Class 12 Hindi Vitan Ch 3 | Magnet Brains", "mFC7ygJ27cU"),
    ("डायरी के पन्ने", "डायरी के पन्ने | Class 12 Hindi Vitan Ch 4 | Magnet Brains", "aDgDYnRfuss"),
]


def build_block(entries):
    lines = ['    "Hindi": {']
    for key, title, vid_id in entries:
        url = "https://www.youtube.com/watch?v=" + vid_id
        lines.append(f'        "{key}": [{{"title": "{title}", "type": "youtube", "url": "{url}"}}],')
    lines.append('    },')
    return "\n" + "\n".join(lines) + "\n"


G11_BLOCK = build_block(G11_ENTRIES)
G12_BLOCK = build_block(G12_ENTRIES)

# Find end of G11 English section
G11_ANCHOR = (
    '"url": "https://www.youtube.com/results?search_query='
    'magnet+brains+class+11+english+writing+skills"},\n'
    '        ],\n'
    '    },\n'
    '}\n'
    '\n'
    '\n'
    '\n'
    '# \u2500\u2500 Grade 12 resources'
)
G11_NEW = (
    '"url": "https://www.youtube.com/results?search_query='
    'magnet+brains+class+11+english+writing+skills"},\n'
    '        ],\n'
    '    },'
    + G11_BLOCK
    + '}\n'
    '\n'
    '\n'
    '\n'
    '# \u2500\u2500 Grade 12 resources'
)

if G11_ANCHOR in src:
    src = src.replace(G11_ANCHOR, G11_NEW, 1)
    print("G11 OK")
else:
    idx = src.find("magnet+brains+class+11+english+writing+skills")
    print("G11 MISS - context:", repr(src[idx:idx+300]))

# Find end of G12 English section
G12_ANCHOR = (
    '"url": "https://www.youtube.com/results?search_query='
    'magnet+brains+class+12+english+writing+skills"},\n'
    '        ],\n'
    '    },\n'
    '}\n'
    '\n'
    '# \u2500\u2500 Grade-aware resource lookup'
)
G12_NEW = (
    '"url": "https://www.youtube.com/results?search_query='
    'magnet+brains+class+12+english+writing+skills"},\n'
    '        ],\n'
    '    },'
    + G12_BLOCK
    + '}\n'
    '\n'
    '# \u2500\u2500 Grade-aware resource lookup'
)

if G12_ANCHOR in src:
    src = src.replace(G12_ANCHOR, G12_NEW, 1)
    print("G12 OK")
else:
    idx = src.find("magnet+brains+class+12+english+writing+skills")
    print("G12 MISS - context:", repr(src[idx:idx+300]))

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(src)
print("Saved.")

# Verify
sys.path.insert(0, 'backend')
import importlib
import app.data.resources as r
importlib.reload(r)
from app.data.resources import get_learning_resources

CHECKS = [
    ('Hindi', 'नमक का दरोगा', 'Grade 11'),
    ('Hindi', 'कबीर के पद', 'Grade 11'),
    ('Hindi', 'आलो-आँधारि', 'Grade 11'),
    ('Hindi', 'आत्मपरिचय', 'Grade 12'),
    ('Hindi', 'भक्तिन', 'Grade 12'),
    ('Hindi', 'डायरी के पन्ने', 'Grade 12'),
]
all_ok = True
for subj, chap, grade in CHECKS:
    res = get_learning_resources(subj, chap, grade)
    ok = res and 'youtube.com/watch' in res[0].get('url', '')
    status = 'OK' if ok else 'FAIL'
    if not ok:
        all_ok = False
    vid = res[0]['url'].split('=')[-1] if ok else '???'
    print(f"  [{status}] {grade} {chap} -> {vid}")
print("All OK!" if all_ok else "SOME FAILED!")
