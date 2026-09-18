import json
from pathlib import Path

base = Path('design-references/social-launch/batch1-canva-templates')
items = json.loads((base / 'canva-batch1-logo-corrected-designs.json').read_text(encoding='utf-8'))
md = [
    '# NamEngine Batch 1 Canva Designs — LOGO Corrected',
    '',
    f'Created {len(items)} logo-corrected Canva designs via Canva Connect API.',
    'Use these instead of the earlier proof/original/QA-fixed batches.',
    '',
]
html = ['<!doctype html><meta charset="utf-8"><title>NamEngine LOGO Corrected Canva Links</title>']
html.append('<style>body{font-family:system-ui;margin:40px;max-width:960px;color:#0D2540}li{margin:16px 0}a{font-size:18px;color:#6d28d9}small{color:#607086}.warn{background:#fff3cd;border:1px solid #ffe08a;padding:12px 16px;border-radius:10px}</style>')
html.append('<h1>NamEngine Batch 1 Canva Designs — LOGO Corrected</h1><p class="warn">Use these links. Ignore earlier proof/original/QA-fixed batches.</p><ol>')
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
(base / 'CANVA_LOGO_CORRECTED_LINKS.md').write_text('\n'.join(md), encoding='utf-8')
(base / 'CANVA_LOGO_CORRECTED_LINKS.html').write_text('\n'.join(html), encoding='utf-8')
print(base / 'CANVA_LOGO_CORRECTED_LINKS.html')
