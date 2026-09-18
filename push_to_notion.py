"""Push NamEngine launch content to Notion Content Calendar."""
import os, json, subprocess, sys

DB_ID = "3c0c8498-b23f-817b-9b89-c79ece48db31"

# Vertical option IDs from database schema
VERTICAL_BABY     = "213b7ae7-c32b-4b58-b987-899271025070"
VERTICAL_PET      = "408ca4bb-c297-445d-ad82-d3f41a0d886c"
VERTICAL_BUSINESS = "d3978a95-6882-423c-a7a7-a629e35dbddd"

# Platform option IDs
PLATFORM_IG    = "4f1ff3f9-9a8e-405b-b288-a0d464433160"
PLATFORM_TIKTOK = "8926985a-70e4-4dcd-8308-ce236bf6b4a7"

# Status option IDs
STATUS_NEEDS_REVIEW = "2213dbe6-64fa-4c89-aacb-c36e4390dcd8"

# Objective option IDs (from existing entries)
OBJ_AWARENESS = "39f33c37-bc3d-4398-ae4c-d62f9d39ebb0"
OBJ_SAVES     = "e586dee5-ea63-4f65-b939-da1863b13914"
OBJ_PARTICIP  = "76b61fea-60f8-4d69-80db-0a0c3f7f32ec"
OBJ_AUTHORITY = "eab55774-a9a1-472a-8515-285cd288b7f0"

def notion_patch(page_id, properties):
    payload = json.dumps({"properties": properties})
    result = subprocess.run(
        ["ntn", "api", f"v1/pages/{page_id}", "-X", "PATCH", "--data", payload],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"PATCH {page_id} FAILED: {result.stderr[:200]}")
    else:
        print(f"PATCH {page_id} OK")
    return result.returncode == 0

def notion_create(properties):
    payload = json.dumps({
        "parent": {"database_id": DB_ID},
        "properties": properties
    })
    result = subprocess.run(
        ["ntn", "api", "v1/pages", "-X", "POST", "--data", payload],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"CREATE FAILED: {result.stderr[:300]}")
        return None
    data = json.loads(result.stdout)
    page_id = data.get("id", "")
    print(f"CREATE OK: {page_id}")
    return page_id

def title_prop(text):
    return {"title": [{"text": {"content": text}}]}

def date_prop(date_str):
    return {"date": {"start": date_str}}

def verticals_prop(vertical_ids):
    return {"multi_select": [{"id": v} for v in vertical_ids]}

def platforms_prop(platform_ids):
    return {"multi_select": [{"id": p} for p in platform_ids]}

def status_prop(status_id):
    return {"status": {"id": status_id}}

def select_prop(option_id):
    return {"select": {"id": option_id}}

def text_prop(text):
    return {"rich_text": [{"text": {"content": text[:2000]}}]}

IG_TT = [PLATFORM_IG, PLATFORM_TIKTOK]
ALL_VERTS = [VERTICAL_BABY, VERTICAL_PET, VERTICAL_BUSINESS]

# ── EXISTING PAGE IDs ──────────────────────────────────────────────────────────
EXISTING = {
    "day1":  "3c0c8498-b23f-8121-a037-d05c45496141",  # Why NamEngine Exists
    "day2":  "3c0c8498-b23f-8125-a04e-fc47f1517885",  # If You Love Theodore
    "day3":  "3c0c8498-b23f-8160-bf97-fcf17c6dfc41",  # Arthur or August → Day 8
    "day4":  "3c0c8498-b23f-8192-98cd-e3e14897e049",  # Name DNA: Margot → Day 5
    "day5":  "3c0c8498-b23f-818f-9b96-c8ae255bf115",  # Conrad → Day 11
    "day6":  "3c0c8498-b23f-81ef-95e5-c360913d1d93",  # Popularity Debate → Day 14
    "day7":  "3c0c8498-b23f-8149-9d28-d0dd34eef35f",  # Sunday Name List → Day 7
}

print("=== Updating existing posts with dates and corrected verticals ===")

# Day 1 — Why NamEngine Exists → Sep 10 | All verticals
notion_patch(EXISTING["day1"], {
    "Date": date_prop("2026-09-10"),
    "Vertical": verticals_prop(ALL_VERTS),
    "Platform": platforms_prop(IG_TT),
})

# Day 2 — If You Love Theodore → Sep 12 | Baby
notion_patch(EXISTING["day2"], {
    "Date": date_prop("2026-09-12"),
    "Platform": platforms_prop(IG_TT),
})

