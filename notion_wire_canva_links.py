import json
import subprocess
import os
from pathlib import Path

ROOT = Path.cwd()
CACHE = ROOT / '.notion-cache'
CACHE.mkdir(exist_ok=True)
BASE = Path('design-references/social-launch/batch1-canva-templates')
CANVA = json.loads((BASE / 'canva-batch1-final-designs.json').read_text(encoding='utf-8'))

PRODUCTION_DS = '3c0c8498-b23f-81f9-9620-000b7035ed71'
CONTENT_CAL_DS = '3c0c8498-b23f-81db-8b12-000bb086e742'

DESIGN_PAGE_URL = 'https://app.notion.com/p/NamEngine-Batch-1-Social-Launch-3c0c8498b23f81a9af56cb918e4cb648'

ENV = os.environ.copy()
ENV['XDG_CACHE_HOME'] = str(CACHE.resolve())

NTN = r'C:\Users\dnorm\AppData\Roaming\npm\ntn.cmd'

def run(args, input_text=None):
    if args and args[0] == 'ntn':
        args = [NTN] + args[1:]
    p = subprocess.run(args, input=input_text, text=True, capture_output=True, env=ENV, shell=False, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        raise RuntimeError(f"command failed {args}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p.stdout

def query(ds):
    out = run(['ntn', 'datasources', 'query', ds, '--limit', '100', '--json'])
    return json.loads(out).get('results', [])

def title_from_prop(prop):
    return ''.join(t.get('plain_text','') for t in prop.get('title', []))

def rich_text_text(prop):
    return ''.join(t.get('plain_text','') for t in prop.get('rich_text', []))

def rt(text):
    # Notion rich_text content chunks max 2000 chars.
    return [{'type': 'text', 'text': {'content': text[i:i+1900]}} for i in range(0, len(text), 1900)] or []

def url_text(label, url):
    return {'type': 'text', 'text': {'content': label, 'link': {'url': url}}}

def patch_page(page_id, props):
    body = {'properties': props}
    path = ROOT / f'.notion-patch-{page_id}.json'
    path.write_text(json.dumps(body, indent=2), encoding='utf-8')
    try:
        return run(['ntn', 'api', f'v1/pages/{page_id}', '-X', 'PATCH', '--data', '@' + str(path)])
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

# Map final Canva assets to working rows.
# Using the final batch that user said is done; Day 07 has a note because a later local-only fix exists.
links = {
    'Day 1 — Why NamEngine Exists': CANVA[6],
    'Day 2 — If You Love Theodore': CANVA[7],
    'Day 3 — Arthur or August?': CANVA[8],
    'Day 4 — Name DNA: Margot': CANVA[9],
    'Day 5 — Nobody’s Talking About Conrad': CANVA[10],
    'Day 6 — Popularity Debate': CANVA[11],
    'Day 7 — Ten Classic Names Beyond the Obvious': CANVA[12],
}
# Some rows may use shorter names; match with normalized contains fallbacks.
fallbacks = [
    ('Day 1', CANVA[6]),
    ('Theodore', CANVA[7]),
    ('Arthur', CANVA[8]),
    ('Margot', CANVA[9]),
    ('Conrad', CANVA[10]),
    ('Popularity', CANVA[11]),
    ('Classic', CANVA[12]),
]

def pick(title):
    if title in links:
        return links[title]
    low = title.lower()
    for needle, item in fallbacks:
        if needle.lower() in low:
            return item
    return None

def canva_note(item, title):
    note = (
        f"Final Canva design wired {item['title']}\n"
        f"Edit: {item['edit_url']}\n"
        f"View: {item['view_url']}\n"
        f"Design ID: {item['design_id']}\n"
        f"Master asset page: {DESIGN_PAGE_URL}"
    )
    if 'day 07' in item['title'].lower() or 'classic' in title.lower():
        note += "\nNote: user said the Canva batch is done; local Day 07 source has a later card-content fix if we choose to replace this design later."
    return note

def update_production_queue():
    rows = query(PRODUCTION_DS)
    changed = []
    skipped = []
    for r in rows:
        props = r.get('properties', {})
        title = title_from_prop(props.get('Post / Asset', {}))
        item = pick(title)
        if not item:
            skipped.append(title)
            continue
        existing = rich_text_text(props.get('Reviewer Notes', {}))
        note = canva_note(item, title)
        combined = existing
        marker = 'Final Canva design wired'
        if marker in combined:
            before = combined.split(marker)[0].rstrip()
            combined = (before + '\n\n' + note).strip()
        else:
            combined = (combined.rstrip() + '\n\n' + note).strip()
        patch_page(r['id'], {
            'Reviewer Notes': {'rich_text': rt(combined)},
            'Status': {'status': {'name': 'Needs Review'}},
        })
        changed.append(title)
    return changed, skipped

def update_content_calendar():
    rows = query(CONTENT_CAL_DS)
    changed = []
    skipped = []
    for r in rows:
        props = r.get('properties', {})
        title = title_from_prop(props.get('Post Title', {}))
        item = pick(title)
        if not item:
            skipped.append(title)
            continue
        existing = rich_text_text(props.get('Notes', {}))
        note = canva_note(item, title)
        combined = existing
        marker = 'Final Canva design wired'
        if marker in combined:
            before = combined.split(marker)[0].rstrip()
            combined = (before + '\n\n' + note).strip()
        else:
            combined = (combined.rstrip() + '\n\n' + note).strip()
        page_props = {
            'Notes': {'rich_text': rt(combined)},
            'Status': {'status': {'name': 'Needs Review'}},
        }
        # Only set Asset Link if property exists.
        if 'Asset Link' in props:
            page_props['Asset Link'] = {'url': item['edit_url']}
        patch_page(r['id'], page_props)
        changed.append(title)
    return changed, skipped

if __name__ == '__main__':
    prod_changed, prod_skipped = update_production_queue()
    cal_changed, cal_skipped = update_content_calendar()
    print(json.dumps({
        'production_queue_updated': prod_changed,
        'production_queue_skipped': prod_skipped,
        'content_calendar_updated': cal_changed,
        'content_calendar_skipped': cal_skipped,
    }, indent=2))
