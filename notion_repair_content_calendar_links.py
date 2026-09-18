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
CONTENT_CAL_DS = '3c0c8498-b23f-81db-8b12-000bb086e742'

def run(args):
    if args and args[0] == 'ntn':
        args = [NTN] + args[1:]
    p = subprocess.run(args, text=True, capture_output=True, env=ENV, shell=False, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        raise RuntimeError(f"command failed {args}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p.stdout

def rt(text):
    return [{'type': 'text', 'text': {'content': text[i:i+1900]}} for i in range(0, len(text), 1900)] or []

def title_from_prop(prop):
    return ''.join(t.get('plain_text','') for t in prop.get('title', []))

def rich_text_text(prop):
    return ''.join(t.get('plain_text','') for t in prop.get('rich_text', []))

def patch_page(page_id, props):
    body = {'properties': props}
    path = ROOT / f'.notion-repair-{page_id}.json'
    path.write_text(json.dumps(body, indent=2), encoding='utf-8')
    try:
        return run(['ntn', 'api', f'v1/pages/{page_id}', '-X', 'PATCH', '--data', '@' + str(path)])
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

rows = json.loads(run(['ntn', 'datasources', 'query', CONTENT_CAL_DS, '--limit', '100', '--json'])).get('results', [])
allowed_prefixes = tuple(f'Day {i} ' for i in range(1, 8))
repaired = []
kept = []
skipped = []
for r in rows:
    props = r.get('properties', {})
    title = title_from_prop(props.get('Post Title', {}))
    if title.startswith(allowed_prefixes):
        kept.append(title)
        continue
    notes = rich_text_text(props.get('Notes', {}))
    marker = 'Final Canva design wired'
    if marker not in notes:
        skipped.append(title)
        continue
    cleaned = notes.split(marker)[0].rstrip()
    patch = {'Notes': {'rich_text': rt(cleaned)}}
    if 'Asset Link' in props:
        patch['Asset Link'] = {'url': None}
    # This database's original early rows were Ideas; revert only the accidental spillover.
    if 'Status' in props:
        patch['Status'] = {'status': {'name': 'Idea'}}
    patch_page(r['id'], patch)
    repaired.append(title)

print(json.dumps({'kept_days_1_to_7': kept, 'repaired_accidental_calendar_rows': repaired, 'skipped_clean_rows': skipped}, indent=2))