# Day 5 (was Day 4) — Name DNA: Margot → Sep 19 | Baby
notion_patch(EXISTING["day4"], {
    "Date": date_prop("2026-09-19"),
    "Platform": platforms_prop(IG_TT),
})

# Day 7 — Sunday Name List → Sep 24 | Baby
notion_patch(EXISTING["day7"], {
    "Date": date_prop("2026-09-24"),
    "Platform": platforms_prop(IG_TT),
})

# Day 8 (was Day 3) — Arthur or August → Sep 26 | Baby
notion_patch(EXISTING["day3"], {
    "Date": date_prop("2026-09-26"),
    "Platform": platforms_prop(IG_TT),
})

# Day 11 (was Day 5) — Nobody's Talking About: Conrad → Oct 3 | Baby
notion_patch(EXISTING["day5"], {
    "Date": date_prop("2026-10-03"),
    "Platform": platforms_prop(IG_TT),
})

# Day 14 (was Day 6) — Popularity Debate → Oct 10 | Baby + Pet
notion_patch(EXISTING["day6"], {
    "Date": date_prop("2026-10-10"),
    "Vertical": verticals_prop([VERTICAL_BABY, VERTICAL_PET]),
    "Platform": platforms_prop(IG_TT),
})

print("\n=== Creating new posts ===")

# POST 0 — We're Live — Sep 8
notion_create({
    "Post Title": title_prop("Post 0 — We're Live: NamEngine for Baby, Pet, and Business"),
    "Date": date_prop("2026-09-08"),
    "Vertical": verticals_prop(ALL_VERTS),
    "Platform": platforms_prop(IG_TT),
    "Status": status_prop(STATUS_NEEDS_REVIEW),
    "Objective": select_prop(OBJ_AWARENESS),
    "CTA": text_prop("Try your free first list at nam-engine.com."),
    "Notes": text_prop(
        "Hook: Finding names isn't the problem. Finding YOUR name is.\n\n"
        "Caption: A name has to do more than sound good. It has to feel right in your mouth. Fit the life it's entering. Carry a little meaning without explaining itself to everyone in the room.\n\n"
        "NamEngine is live today for three kinds of naming decisions:\n"
        "- Baby names with depth, style, and emotional fit\n"
        "- Pet names that feel personal, not pulled from the same top-ten list\n"
        "- Business names that sound credible before you explain the idea\n\n"
        "Start with a free first list. Unlock the full experience for $4.99.\n\n"
        "Baby. Pet. Business. One engine for names that feels considered.\n\n"
        "Finding names isn't the problem. Finding YOUR name is.\n\nnam-engine.com\n\n"
        "Reel VO: Naming is strange because the problem is never that there aren't enough options. "
        "There are thousands. The problem is finding the one that feels like it already belonged to you. "
        "Today, NamEngine is live for baby names, pet names, and business names. "
        "Start with a free first list, then unlock the full experience for $4.99."
    ),
})

# DAY 3 — If You Love Milo (Pet) — Sep 15
notion_create({
    "Post Title": title_prop("Day 3 — If You Love Milo But Want Something Less Common"),
    "Date": date_prop("2026-09-15"),
    "Vertical": verticals_prop([VERTICAL_PET]),
    "Platform": platforms_prop(IG_TT),
    "Status": status_prop(STATUS_NEEDS_REVIEW),
    "Objective": select_prop(OBJ_SAVES),
    "CTA": text_prop("Save this list, or try a free first pet name list at nam-engine.com."),
    "Notes": text_prop(
        "Hook: If you love Milo but want something a little less expected.\n\n"
        "Caption: Milo works for a reason — warm, easy, playful without being silly, soft enough for a cat but lively enough for a dog. "
        "The only problem is that everyone else noticed too.\n\n"
        "Five names with a similar spirit:\n"
        "Otis — gentle, soulful, and slightly old-record-store charming.\n"
        "Remy — quick, clever, and polished without feeling precious.\n"
        "Arlo — relaxed, musical, and sunny; familiar but still distinctive.\n"
        "Nico — crisp, affectionate, and effortlessly cool.\n"
        "Hugo — sturdy, warm, and a little storybook without tipping into costume.\n\n"
        "Finding names isn't the problem. Finding YOUR name is.\n\n"
        "Reel VO: If you love the name Milo for a pet, you're not alone. It's friendly, bright, and easy to say, "
        "which is exactly why it's everywhere. Try Otis, Remy, Arlo, Nico, or Hugo instead."
    ),
})

