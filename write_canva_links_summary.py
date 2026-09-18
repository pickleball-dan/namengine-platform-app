import json
from pathlib import Path

base = Path('design-references/social-launch/batch1-canva-templates')
items = json.loads((base / 'canva-batch1-created-designs.json').read_text(encoding='utf-8'))
lines = [
    '# NamEngine Batch 1 Canva Designs',
    '',
    f'Created {len(items)} Canva designs via Canva Connect API.',
    '',
]
for i, item in enumerate(items, 1):
    lines.extend([
        f"## {i}. {item['title']}",
        f"- File: `{item['file']}`",
        f"- Canva design ID: `{item['design_id']}`",
        f"- Edit: {item['edit_url']}",
        f"- View: {item['view_url']}",
        '',
    ])
(base / 'CANVA_LINKS.md').write_text('\n'.join(lines), encoding='utf-8')
print(base / 'CANVA_LINKS.md')
