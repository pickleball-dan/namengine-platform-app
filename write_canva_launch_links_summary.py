import json
from pathlib import Path

base = Path('design-references/social-launch/day1-7-launch-cards')
items = json.loads((base / 'canva-day1-7-launch-card-designs.json').read_text(encoding='utf-8'))

md = [
    '# NamEngine Day 1-7 Launch Cards — Canva Links',
    '',
    f'Created {len(items)} Canva designs via Canva Connect API.',
    '',
    'Use this latest short-name batch only. Older long-name batches can be deleted manually in Canva.',
    '',
]

html = ['<!doctype html><meta charset="utf-8"><title>NamEngine Day 1-7 Launch Canva Links</title>']
html.append('<style>body{font-family:system-ui;margin:40px;max-width:1040px;color:#0D2540;background:#FBF8F1}h1{font-size:32px}.note{background:#fff;border:1px solid #DDE3EC;border-radius:14px;padding:14px 18px;margin:18px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}li{margin:14px 0}a{color:#0F6BFF;font-weight:750}.meta{color:#607086;font-size:13px}</style>')
html.append('<h1>NamEngine Day 1-7 Launch Cards — Canva Links</h1>')
html.append(f'<div class="note">Created <strong>{len(items)}</strong> short-named Canva designs. Use this batch only; delete older draft batches manually.</div><div class="grid">')

for suffix, format_name in [('ig', 'Instagram 4x5'), ('tt', 'TikTok 9x16')]:
    filtered = [item for item in items if item['title'].endswith(suffix)]
    md.append(f'## {format_name}')
    html.append(f'<section><h2>{format_name}</h2><ol>')
    for item in filtered:
        title = item['title']
        md.extend([
            f'### {title}',
            f'- File: `{item["file"]}`',
            f'- Size: {item["width"]}×{item["height"]}',
            f'- Edit: {item["edit_url"]}',
            f'- View: {item["view_url"]}',
            '',
        ])
        html.append(f'<li><strong>{title}</strong><br><a href="{item["edit_url"]}">Edit in Canva</a> &nbsp; <a href="{item["view_url"]}">View</a><br><span class="meta">{item["file"]} · {item["width"]}×{item["height"]} · {item["design_id"]}</span></li>')
    html.append('</ol></section>')
    md.append('')
html.append('</div>')

(base / 'CANVA_DAY1_7_LAUNCH_LINKS.md').write_text('\n'.join(md), encoding='utf-8')
(base / 'CANVA_DAY1_7_LAUNCH_LINKS.html').write_text('\n'.join(html), encoding='utf-8')
print(base / 'CANVA_DAY1_7_LAUNCH_LINKS.html')
print(base / 'CANVA_DAY1_7_LAUNCH_LINKS.md')