# DAY 4 — The Business Name Gut Check — Sep 17
notion_create({
    "Post Title": title_prop("Day 4 — The Business Name Gut Check"),
    "Date": date_prop("2026-09-17"),
    "Vertical": verticals_prop([VERTICAL_BUSINESS]),
    "Platform": platforms_prop(IG_TT),
    "Status": status_prop(STATUS_NEEDS_REVIEW),
    "Objective": select_prop(OBJ_AUTHORITY),
    "CTA": text_prop("Find your business name through NamEngine at nam-engine.com."),
    "Notes": text_prop(
        "Hook: You know a great business name when you hear one. Here's what makes it stick.\n\n"
        "Caption: A strong business name usually doesn't need a paragraph of defense.\n\n"
        "1. Is it easy to say? If people hesitate, they will avoid saying it.\n"
        "2. Is it easy to spell? A clever name that no one can type is expensive in ways you won't see right away.\n"
        "3. Does it carry meaning without explaining itself? The best names suggest a world. They don't drag the entire pitch deck behind them.\n\n"
        "Your business name does not have to describe everything you do. It does have to give people a reason to remember you.\n\n"
        "Finding names isn't the problem. Finding YOUR name is.\n\n"
        "Reel VO: You can usually feel when a business name works before you can explain why. "
        "It sounds clean. It's easy to repeat. It has a little meaning built in, but it doesn't try to carry the whole business plan."
    ),
})

# DAY 6 — Nobody's Talking About: Luna — Sep 22
notion_create({
    "Post Title": title_prop("Day 6 — Nobody's Talking About: Luna Alternatives"),
    "Date": date_prop("2026-09-22"),
    "Vertical": verticals_prop([VERTICAL_PET]),
    "Platform": platforms_prop(IG_TT),
    "Status": status_prop(STATUS_NEEDS_REVIEW),
    "Objective": select_prop(OBJ_SAVES),
    "CTA": text_prop("Save the list, then try a free pet name list at nam-engine.com."),
    "Notes": text_prop(
        "Hook: Luna is everywhere. These are the alternatives nobody mentions.\n\n"
        "Caption: Luna became popular because it has the whole package: soft sound, celestial meaning, easy spelling, and a little mystery.\n\n"
        "Five alternatives that keep the mood:\n"
        "Wren — small, graceful, and nature-led without being sugary.\n"
        "Vesper — evening-toned, elegant, and quietly dramatic.\n"
        "Cleo — bright, feline, clever, and full of personality.\n"
        "Sable — sleek, dark, soft-edged, and beautiful on a cat or dog.\n"
        "Isadora — romantic, elaborate, and unexpectedly wearable with Izzy as a nickname.\n\n"
        "Finding names isn't the problem. Finding YOUR name is.\n\n"
        "Reel VO: Luna is everywhere because it works. Soft, celestial, easy to spell, and just mysterious enough. "
        "But if you want the Luna feeling without the Luna popularity, try Wren, Vesper, Cleo, Sable, or Isadora."
    ),
})

# DAY 9 — The Name That Almost Wasn't (Pet) — Sep 29
notion_create({
    "Post Title": title_prop("Day 9 — The Name That Almost Wasn't"),
    "Date": date_prop("2026-09-29"),
    "Vertical": verticals_prop([VERTICAL_PET]),
    "Platform": platforms_prop(IG_TT),
    "Status": status_prop(STATUS_NEEDS_REVIEW),
    "Objective": select_prop(OBJ_PARTICIP),
    "CTA": text_prop("Comment the almost-name and the name that stuck. Try NamEngine for your free first pet name list."),
    "Notes": text_prop(
        "Hook: What name did you almost give your pet before the real one stuck?\n\n"
        "Caption: Pet names have a funny way of revealing themselves late. You bring them home with one idea. "
        "Then three days later their personality arrives, knocks the first name off the table, and suddenly the right name is obvious.\n\n"
        "Maybe they were almost:\n"
        "- Olive before they became Goose\n"
        "- Jasper before they became Beans\n"
        "- Daisy before they became Mabel\n"
        "- Apollo before they became Sock\n\n"
        "Tell us: what name did you almost give your pet before the real one stuck?\n\n"
        "Reel VO: Every pet has an almost-name. The name you had picked before their actual personality showed up and ruined your plan."
    ),
})

