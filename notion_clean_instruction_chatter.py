import json
import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
CACHE = ROOT / '.notion-cache'
CACHE.mkdir(exist_ok=True)
ENV = os.environ.copy()
ENV['XDG_CACHE_HOME'] = str(CACHE.resolve())
NTN = r'C:\Users\dnorm\AppData\Roaming\npm\ntn.cmd'
PRODUCTION_DS = '3c0c8498-b23f-81f9-9620-000b7035ed71'
CONTENT_CAL_DS = '3c0c8498-b23f-81db-8b12-000bb086e742'
MASTER_PAGES = [
    '3c0c8498-b23f-81a9-af56-cb918e4cb648',  # visible child under Batch 1 Canva Design Briefs
    '3c0c8498-b23f-813f-8a18-ec9eb20f7f62',  # earlier misplaced duplicate, kept clean if user sees it
]
BASE = Path('design-references/social-launch/batch1-canva-templates')
CANVA = json.loads((BASE / 'canva-batch1-final-designs.json').read_text(encoding='utf-8'))


def run(args, input_text=None):
    if args and args[0] == 'ntn':
        args = [NTN] + args[1:]
    p = subprocess.run(args, input=input_text, text=True, capture_output=True, env=ENV, shell=False, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        raise RuntimeError(f"command failed {args}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p.stdout


def query(ds):
    return json.loads(run(['ntn', 'datasources', 'query', ds, '--limit', '100', '--json'])).get('results', [])


def title_from_prop(prop):
    return ''.join(t.get('plain_text','') for t in prop.get('title', []))


def rich_text_text(prop):
    return ''.join(t.get('plain_text','') for t in prop.get('rich_text', []))


def rt(text):
    return [{'type': 'text', 'text': {'content': text[i:i+1900]}} for i in range(0, len(text), 1900)] if text else []


def patch_page(page_id, props):
    body = {'properties': props}
    path = ROOT / f'.notion-clean-{page_id}.json'
    path.write_text(json.dumps(body, indent=2), encoding='utf-8')
    try:
        return run(['ntn', 'api', f'v1/pages/{page_id}', '-X', 'PATCH', '--data', '@' + str(path)])
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def clean_before_marker(text):
    marker = 'Final Canva design wired'
    if marker in text:
        return text.split(marker)[0].rstrip()
    return text

# Production Queue has no URL field, so keep only a tiny asset pointer in Reviewer Notes, not workflow/instruction chatter.
prod_rows = query(PRODUCTION_DS)
prod_cleaned = []
for r in prod_rows:
    props = r.get('properties', {})
    title = title_from_prop(props.get('Post / Asset', {}))
    if not title.startswith(tuple(f'Day {i} ' for i in range(1, 8))):
        continue
    existing = clean_before_marker(rich_text_text(props.get('Reviewer Notes', {})))
    # Match final Canva item by day number.
    day_num = int(title.split(' ')[1])
    item = CANVA[5 + day_num]  # Day 1 starts at index 6
    clean_link = f"Canva edit link: {item['edit_url']}"
    combined = (existing.rstrip() + '\n\n' + clean_link).strip() if existing else clean_link
    patch_page(r['id'], {'Reviewer Notes': {'rich_text': rt(combined)}})
    prod_cleaned.append(title)

# Content Calendar has Asset Link, so remove the added notes chatter and leave the link in the proper field.
cal_rows = query(CONTENT_CAL_DS)
cal_cleaned = []
for r in cal_rows:
    props = r.get('properties', {})
    title = title_from_prop(props.get('Post Title', {}))
    if not title.startswith(tuple(f'Day {i} ' for i in range(1, 8))):
        continue
    cleaned_notes = clean_before_marker(rich_text_text(props.get('Notes', {})))
    patch_page(r['id'], {'Notes': {'rich_text': rt(cleaned_notes)}})
    cal_cleaned.append(title)

# Replace master pages with a clean asset index only: no process instructions, no cleanup commands, no caveats.
lines = [
    '# NamEngine Batch 1 Social Launch',
    '',
    '## Final Canva Designs',
    '',
]
for i, item in enumerate(CANVA, 1):
    lines.extend([
        f"### {i}. {item['title']}",
        f"- Edit: {item['edit_url']}",
        f"- View: {item['view_url']}",
        '',
    ])
clean_master_content = '\n'.join(lines)
for page_id in MASTER_PAGES:
    run(['ntn', 'pages', 'update', page_id], input_text=clean_master_content)

print(json.dumps({
    'production_queue_cleaned': prod_cleaned,
    'content_calendar_cleaned': cal_cleaned,
    'master_pages_cleaned': MASTER_PAGES,
}, indent=2))
