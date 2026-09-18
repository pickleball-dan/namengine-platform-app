import os, sys, time, json, requests
from typing import Dict, Any, List

TOKEN = os.environ.get("NOTION" + "_API" + "_TOKEN")
VERSION = os.environ.get("NOTION" + "_API" + "_VERSION") or "2026-03-11"
BASE = "https://api.notion.com/v1"
HQ_PAGE_ID = "3c0c8498-b23f-8060-895a-ddbe0ec44ded"

if not TOKEN:
    print("Missing Notion token", file=sys.stderr)
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": VERSION,
    "Content-Type": "application/json",
}

def rich(s: str) -> List[Dict[str, Any]]:
    if not s:
        return []
    chunks = [s[i:i+1900] for i in range(0, len(s), 1900)]
    return [{"type": "text", "text": {"content": c}} for c in chunks]

def title(s: str) -> List[Dict[str, Any]]:
    return [{"type": "text", "text": {"content": s[:2000]}}]

def patch_page(page_id: str, props: Dict[str, Any]) -> None:
    r = requests.patch(f"{BASE}/pages/{page_id}", headers=headers, json={"properties": props}, timeout=30)
    if r.status_code >= 400:
        print("PATCH ERROR", page_id, r.status_code, r.text[:2000], file=sys.stderr)
        sys.exit(1)
    time.sleep(0.12)

def block_para(text: str):
    return {"object":"block","type":"paragraph","paragraph":{"rich_text":rich(text)}}

def block_h1(text: str):
    return {"object":"block","type":"heading_1","heading_1":{"rich_text":rich(text)}}

def block_h2(text: str):
    return {"object":"block","type":"heading_2","heading_2":{"rich_text":rich(text)}}

def block_h3(text: str):
    return {"object":"block","type":"heading_3","heading_3":{"rich_text":rich(text)}}

def block_bullet(text: str):
    return {"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":rich(text)}}

def create_page_under_hq(name: str, blocks: List[Dict[str, Any]]) -> str:
    payload = {"parent":{"page_id":HQ_PAGE_ID}, "properties":{"title":{"title":title(name)}}, "children":blocks[:90]}
    r = requests.post(f"{BASE}/pages", headers=headers, json=payload, timeout=30)
    if r.status_code >= 400:
        print("CREATE ERROR", r.status_code, r.text[:2000], file=sys.stderr)
        sys.exit(1)
    return r.json()["url"]

pages = {
    "day1": "3c0c8498-b23f-8108-bd5b-dff007503701",
    "day2": "3c0c8498-b23f-81e5-b76d-c73d5082d105",
    "day3": "3c0c8498-b23f-8144-92e2-dab95c52f019",
    "day4": "3c0c8498-b23f-8190-ad59-c412ace93f38",
    "day5": "3c0c8498-b23f-8141-b3be-f14370113ede",
    "day6": "3c0c8498-b23f-817d-9e4b-e38f47a1a560",
    "day7": "3c0c8498-b23f-8177-9aa1-c07c28f6e9f0",
}