# DAY 10 — Name DNA: Stripe (Business) — Oct 1
notion_create({
    "Post Title": title_prop("Day 10 — Name DNA: Stripe"),
    "Date": date_prop("2026-10-01"),
    "Vertical": verticals_prop([VERTICAL_BUSINESS]),
    "Platform": platforms_prop(IG_TT),
    "Status": status_prop(STATUS_NEEDS_REVIEW),
    "Objective": select_prop(OBJ_AUTHORITY),
    "CTA": text_prop("Try NamEngine for a free first business name list at nam-engine.com."),
    "Notes": text_prop(
        "Hook: Name DNA: Why Stripe works as a business name.\n\n"
        "Caption: Stripe is a strong name because it does not try to explain payments in the obvious way.\n\n"
        "Sound: Short, crisp, one syllable. Easy to say, easy to remember, hard to mumble.\n"
        "Shape: The word feels linear and clean. A stripe is a mark, a band, a line of movement.\n"
        "Signal: It suggests speed, order, and clarity without trapping the company inside one narrow feature.\n"
        "What it avoids: No forced tech spelling. No generic 'pay' construction. No over-explained benefit.\n\n"
        "A great name is not just available. It is repeatable, searchable, and emotionally clear.\n\n"
        "Reel VO: Stripe works because it doesn't over-explain itself. Short, crisp, visual, and easy to remember. "
        "A good business name points in the right direction without trapping the company inside one feature."
    ),
})

# DAY 12 — Sunday Pet Name List — Oct 6
notion_create({
    "Post Title": title_prop("Day 12 — Sunday Pet Name List: Not the Obvious Ones"),
    "Date": date_prop("2026-10-06"),
    "Vertical": verticals_prop([VERTICAL_PET]),
    "Platform": platforms_prop(IG_TT),
    "Status": status_prop(STATUS_NEEDS_REVIEW),
    "Objective": select_prop(OBJ_SAVES),
    "CTA": text_prop("Save this Sunday list, or try your free first pet name list at nam-engine.com."),
    "Notes": text_prop(
        "Hook: Pet names that feel considered, not generic.\n\n"
        "Caption: A good pet name doesn't have to be quirky to have personality.\n\n"
        "This week's list:\n"
        "1. Mabel — soft, vintage, and deeply lovable.\n"
        "2. Otis — soulful, sturdy, and sweet without being sugary.\n"
        "3. Cleo — clever, bright, and expressive.\n"
        "4. Bowie — stylish, musical, and confident.\n"
        "5. Fig — small, warm, and quietly funny.\n"
        "6. Winnie — affectionate, sunny, and easy to live with.\n"
        "7. Sable — sleek, elegant, and a little mysterious.\n"
        "8. Hugo — charming, solid, and storybook-warm.\n"
        "9. Pippa — upbeat, brisk, and full of motion.\n"
        "10. Rune — spare, atmospheric, and quietly magical.\n\n"
        "Reel VO: Pet names that feel considered, not generic: Mabel, Otis, Cleo, Bowie, Fig, Winnie, Sable, Hugo, Pippa, and Rune."
    ),
})

# DAY 13 — Would You Name Your Brand This? (Business) — Oct 8
notion_create({
    "Post Title": title_prop("Day 13 — Would You Name Your Brand This?"),
    "Date": date_prop("2026-10-08"),
    "Vertical": verticals_prop([VERTICAL_BUSINESS]),
    "Platform": platforms_prop(IG_TT),
    "Status": status_prop(STATUS_NEEDS_REVIEW),
    "Objective": select_prop(OBJ_PARTICIP),
    "CTA": text_prop("Comment your vote: Meridian Coffee or The Daily Press. Build your own at nam-engine.com."),
    "Notes": text_prop(
        "Hook: Meridian Coffee vs. The Daily Press — which one would you go to?\n\n"
        "Caption: Same category. Very different signals.\n\n"
        "Meridian Coffee feels polished, calm, and slightly elevated. "
        "It suggests craft, direction, maybe a place with good light and a serious espresso program.\n\n"
        "The Daily Press feels familiar, active, and community-based. "
        "It suggests routine, newspapers, morning rituals, and a place people fold into their day.\n\n"
        "One says: refined pause. The other says: everyday ritual.\n\n"
        "Vote in the comments: Meridian Coffee or The Daily Press.\n\n"
        "Reel VO: Would you go to Meridian Coffee or The Daily Press? Same category, totally different feeling. "
        "That's the point of naming: you're not just choosing words. You're choosing the promise people feel before they ever walk in."
    ),
})

print("\n=== All done ===")
print("15 posts total: 7 updated + 8 created")
print("Content calendar: Sep 8 → Oct 10")
