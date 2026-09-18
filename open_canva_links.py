import json
import os
from pathlib import Path

base = Path('design-references/social-launch/batch1-canva-templates')
items = json.loads((base / 'canva-batch1-created-designs.json').read_text(encoding='utf-8'))
html = ['<!doctype html><meta charset="utf-8"><title>NamEngine Canva Links</title>']
html.append('<style>body{font-family:system-ui;margin:40px;max-width:900px}li{margin:14px 0}a{font-size:18px}</style>')
html.append('<h1>NamEngine Batch 1 Canva Designs</h1><p>Click Edit to open each Canva design.</p><ol>')
for item in items:
    html.append(f"<li><strong>{item['title']}</strong><br><a href='{item['edit_url']}'>Edit in Canva</a> &nbsp; <a href='{item['view_url']}'>View</a><br><small>{item['design_id']}</small></li>")
html.append('</ol>')
out = base / 'CANVA_LINKS.html'
out.write_text('\n'.join(html), encoding='utf-8')
os.startfile(str(out.resolve()))
print(out)