polished = {
"day1": {
"Post / Asset": "Day 1 — Why NamEngine Exists",
"Hook": "Finding names isn’t the problem. Finding your names is.",
"Reel / TikTok Script": "ON-SCREEN HOOK: Finding names isn’t the problem. Finding your names is.\n\nVOICEOVER: There are already endless baby-name lists. Top 100 lists. Vintage lists. Rare lists. Classic lists. And somehow, more names can make the decision feel harder. Because the real problem is not finding more options. It is finding the names that actually feel like yours. That is what NamEngine is built for: moving from a giant pile of possibilities to a smaller set of names that fit your taste.\n\nCAPTION: Most naming tools give you more names. NamEngine is built to understand your taste — what you love, what you rule out, and the patterns behind both.\n\nCTA: Follow for smarter baby-name ideas and naming taste tests.",
"Carousel Copy": "Slide 1: Finding names isn’t the problem. Finding your names is.\nSlide 2: There are already endless baby-name lists.\nSlide 3: More options do not always make naming easier.\nSlide 4: The real question is: which names actually feel like us?\nSlide 5: NamEngine helps you discover names that fit your taste.\nSlide 6: Follow for naming ideas with a point of view.",
"Pinterest Copy": "Pin title: Finding your baby name is not about bigger lists\nPin description: Most baby-name tools give you more names. NamEngine helps you think about which names actually fit your taste.",
"Design Notes": "Canva brief: 9:16 Reel/TikTok. Start with visual chaos: scrolling list/name dump. Cut to calm curated set of 5–8 name cards. Palette: warm cream, soft black, muted green or clay accent. Typography: refined serif for names, clean sans for commentary. Keep product subtle; this is brand intro, not a full demo.",
"Reviewer Notes": "Polished for final review. Check: warm, intelligent, anti-endless-list without sounding smug. Avoid extra AI language."
},
"day2": {
"Post / Asset": "Day 2 — If You Love Theodore",
"Hook": "If you love Theodore but want something less common…",
"Reel / TikTok Script": "ON-SCREEN HOOK: If you love Theodore but want something less common…\n\nVOICEOVER: If Theodore is on your list, you may not just love the name. You may love the shape of it: traditional, substantial, warm, and nickname-friendly. So do not replace it with random rare names. Look for names that share the same DNA. Frederick has the old-soul weight and nickname potential. Arthur feels classic and storied. Edmund is literary and grounded. Hugo keeps the warmth in a shorter package. Ambrose is more distinctive, but still rooted and elegant. The trick is not finding a Theodore clone. It is understanding what you loved about Theodore in the first place.\n\nCAPTION: The smartest alternatives are not just “names like Theodore.” They share the part of Theodore you actually love: history, rhythm, warmth, nickname potential, or old-soul charm.\n\nCTA: Which Theodore alternative would you actually consider?",
"Carousel Copy": "Slide 1: If you love Theodore but want something less common…\nSlide 2: First, ask what you love about Theodore. History? Warmth? Nickname potential? Old-soul charm?\nSlide 3: Frederick — substantial, traditional, and full of nickname options.\nSlide 4: Arthur — classic, storied, and sturdy without feeling showy.\nSlide 5: Edmund — literary, grounded, and quietly handsome.\nSlide 6: Hugo — warm, vintage, and much more compact.\nSlide 7: Ambrose — distinctive, elegant, and still rooted.\nSlide 8: The goal is not a Theodore clone. It is a name that fits the same taste.\nSlide 9: Save this if Theodore is on your list.",
"Pinterest Copy": "Pin title: If you love Theodore but want something less common\nPin description: Thoughtful baby-name alternatives to Theodore: Frederick, Arthur, Edmund, Hugo, and Ambrose — with notes on their classic, warm, old-soul feel.",
"Design Notes": "Canva brief: IG carousel 4:5, plus Pinterest 2:3. Editorial name-card template. Slide 1 strong hook; slides 3–7 one large name + one taste sentence; slide 8 explains the NamEngine POV. Use subtle labels like “old-soul,” “storied,” “grounded.”",
"Reviewer Notes": "Polished for final review. Verify the five alternatives feel aligned with brand taste. No unsupported popularity stats."
},
"day3": {
"Post / Asset": "Day 3 — Would You Name Them Arthur or August?",
"Hook": "Arthur or August? No overthinking.",
"Reel / TikTok Script": "ON-SCREEN HOOK: Arthur or August? No overthinking.\n\nVOICEOVER: Two classic-feeling names. Very different energy. Arthur feels sturdy, storied, a little knightly, and quietly serious. August feels warm, polished, golden, and slightly grand. If you had to choose today: Arthur or August?\n\nTEXT BEATS: Arthur: sturdy / storied / classic. August: warm / polished / grand.\n\nCAPTION: This is why naming is taste, not just preference. Arthur and August can both feel classic — but they do very different things emotionally.\n\nCTA: Vote: Arthur or August?",
"Carousel Copy": "Slide 1: Arthur or August?\nSlide 2: Arthur feels sturdy, storied, and classic.\nSlide 3: August feels warm, polished, and golden.\nSlide 4: Both can feel timeless. Which one feels more like you?",
"Pinterest Copy": "Not primary. If adapted: Arthur vs. August — two classic boy names with very different style energy.",
"Design Notes": "Canva brief: 9:16 Reel + Story poll. Split screen: Arthur left, August right. Keep pacing fast and vote-focused. Story poll sticker: Arthur / August. Use the post title format: “Would You Name Them Arthur or August?”",
"Reviewer Notes": "Title corrected to match user edit. Participation post; no winner declared."
},
"day4": {
"Post / Asset": "Day 4 — Name DNA: Margot",
"Hook": "Why does Margot feel vintage and modern at the same time?",
"Reel / TikTok Script": "ON-SCREEN HOOK: Why does Margot feel vintage and modern at the same time?\n\nVOICEOVER: Margot works because it carries a few signals at once. It has roots through Margaret, so it does not feel newly invented. But the ending gives it a cleaner, more stylish shape. That final “o” sound feels a little unexpected in English, while still being easy to say. It is tailored, but not cold. Polished, but not stiff. That is why Margot can feel traditional, stylish, and contemporary all at once.\n\nTEXT BEATS: Rooted in Margaret. Clean final sound. Tailored, stylish, warm. Vintage and modern.\n\nCAPTION: Some names work because they carry more than one style signal. Margot feels rooted, but not heavy. Stylish, but not made-up. Distinctive, but still familiar.\n\nCTA: What does Margot feel like to you?",
"Carousel Copy": "Slide 1: Name DNA: Margot\nSlide 2: Why does it feel vintage and modern at the same time?\nSlide 3: It has roots through Margaret, so it does not feel invented.\nSlide 4: The cleaner ending makes it feel tailored and contemporary.\nSlide 5: It is distinctive without being difficult.\nSlide 6: Margot’s energy: traditional / stylish / polished / warm.\nSlide 7: Would you use Margot?",
"Pinterest Copy": "Pin title: Name DNA: Margot\nPin description: Why Margot feels traditional, stylish, and contemporary at the same time — a baby-name style breakdown from NamEngine.",
"Design Notes": "Canva brief: 9:16 Reel. Elegant text-card sequence; large “Margot” title card, then 3–4 short analysis cards. Palette: cream, charcoal, muted blush. Avoid trend/popularity claims; this is style analysis.",
"Reviewer Notes": "Polished authority post. Good brand signal: NamEngine understands why names work."
},
"day5": {
"Post / Asset": "Day 5 — Nobody’s Talking About: Conrad",
"Hook": "Nobody’s talking about Conrad enough.",
"Reel / TikTok Script": "ON-SCREEN HOOK: Nobody’s talking about Conrad enough.\n\nVOICEOVER: Conrad is one of those names that feels established without feeling overexposed. It has a strong sound, but not a harsh one. It feels traditional, but not predictable. And it has a grounded, intelligent quality that wears well beyond childhood. If you like Arthur, Frederick, Edmund, or Walter, Conrad probably belongs in the conversation.\n\nCAPTION: Conrad is a strong candidate for parents who want something established, substantial, and less frequently encountered than the most obvious classics.\n\nCTA: Would you add Conrad to the list?",
"Carousel Copy": "Slide 1: Nobody’s talking about Conrad enough.\nSlide 2: Conrad feels established without feeling overexposed.\nSlide 3: It has a strong sound, but not a harsh one.\nSlide 4: It sits near Arthur, Frederick, Edmund, and Walter: classic, serious, grown-up.\nSlide 5: The style: grounded, intelligent, traditional, quietly distinctive.\nSlide 6: Best for someone who wants a real classic that is not one of the obvious choices.\nSlide 7: Would you consider Conrad?\nSlide 8: Save this if you like underused classics.",
"Pinterest Copy": "Pin title: Nobody’s talking about Conrad enough\nPin description: Conrad is an underused classic boy name with a grounded, intelligent, traditional feel. A strong option if you like Arthur, Frederick, Edmund, or Walter.",
"Design Notes": "Canva brief: IG carousel 4:5. Editorial classic feel; avoid cheesy medieval imagery. Strong serif name cards with short supporting lines. Pinterest adaptation: one tall card with Conrad + four style descriptors + adjacent names.",
"Reviewer Notes": "Polished discovery post. Uses “less frequently encountered” to avoid unsupported stats."
},
"day6": {
"Post / Asset": "Day 6 — Debate: Popularity",
"Hook": "Would popularity stop you from using a name you love?",
"Reel / TikTok Script": "ON-SCREEN HOOK: Would popularity stop you from using a name you love?\n\nVOICEOVER: Here is the naming dilemma. You find a name you really love. It fits. It feels right. You can imagine saying it every day. Then you realize it is becoming popular. Do you keep it because love matters most? Or do you move on because distinctiveness matters to you too? There is no correct answer. But your answer says a lot about your naming taste.\n\nCAPTION: Popularity is one of the biggest naming tradeoffs. Some people want a name that feels familiar and loved. Others want something with more room around it. Neither instinct is wrong — it is taste.\n\nCTA: Would popularity stop you? Yes or no?",
"Carousel Copy": "Slide 1: Would popularity stop you from using a name you love?\nSlide 2: Side A: If you love it, use it.\nSlide 3: Side B: Distinctiveness matters too.\nSlide 4: Popularity is not just data. It changes how a name feels.\nSlide 5: Your answer says something about your naming taste.\nSlide 6: Would it stop you?",
"Pinterest Copy": "Not primary. If adapted: Would popularity stop you from using your favorite baby name? A naming debate about love, familiarity, and distinctiveness.",
"Design Notes": "Canva brief: 9:16 Reel + Story. Balanced split: “Love wins” vs “I need more distinctiveness.” Story poll: Yes, I’d move on / No, love wins. Keep tone open-ended and nonjudgmental.",
"Reviewer Notes": "Polished participation/taste-insight post. Save useful comments into Taste Lab later."
},
"day7": {
"Post / Asset": "Day 7 — Sunday List: Classic Beyond Obvious",
"Hook": "Ten classic names beyond the obvious choices.",
"Reel / TikTok Script": "ON-SCREEN HOOK: Ten classic names beyond the obvious choices.\n\nVOICEOVER: If you like classic names but do not want the first ten names everyone thinks of, try looking one layer deeper. Not obscure. Not invented. Just established names with a little more breathing room. Celia. Louisa. Beatrice. Harriet. Susannah. Arthur. Frederick. Edmund. Conrad. Hugo. Classic does not have to mean obvious.\n\nCAPTION: A classic name does not have to be one of the same few names on every list. These feel rooted, wearable, and familiar enough — with a little more room around them.\n\nCTA: Which one deserves more attention?",
"Carousel Copy": "Slide 1: Ten classic names beyond the obvious choices\nSlide 2: Celia — graceful, compact, and quietly literary.\nSlide 3: Louisa — warm, elegant, and familiar without feeling overused.\nSlide 4: Beatrice — vintage, bright, and full of character.\nSlide 5: Harriet — sturdy, charming, and wonderfully old-soul.\nSlide 6: Susannah — melodic, traditional, and softer than it first appears.\nSlide 7: Arthur — storied, sturdy, and deeply classic.\nSlide 8: Frederick — formal, substantial, and rich with nickname potential.\nSlide 9: Edmund — literary, grounded, and quietly handsome.\nSlide 10: Conrad — strong, established, and less expected.\nSlide 11: Hugo — warm, vintage, and easy to wear.\nSlide 12: Classic does not have to mean obvious. Save this list.",
"Pinterest Copy": "Pin title: Ten classic baby names beyond the obvious choices\nPin description: Classic baby names with a little more breathing room: Celia, Louisa, Beatrice, Harriet, Susannah, Arthur, Frederick, Edmund, Conrad, and Hugo.",
"Design Notes": "Canva brief: IG carousel 4:5 + Pinterest 2:3. Highly saveable list design. Use one name per slide for IG; Pinterest can summarize all ten. Visual subtitle: “Rooted, wearable, less obvious.” Keep gender presentation soft/neutral.",
"Reviewer Notes": "Polished list post. Needs final approval of the 10-name mix before design production."
}
}

