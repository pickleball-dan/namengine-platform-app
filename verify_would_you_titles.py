import os, sys, requests
TOKEN=os.environ.get('NOTION_API_TOKEN')
VERSION=os.environ.get('NOTION_API_VERSION') or '2026-03-11'
BASE='https://api.notion.com/v1'
DS='3c0c8498-b23f-81db-8b12-000bb086e742'
headers={'Authorization':f'Bearer {TOKEN}','Notion-Version':VERSION,'Content-Type':'application/json'}
r=requests.post(f'{BASE}/data_sources/{DS}/query',headers=headers,json={'page_size':100},timeout=30)
r.raise_for_status()
for page in r.json()['results']:
    title=''.join(t['plain_text'] for t in page['properties']['Post Title']['title'])
    if 'Would You' in title or ' vs. ' in title:
        print(title)
