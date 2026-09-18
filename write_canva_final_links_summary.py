import json
from pathlib import Path

base = Path('design-references/social-launch/batch1-canva-templates')
items = json.loads((base / 'canva-batch1-final-designs.json').read_text(encoding='utf-8'))
md = [
    '# NamEngine Batch 1 Canva Designs — FINAL',
    '',
    f'Created {len(items)} final Canva designs via Canva Connect API.',
    'Use these after deleting the earlier proof/original/QA/logo-corrected drafts.',
    '',
]
html = ['<!doctype html><meta charset="utf-8"><title>NamEngine FINAL Canva Links</title>']
html.append('<style>body{font-family:system-ui;margin:40px;max-width:960px;color:#0D2540}li{margin:16px 0}a{font-size:18px;color:#6d28d9}small{color:#607086}.ok{background:#eaf7ef;border:1px solid #bfe7cb;padding:12px 16px;border-radius:10px}</style>')
html.append('<h1>NamEngine Batch 1 Canva Designs — FINAL</h1><p class="ok">Use these FINAL links only. Latest color/layout/copy pass included.</p><ol>')
for i, item in enumerate(items, 1):
    md.extend([
        f"## {i}. {item['title']}",
        f"- File: `{item['file']}`",
        f"- Canva design ID: `{item['design_id']}`",
        f"- Edit: {item['edit_url']}",
        f"- View: {item['view_url']}",
        '',
    ])
    html.append(f"<li><strong>{item['title']}</strong><br><a href='{item['edit_url']}'>Edit in Canva</a> &nbsp; <a href='{item['view_url']}'>View</a><br><small>{item['design_id']}</small></li>")
html.append('</ol>')
(base / 'CANVA_FINAL_LINKS.md').write_text('\n'.join(md), encoding='utf-8')
(base / 'CANVA_FINAL_LINKS.html').write_text('\n'.join(html), encoding='utf-8')
print(base / 'CANVA_FINAL_LINKS.html')