for key, data in polished.items():
    props = {}
    for prop, val in data.items():
        if prop == "Post / Asset":
            props[prop] = {"title": title(val)}
        else:
            props[prop] = {"rich_text": rich(val)}
    props["Status"] = {"status": {"name": "Needs Review"}}
    patch_page(pages[key], props)

brief_blocks = [
    block_h1("Batch 1 Canva Design Briefs"),
    block_para("Use these as production instructions for the first seven NamEngine social posts. Batch 1 should be finished before launch. Design goal: warm, editorial, intelligent, highly saveable — never generic baby-content mush."),
    block_h2("Global Visual System"),
    block_bullet("Formats: Reels/TikToks 9:16; Instagram carousels 4:5; Pinterest pins 2:3."),
    block_bullet("Brand feel: curious, intelligent, warm, occasionally opinionated, nonjudgmental."),
    block_bullet("Typography: refined serif for names and hooks; clean sans for analysis/captions."),
    block_bullet("Palette: warm cream base, charcoal text, muted green/clay/blush accents."),
    block_bullet("Avoid: nursery clichés, mocking names, unsupported trend claims, excessive AI language, name dumps without reasoning."),
    block_bullet("Reusable design components: large name card, taste descriptor chips, split-choice poll frame, list slide, save/share closing card."),
]

