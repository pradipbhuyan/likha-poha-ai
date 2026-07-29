"""
Add Grade 11 and Grade 12 Hindi chapters (Magnet Brains, verified Jul 2026)
to GRADE_11_RESOURCES and GRADE_12_RESOURCES in resources.py.
"""
import re

FILE = '/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend/app/data/resources.py'

with open(FILE, encoding='utf-8') as f:
    src = f.read()

# ── Grade 11 Hindi section to insert ────────────────────────────────────────
HINDI_G11 = '''\n    # ── HINDI ─────────────────────────────────────────────────────────────────
    "Hindi": {
        # Aroh Bhag 1 — Gadya Khand (Prose)
        "नमक का दरोगा": [{"title": "नमक का दरोगा | Class 11 Hindi Aroh Ch 1 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=TL0_M2qWB9g"}],
        "मियाँ नसीरुद्दीन": [{"title": "मियाँ नसीरुद्दीन | Class 11 Hindi Aroh Ch 2 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=U9GNH0LN_I0"}],
        "अपू के साथ ढाई साल": [{"title": "अपू के साथ ढाई साल | Class 11 Hindi Aroh Ch 3 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=xE1x0FXsTC0"}],
        "विदाई-संभाषण": [{"title": "विदाई संभाषण | Class 11 Hindi Aroh Ch 4 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=91pjJf5GuDQ"}],
        "गलता लोहा": [{"title": "गलता लोहा | Class 11 Hindi Aroh Ch 5 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=KQfrb-ULT7g"}],
        "स्पीति में बारिश": [{"title": "स्पीति में बारिश | Class 11 Hindi Aroh Ch 6 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=s5m-GfBYcHc"}],
        "रजनी": [{"title": "रजनी | Class 11 Hindi Aroh Ch 7 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=_k9TN15OZGc"}],
        "जामुन का पेड़": [{"title": "जामुन का पेड़ | Class 11 Hindi Aroh Ch 8 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=JrSzOUTEPNs"}],
        "भारत माता": [{"title": "भारत माता | Class 11 Hindi Aroh Ch 9 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=tP-p7HDB8yA"}],
        "आत्मा का ताप": [{"title": "आत्मा का ताप | Class 11 Hindi Aroh Ch 10 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=OU_IY9enHC8"}],
        # Aroh Bhag 1 — Kavya Khand (Poetry)
        "कबीर के पद": [{"title": "कबीर के पद | Class 11 Hindi Aroh Kavya | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=8nuezsYi2Cg"}],
        "पथिक": [{"title": "पथिक | Class 11 Hindi Aroh Kavya | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=sZWQOAA2p2Q"}],
        "वे आँखें": [{"title": "वे आँखें | Class 11 Hindi Aroh Kavya | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=gELNQeUIjpE"}],
        "घर की याद": [{"title": "घर की याद | Class 11 Hindi Aroh Kavya | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=11xmCStzwBs"}],
        "चंपा काले काले अच्छर नहीं चिन्हती": [{"title": "चंपा काले काले | Class 11 Hindi Aroh Kavya | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=KoAL0yqnzHI"}],
        "गजल": [{"title": "गजल (Dushyant Kumar) | Class 11 Hindi Aroh Kavya | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=6FlI3DIDsg0"}],
        "हे भूख! मत मचल": [{"title": "हे भूख मत मचल | Class 11 Hindi Aroh Kavya | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=imbaL8TwgMk"}],
        "सबसे खतरनाक": [{"title": "सबसे खतरनाक | Class 11 Hindi Aroh Kavya | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=fqtB-8eXC8I"}],
        # Vitan Bhag 1 (Supplementary)
        "भारतीय गायिकाओं में बेजोड़ : लता मंगेशकर": [{"title": "लता मंगेशकर | Class 11 Hindi Vitan Ch 1 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=XIexKf7h8DQ"}],
        "राजस्थान की रजत बूँदें": [{"title": "राजस्थान की रजत बूँदें | Class 11 Hindi Vitan Ch 2 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=2boSuacLzTM"}],
        "आलो-आँधारि": [{"title": "आलो आँधारि | Class 11 Hindi Vitan Ch 3 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=Do7gctB54E0"}],
    },
'''

# ── Grade 12 Hindi section to insert ────────────────────────────────────────
HINDI_G12 = '''\n    # ── HINDI ─────────────────────────────────────────────────────────────────
    "Hindi": {
        # Aroh Bhag 2 — Kavya Khand (Poetry)
        "आत्मपरिचय": [{"title": "आत्मपरिचय / एक गीत | Class 12 Hindi Aroh Ch 1 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=mxioFBY5JP4"}],
        "पतंग": [{"title": "पतंग | Class 12 Hindi Aroh Ch 2 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=SLEeJ9DeLJ8"}],
        "कविता के बहाने": [{"title": "कविता के बहाने | Class 12 Hindi Aroh Ch 3 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=60uPLagY3y8"}],
        "कैमरे में बंद अपाहिज": [{"title": "कैमरे में बंद अपाहिज | Class 12 Hindi Aroh Ch 4 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=wVwAfQmCvYQ"}],
        "सहर्ष स्वीकारा है": [{"title": "सहर्ष स्वीकारा है | Class 12 Hindi Aroh Ch 5 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=YgS1KjNoBLE"}],
        "उषा": [{"title": "उषा | Class 12 Hindi Aroh Ch 6 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=zXxfmci3nBI"}],
        "बादल राग": [{"title": "बादल राग | Class 12 Hindi Aroh Ch 7 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=z2Zi6cv4VJU"}],
        "कवितावली": [{"title": "कवितावली | Class 12 Hindi Aroh Ch 8 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=gcsjtvfcLrM"}],
        "रुबाइयाँ": [{"title": "रुबाइयाँ और गजल | Class 12 Hindi Aroh Ch 9 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=D8BREPWfQec"}],
        "गज़ल": [{"title": "रुबाइयाँ और गजल | Class 12 Hindi Aroh Ch 9 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=D8BREPWfQec"}],
        # Aroh Bhag 2 — Gadya Khand (Prose)
        "भक्तिन": [{"title": "भक्तिन | Class 12 Hindi Aroh Ch 11 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=lfMr0crAczk"}],
        "बाज़ार दर्शन": [{"title": "बाज़ार दर्शन | Class 12 Hindi Aroh Ch 12 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=x4u2V8oJOU8"}],
        "काले मेघा पानी दे": [{"title": "काले मेघा पानी दे | Class 12 Hindi Aroh Ch 13 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=IAmIGVFu4vA"}],
        "पहलवान की ढोलक": [{"title": "पहलवान की ढोलक | Class 12 Hindi Aroh Ch 14 | Magnet Brains", "type": "youtube", "url": "https://www.youtube.com/watch?v=qwaiRSkP1LI"}],
        "शिरीष के फूल": [{"title": "शिरीष के फूल
