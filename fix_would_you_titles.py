import os, sys, time, requests

TOKEN = os.environ.get("NOTION_API_TOKEN")
VERSION = os.environ.get("NOTION_API_VERSION") or "2026-03-11"
BASE = "https://api.notion.com/v1"
CALENDAR_DS = "3c0c8498-b23f-81db-8b12-000bb086e742"
QUEUE_DS = "3c0c8498-b23f-81f9-9620-000b7035ed71"

if not TOKEN:
    print("Missing NOTION_API_TOKEN", file=sys.stderr)
    sys.exit(1)

headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": VERSION, "Content-Type": "application/json"}

def rich(s):
    return [{"type":"text", "text":{"content": s}}] if s else []

def title(s):
    return [{"type":"text", "text":{"content": s}}]

def query(ds):
    out=[]; cursor=None
    while True:
        payload={"page_size":100}
        if cursor: payload["start_cursor"] = cursor
        r=requests.post(f"{BASE}/data_sources/{ds}/query", headers=headers, json=payload, timeout=30)
        if r.status_code >= 400:
            print(r.status_code, r.text, file=sys.stderr); sys.exit(1)
        data=r.json(); out.extend(data.get("results", []))
        if not data.get("has_more"): break
        cursor=data.get("next_cursor")
    return out

def get_title(page, prop):
    vals = page["properties"][prop]["title"]
    return vals[0]["plain_text"] if vals else ""

def patch(page_id, props):
    r=requests.patch(f"{BASE}/pages/{page_id}", headers=headers, json={"properties": props}, timeout=30)
    if r.status_code >= 400:
        print("PATCH ERROR", page_id, r.status_code, r.text, file=sys.stderr); sys.exit(1)
    time.sleep(0.15)

calendar_updates = {
    "Day 9": {
        "Post Title": "Day 9 — Would You Name Them Maeve or Margot?",
        "Notes": "Preference prompt: Maeve or Margot? Keep it simple, fast, and instinctive.",
        "CTA": "Vote or comment: Maeve or Margot?",
    },
    "Day 17": {
        "Post Title": "Day 17 — Would You Name Them Felix or Finn?",
        "Notes": "Preference prompt: Felix or Finn? Keep it simple, fast, and instinctive.",
        "CTA": "Vote or comment: Felix or Finn?",
    },
}

updated=[]
for page in query(CALENDAR_DS):
    t=get_title(page, "Post Title")
    for prefix, vals in calendar_updates.items():
        if t.startswith(prefix + " ") or t.startswith(prefix + " —"):
            patch(page["id"], {
                "Post Title": {"title": title(vals["Post Title"])},
                "Notes": {"rich_text": rich(vals["Notes"])},
                "CTA": {"rich_text": rich(vals["CTA"])},
            })
            updated.append(vals["Post Title"])

# If future production queue entries for these days exist, update them too.
queue_updates = {
    "Day 9": {
        "Post / Asset": "Day 9 — Would You Name Them Maeve or Margot?",
        "Hook": "Maeve or Margot? No overthinking.",
        "Design Notes": "Use the standardized Would You Name Them format: “Maeve or Margot?” Story poll options: Maeve / Margot.",
    },
    "Day 17": {
        "Post / Asset": "Day 17 — Would You Name Them Felix or Finn?",
        "Hook": "Felix or Finn? No overthinking.",
        "Design Notes": "Use the standardized Would You Name Them format: “Felix or Finn?” Story poll options: Felix / Finn.",
    },
}
for page in query(QUEUE_DS):
    t=get_title(page, "Post / Asset")
    for prefix, vals in queue_updates.items():
        if t.startswith(prefix + " ") or t.startswith(prefix + " —"):
            patch(page["id"], {
                "Post / Asset": {"title": title(vals["Post / Asset"])},
                "Hook": {"rich_text": rich(vals["Hook"])},
                "Design Notes": {"rich_text": rich(vals["Design Notes"])},
            })
            updated.append(vals["Post / Asset"])

print({"updated": updated})