per_day = [
    ("Day 1 — Why NamEngine Exists", ["Primary asset: Reel/TikTok.", "Visual arc: chaotic scrolling list → calm curated set.", "Text priority: hook first, then the idea that more names are not the same as better fit.", "Product should appear lightly, if at all."]),
    ("Day 2 — If You Love Theodore", ["Primary asset: carousel; secondary Pinterest pin.", "Slide rhythm: hook → taste question → five alternative name cards → NamEngine POV closing slide.", "Use taste labels: old-soul, storied, grounded, warm, rooted.", "Pinterest version can show all five alternatives on one tall graphic."]),
    ("Day 3 — Would You Name Them Arthur or August?", ["Primary asset: Reel + Story poll.", "Split-screen layout: Arthur vs. August.", "Story poll options: Arthur / August.", "Keep it fast; no declared winner."]),
    ("Day 4 — Name DNA: Margot", ["Primary asset: Reel.", "Elegant text-card sequence with Margot as the hero visual.", "Analysis cards: rooted in Margaret; clean final sound; tailored/stylish/warm; vintage and modern.", "Avoid popularity claims."]),
    ("Day 5 — Nobody’s Talking About: Conrad", ["Primary asset: carousel; optional Reel adaptation.", "Editorial classic feel; avoid medieval clichés.", "Name-card slides should feel substantial and adult-wearable.", "Use descriptors: grounded, intelligent, traditional, quietly distinctive."]),
    ("Day 6 — Debate: Popularity", ["Primary asset: Reel + Story poll.", "Balanced split: Love wins vs. I need more distinctiveness.", "Story poll: Yes, I’d move on / No, love wins.", "Keep tone open-ended; this is a taste question, not a verdict."]),
    ("Day 7 — Sunday List: Classic Beyond Obvious", ["Primary asset: carousel + Pinterest pin.", "IG: one name per slide, short rationale, strong save/share closing card.", "Pinterest: all ten names on one tall graphic with subtitle: Rooted, wearable, less obvious.", "Keep gender presentation soft/neutral."]),
]
for heading, bullets in per_day:
    brief_blocks.append(block_h3(heading))
    for b in bullets:
        brief_blocks.append(block_bullet(b))

url = create_page_under_hq("Batch 1 Canva Design Briefs", brief_blocks)
print(json.dumps({"updated_batch_items": 7, "canva_brief_url": url}, indent=2))
