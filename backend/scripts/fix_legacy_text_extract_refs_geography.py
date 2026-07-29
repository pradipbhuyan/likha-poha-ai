import sys, re, json
sys.path.insert(0, '/Users/a0247716/Pradips_Project/cbse-tutor-platform/backend')
from app.services.auth_service import admin_client
from app.services.grade_db_router import get_content_db

_EXTRACT_REF_RE = re.compile(r'```extract-ref\n(\{.*?\})\n```', re.S)

EXERCISE_PAGE = {323: 11, 324: 6, 325: 11, 326: 11, 327: 15, 328: 12, 329: 12}
CHAPTERS = [
  ('Chapter 1: Resources and Development', 323),
  ('Chapter 2: Forest and Wildlife Resources', 324),
  ('Chapter 3: Water Resources', 325),
  ('Chapter 4: Agriculture', 326),
  ('Chapter 5: Minerals and Energy Resources', 327),
  ('Chapter 6: Manufacturing Industries', 328),
  ('Chapter 7: Lifelines of National Economy', 329),
]

def fetch_asset_url(document_id, page_number):
    r = admin_client.table('rag_visual_assets').select('asset_url').eq('document_id', document_id).eq('page_number', page_number).limit(1).execute()
    if r.data:
        return r.data[0]['asset_url']
    return None

db = get_content_db('Grade 10')
total_fixed = 0
total_blocks = 0
for chapter, doc_id in CHAPTERS:
    page = EXERCISE_PAGE[doc_id]
    asset_url = fetch_asset_url(doc_id, page)
    if not asset_url:
        print('  [skip]', chapter, '- no asset for page', page)
        continue
    rows = db.table('lesson_cache').select('id,step_title,lesson_content').eq('grade','Grade 10').eq('subject','Social Science').eq('chapter', chapter).execute().data
    for row in rows:
        text = row['lesson_content'] or ''
        def _replace(m):
            global total_blocks
            raw_json = m.group(1)
            try:
                d = json.loads(raw_json)
            except Exception:
                return m.group(0)
            if 'asset_url' in d:
                return m.group(0)
            new_d = {'citation': d.get('citation',''), 'page_number': page, 'asset_url': asset_url}
            if d.get('note'):
                new_d['note'] = d['note']
            total_blocks += 1
            return '```extract-ref\n' + json.dumps(new_d, ensure_ascii=False) + '\n```'
        new_text, n = _EXTRACT_REF_RE.subn(_replace, text)
        if n > 0:
            db.table('lesson_cache').update({'lesson_content': new_text}).eq('id', row['id']).execute()
            total_fixed += 1
            print('  fixed', chapter, '|', row['step_title'], '-> ', n, 'block(s)')

print('\nTotal lesson_cache rows updated:', total_fixed)
print('Total extract-ref blocks converted:', total_blocks)

print('\nInvalidating chapter_doc caches...')
for chapter, doc_id in CHAPTERS:
    db.table('lesson_chapter_doc').delete().eq('grade','Grade 10').eq('subject','Social Science').eq('chapter', chapter).execute()
    print('  invalidated:', chapter)
print('Done.')
