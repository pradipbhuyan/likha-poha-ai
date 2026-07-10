#!/usr/bin/env python3
"""
Step-by-step trace: parseSections + getRenderableContent for Grade 5 English Chapter 1.
Shows EXACTLY what content is rendered vs discarded for every section.
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.grade_db_router import get_content_db

# ── Exact replica of the JS logic in LessonSections.jsx ──────────────────────

def detectHeading(line):
    # Pattern 1+2: numbered heading (## 1. Title or **1. Title**)
    m = re.match(r'^#{0,3}\s*\**\s*(\d+\.\s+.+?)\**\s*$', line)
    if m:
        captured = re.sub(r'^\d+\.\s*', '', m.group(1)).strip()
        if len(captured) <= 65 and not re.search(r'[.?!]$', captured):
            return ('P1', captured)
    # Pattern 3: ## Heading
    m = re.match(r'^#{1,3}\s+(.+)$', line)
    if m:
        t = m.group(1).replace('**', '').strip()
        if len(t) >= 3:
            return ('P3', t)
    # Pattern 5: Step N: Title  (no terminal punctuation)
    m = re.match(
        r'^(Step\s+\d+|Question|Summary|Introduction|Conclusion|Common\s+Mistake|'
        r'Quick\s+Check|What\s+You\s+Will\s+Learn|Worked\s+Example|Overview)\s*:\s*(.*)$',
        line, re.I)
    if m:
        label = m.group(1).strip()
        rest  = (m.group(2) or '').strip()
        combined = f'{label}: {rest}' if rest else label
        if 3 <= len(combined) <= 70 and not re.search(r'[.?!]$', combined):
            return ('P5', combined)
    # Pattern 4: **Bold heading**
    m = re.match(r'^\*\*(.+?)\*\*:?\s*$', line)
    if m:
        t = m.group(1).strip()
        if 4 <= len(t) <= 80 and not re.match(r'^[a-z]', t):
            return ('P4', t)
    return None


def parseSections(markdown):
    lines = markdown.split('\n')
    sections = []
    cur_title = None
    cur_pattern = None
    cur_content = []
    for line in lines:
        result = detectHeading(line)
        if result:
            pat, title = result
            if ''.join(cur_content).strip():
                sections.append({
                    'title':   cur_title or 'Introduction',
                    'pattern': cur_pattern or 'none',
                    'content': '\n'.join(cur_content),
                })
            cur_title   = title
            cur_pattern = pat
            cur_content = []
        else:
            cur_content.append(line)
    if ''.join(cur_content).strip():
        sections.append({
            'title':   cur_title or 'Introduction',
            'pattern': cur_pattern or 'none',
            'content': '\n'.join(cur_content),
        })
    return sections


def cleanQuestionText(text):
    t = re.sub(r'```[\s\S]*?```', '', text)
    t = re.sub(r'[#*_`>]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def getQuestionPrompt(section):
    content = cleanQuestionText(section['content'])
    # Labelled question match
    m = re.search(
        r'(?:^|\s)(?:question|quick check(?: question)?|try this|your turn)\s*:\s*'
        r'([\s\S]+?)(?=(?:\s(?:step\s*\d+|answer|hint|solution)\s*:)|$)',
        content, re.I)
    if m:
        prompt = m.group(1).strip()
        if not re.search(r'^would you like', prompt, re.I):
            return prompt
    title = section['title'].lower()
    if any(k in title for k in ['question', 'quick check', 'self check', 'practice']):
        return content
    m = re.search(r'([^.!?]*\?)\s*$', content)
    if m and len(m.group(1).strip()) >= 12:
        return m.group(1).strip()
    return ''


def getRenderableContent(section, qp):
    if not qp:
        return section['content']

    # KEY FIX: if "Question:" is followed by a solution (Step N:, Answer:, etc.)
    # → this is a WORKED EXAMPLE → show full body (question + solution both visible)
    parts = re.split(r'question\s*:', section['content'], maxsplit=1, flags=re.I)
    after_question = parts[1] if len(parts) > 1 else ''
    has_solution = bool(re.search(
        r'(?:step\s+\d+|answer\s*:|solution\s*:|therefore|hint\s*:)',
        after_question, re.I))
    if has_solution:
        return section['content']  # Show everything — don't discard the solution

    # Try stripping labelled question block
    stripped = re.sub(
        r'(?:^|\n)\s*(?:[-*]\s*)?(?:\*\*)?'
        r'(?:question|quick check(?: question)?|try this|your turn)'
        r'(?:\*\*)?\s*:\s*[\s\S]*$',
        '', section['content'], flags=re.I)
    if stripped != section['content']:
        return stripped.strip()
    # Section is a question section → render nothing (question shows in inline box)
    title = section['title'].lower()
    if any(k in title for k in ['question', 'quick check', 'self check', 'practice']):
        return ''
    # Strip trailing question
    ep = re.escape(qp)
    return re.sub(ep + r'\s*$', '', section['content']).strip()


# ── Run the audit ─────────────────────────────────────────────────────────────

def main():
    db = get_content_db('Grade 5')
    chapter = "1. Papa's Spectacles"
    steps   = ['What We Learn', 'Worked Examples', 'Recap']

    print('=' * 70)
    print(f'PARSER TRACE — Grade 5 · English · {chapter}')
    print('=' * 70)

    for step in steps:
        resp = (db.table('lesson_cache')
                  .select('lesson_content')
                  .eq('grade', 'Grade 5')
                  .eq('subject', 'English')
                  .eq('chapter', chapter)
                  .eq('step_title', step)
                  .eq('status', 'active')
                  .execute())
        if not resp.data:
            print(f'\n--- {step}: NO ACTIVE CACHE ENTRY ---\n')
            continue

        content = resp.data[0]['lesson_content']
        total_words = len(content.split())
        sections    = parseSections(content)

        print(f'\n{"─"*70}')
        print(f'STEP: {step}  ({total_words} total words, {len(sections)} section(s) detected)')
        print(f'{"─"*70}')

        total_rendered  = 0
        total_discarded = 0

        for i, s in enumerate(sections):
            qp = getQuestionPrompt(s)
            rc = getRenderableContent(s, qp)
            sw = len(s['content'].split())
            rw = len(rc.split()) if rc else 0
            dw = sw - rw
            total_rendered  += rw
            total_discarded += dw

            flag = '  ⚠️  PARTIAL DISCARD' if 0 < dw < sw else ('  ❌ ALL DISCARDED' if dw == sw and sw > 0 else '')
            print(f'\n  Section {i+1}: "{s["title"]}"  [detected via Pattern {s["pattern"]}]')
            print(f'    Stored:   {sw} words')
            print(f'    Rendered: {rw} words{flag}')
            if dw > 0:
                print(f'    Discarded:{dw} words')
                # Show WHY it was discarded
                if qp:
                    print(f'    REASON: getQuestionPrompt() found a question ({len(qp)} chars):')
                    print(f'      Q: {repr(qp[:120])}')
                    stripped = re.sub(
                        r'(?:^|\n)\s*(?:[-*]\s*)?(?:\*\*)?'
                        r'(?:question|quick check(?: question)?|try this|your turn)'
                        r'(?:\*\*)?\s*:\s*[\s\S]*$',
                        '', s['content'], flags=re.I)
                    if stripped != s['content']:
                        print(f'    STRIP ACTION: "question:" label found → stripped everything after it')
                    elif any(k in s['title'].lower() for k in ['question','quick check','self check','practice']):
                        print(f'    STRIP ACTION: section title contains "question" → rendered EMPTY (question in inline box)')
                    else:
                        print(f'    STRIP ACTION: trailing question stripped from content')
            if rc:
                print(f'    First 120 chars rendered: {repr(rc[:120])}')

        pct = round(total_rendered / total_words * 100) if total_words else 0
        print(f'\n  ► STEP SUMMARY: {total_rendered}/{total_words} words rendered ({pct}%)')
        if total_discarded > 0:
            print(f'  ► DISCARDED:    {total_discarded} words NOT shown to student')

    print('\n' + '=' * 70)


if __name__ == '__main__':
    main()
