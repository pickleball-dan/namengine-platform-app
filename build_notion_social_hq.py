import os
import sys
import json
import time
from typing import Any, Dict, List
import requests

TOKEN = os.environ.get("NOTION_API_TOKEN") or os.environ.get("NOTION_TOKEN")
VERSION = os.environ.get("NOTION_API_VERSION") or "2026-03-11"
BASE = "https://api.notion.com/v1"

HQ_PAGE_ID = "3c0c8498-b23f-8060-895a-ddbe0ec44ded"
CALENDAR_DS = "3c0c8498-b23f-81db-8b12-000bb086e742"
QUEUE_DS = "3c0c8498-b23f-81f9-9620-000b7035ed71"
FRANCHISE_DS = "3c0c8498-b23f-81f6-b321-000b969dda8a"
IDEAS_DS = "3c0c8498-b23f-814d-a1f9-000be4ded08f"
METRICS_DS = "3c0c8498-b23f-81f9-9620-000b7035ed71"  # not used; populated later if needed

if not TOKEN:
    print("Missing NOTION_API_TOKEN", file=sys.stderr)
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": VERSION,
    "Content-Type": "application/json",
}


def post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(BASE + path, headers=headers, json=payload, timeout=30)
    if r.status_code >= 400:
        print("ERROR", r.status_code, r.text[:2000], file=sys.stderr)
        raise SystemExit(1)
    time.sleep(0.12)
    return r.json()


def rich(s: str) -> List[Dict[str, Any]]:
    if not s:
        return []
    chunks = [s[i:i+1900] for i in range(0, len(s), 1900)]
    return [{"type":"text", "text":{"content": c}} for c in chunks]


def title(s: str) -> List[Dict[str, Any]]:
    return [{"type":"text", "text":{"content": s[:2000]}}]


def blocks_from_markdownish(md: str) -> List[Dict[str, Any]]:
    blocks = []
    for raw in md.strip().splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append({"object":"block","type":"heading_1","heading_1":{"rich_text":rich(line[2:])}})
        elif line.startswith("## "):
            blocks.append({"object":"block","type":"heading_2","heading_2":{"rich_text":rich(line[3:])}})
        elif line.startswith("### "):
            blocks.append({"object":"block","type":"heading_3","heading_3":{"rich_text":rich(line[4:])}})
        elif line.startswith("- "):
            blocks.append({"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":rich(line[2:])}})
        else:
            blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text":rich(line)}})
    return blocks[:90]


def create_page_under_hq(name: str, body: str) -> str:
    payload = {
        "parent": {"page_id": HQ_PAGE_ID},
        "properties": {"title": {"title": title(name)}},
        "children": blocks_from_markdownish(body),
    }
    return post("/pages", payload)["url"]


def create_calendar(item):
    props = {
        "Post Title": {"title": title(item["title"])},
        "Vertical": {"multi_select": [{"name":"Baby"}]},
        "Platform": {"multi_select": [{"name": p} for p in item["platforms"]]},
        "Franchise": {"select": {"name": item["franchise"]}},
        "Objective": {"select": {"name": item["objective"]}},
        "Status": {"status": {"name": item.get("status", "Idea")}},
        "Notes": {"rich_text": rich(item["notes"])},
        "CTA": {"rich_text": rich(item.get("cta", ""))},
    }
    payload = {"parent": {"data_source_id": CALENDAR_DS}, "properties": props}
    return post("/pages", payload)


def create_queue(item):
    props = {
        "Post / Asset": {"title": title(item["title"])},
        "Related Franchise": {"select": {"name": item["franchise"]}},
        "Status": {"status": {"name": item.get("status", "Briefed")}},
        "Hook": {"rich_text": rich(item.get("hook", ""))},
        "Reel / TikTok Script": {"rich_text": rich(item.get("script", ""))},
        "Carousel Copy": {"rich_text": rich(item.get("carousel", ""))},
        "Pinterest Copy": {"rich_text": rich(item.get("pinterest", ""))},
        "Design Notes": {"rich_text": rich(item.get("design", ""))},
        "Reviewer Notes": {"rich_text": rich(item.get("review", ""))},
    }
    return post("/pages", {"parent": {"data_source_id": QUEUE_DS}, "properties": props})


def create_franchise(item):
    props = {
        "Franchise": {"title": title(item["name"])},
        "Default Format": {"multi_select": [{"name": f} for f in item["formats"]]},
        "Purpose": {"rich_text": rich(item["purpose"])},
        "Hook Pattern": {"rich_text": rich(item["hook"])},
        "Structure": {"rich_text": rich(item["structure"])},
        "CTA Style": {"rich_text": rich(item["cta"])},
        "Guardrails": {"rich_text": rich(item["guardrails"])},
    }
    return post("/pages", {"parent": {"data_source_id": FRANCHISE_DS}, "properties": props})


def create_idea(item):
    props = {
        "Idea": {"title": title(item["idea"])},
        "Vertical": {"multi_select": [{"name": v} for v in item["verticals"]]},
        "Platform Fit": {"multi_select": [{"name": p} for p in item["platforms"]]},
        "Franchise": {"select": {"name": item["franchise"]}},
        "Priority": {"select": {"name": item["priority"]}},
        "Status": {"status": {"name":"Idea"}},
        "Source / Insight": {"rich_text": rich(item["source"])},
    }
    return post("/pages", {"parent": {"data_source_id": IDEAS_DS}, "properties": props})

strategy_url = create_page_under_hq("Strategy Brief + Creative Guardrails", """
# Strategy Brief + Creative Guardrails
## Core positioning
- NamEngine helps people discover names that fit their taste.
- Do not lead with “AI baby-name generator.” The technology should stay behind the experience.
- Central social idea: Names are more interesting than you think.
- Desired audience reaction: “This account understands names.” Then: “This product might actually understand my taste.”

## First 30-day objectives
- Build brand awareness without over-promoting.
- Establish naming authority through sound, history, meaning, culture, popularity, emotional feel, and style.
- Generate participation through polls, debates, comparisons, comments, saves, and shares.
- Teach taste: naming is not just finding names people like; it is identifying patterns in what they like.
- Drive qualified traffic by the second half of the launch period.

## Content ratio
- 70% useful, interesting, highly shareable naming content.
- 20% audience participation and community.
- 10% direct NamEngine promotion.

## Creative guardrails
- Do not mock names, parents, or personal choices.
- Do not present subjective taste as objective truth.
- Avoid “worst baby name” clickbait.
- Avoid overusing AI terminology.
- Avoid generic list content without editorial reasoning.
- Do not copy viral naming accounts without a NamEngine point of view.
- Do not make unsupported popularity/trend claims.
- Do not invent survey statistics.
- Do not over-promote the product.

## Product-state rule
- Social product demonstrations should show Love / No reactions only.
- Do not use Like or Maybe in new launch materials unless the product UI changes.
""")

taste_lab_url = create_page_under_hq("Taste Lab + Future Taste Index", """
# Taste Lab + Future Taste Index
## Operating idea
Social should function as a research layer, not just a broadcast channel.
Audience choices can reveal aggregate naming taste: Arthur vs. August, familiar vs. distinctive, strong vs. soft, traditional vs. contemporary, common spelling vs. alternative spelling.

## Research boundary
- Treat early audience data as directional research only.
- Do not automatically feed social results into production recommendations.
- Do not publish statistics unless the data exists and is clearly labeled.

## Future branded research product
The NamEngine Taste Index could eventually report:
- Names people love but say they would not use.
- Most polarizing names.
- Rising naming styles.
- Most appealing underused names.
- Generational differences in taste.
- Familiarity versus distinctiveness preferences.

## Measurement priority
- Saves = usefulness.
- Shares = social relevance.
- Comments/votes = participation.
- Profile visits = brand curiosity.
- Website visits = traffic.
- NamEngine session starts = qualified social traffic.
- Naming-session completion = traffic quality.
""")

franchises = [
    {"name":"Name DNA","formats":["Reel"],"purpose":"Establish NamEngine as an authority by explaining why a name feels the way it does.","hook":"Why does [Name] feel [traditional/stylish/strong/warm] at the same time?","structure":"Name → sound/shape → history/usage → emotional feel → why it works → soft prompt for audience reaction.","cta":"Ask: Would you use it? or What does this name feel like to you?","guardrails":"Avoid definitive taste judgments; explain the reasoning without claiming objective superiority."},
    {"name":"If You Love…","formats":["Carousel","Reel","Pinterest Pin"],"purpose":"Demonstrate intelligent recommendations by explaining what alternatives share with a familiar favorite.","hook":"If you love [popular name] but want something less common…","structure":"Anchor name → what people may love about it → 5 alternatives → why each fits a different dimension.","cta":"Save for your baby-name list; ask which alternative feels closest.","guardrails":"Avoid generic replacement lists; every suggestion needs an editorial reason."},
    {"name":"Would You Name Them?","formats":["Reel","Story"],"purpose":"Generate participation and collect simple taste signals.","hook":"Arthur or August? No overthinking.","structure":"Two names → quick contrast → poll/comment prompt → optional follow-up insight.","cta":"Vote in stories or comment your pick.","guardrails":"Keep it playful and nonjudgmental; no dunking on either option."},
    {"name":"Nobody’s Talking About…","formats":["Carousel"],"purpose":"Make NamEngine a source of discovery for excellent underused names.","hook":"Nobody’s talking about [Name] enough.","structure":"Name → pronunciation if needed → origin/history → feel → why it deserves consideration.","cta":"Save this if you want familiar but not overused names.","guardrails":"No unsupported popularity claims; say less frequently encountered if data is not cited."},
    {"name":"Naming Debate","formats":["Reel","Story"],"purpose":"Create comments and insight into how people make naming tradeoffs.","hook":"Would popularity stop you from using a name you love?","structure":"One real dilemma → two valid sides → ask audience to choose/explain.","cta":"Comment your rule or vote in stories.","guardrails":"Never imply one personal choice is obviously wrong."},
    {"name":"Taste Test","formats":["Reel","Story"],"purpose":"Introduce the concept of taste without explaining the technology.","hook":"Don’t overthink it. Which immediately feels most like you?","structure":"3–4 style groups or names → instant preference prompt → later interpret patterns.","cta":"Comment A/B/C/D or vote in stories.","guardrails":"Avoid overinterpreting individual votes; this is a taste signal, not a diagnosis."},
    {"name":"Sunday Name List","formats":["Carousel","Pinterest Pin"],"purpose":"Create saveable evergreen naming content with editorial personality.","hook":"Ten classic names beyond the obvious choices.","structure":"Theme → curated list → short reason per name → save/share prompt.","cta":"Save this list; send it to someone naming a baby.","guardrails":"List must have a point of view; not just names dumped on slides."},
    {"name":"Product Demo","formats":["Reel","TikTok"],"purpose":"Show that NamEngine learns taste through reactions and refinement.","hook":"Watch NamEngine learn someone’s naming taste.","structure":"Intake → initial names → Love / No reactions → refinement → improved recommendations.","cta":"Try NamEngine.","guardrails":"Use Love / No only. Keep AI language minimal and product proof concrete."},
]

calendar = [
    (1,"Why NamEngine Exists","Product Demo",["Instagram","TikTok"],"Awareness","Message: Finding names isn't the problem. Finding your names is. Introduce the idea that endless lists do not solve the naming problem.",""),
    (2,"If You Love Theodore","If You Love…",["Instagram","Pinterest"],"Saves/Shares","Five thoughtful alternatives to Theodore for someone who wants something less common.","Save this for your name list."),
    (3,"Would You Name Them? Arthur vs. August","Would You Name Them?",["Instagram","Stories"],"Participation","Head-to-head preference prompt: Arthur vs. August.","Vote or comment your pick."),
    (4,"Name DNA: Margot","Name DNA",["Instagram"],"Authority","Explain why Margot can feel traditional, stylish, and contemporary at once.","Would you use Margot?"),
    (5,"Nobody’s Talking About: Conrad","Nobody’s Talking About…",["Instagram"],"Saves/Shares","Introduce Conrad as established but less frequently encountered.","Save if you like serious-but-warm classics."),
    (6,"Naming Debate: Popularity","Naming Debate",["Instagram","Stories"],"Participation","Would you avoid a name you love because it is becoming popular?","Tell us your rule."),
    (7,"Sunday Name List: Classic Beyond Obvious","Sunday Name List",["Instagram","Pinterest"],"Saves/Shares","Ten classic names beyond the most obvious choices.","Save/share with someone naming a baby."),
    (8,"If You Love Henry","If You Love…",["Instagram","TikTok"],"Authority","Offer alternatives and explain what each shares with Henry: Arthur, Hugh, Frederick, Edmund, Conrad.","Which one feels closest to Henry?"),
    (9,"Would You Name Them? Maeve vs. Margot","Would You Name Them?",["Instagram","Stories"],"Participation","Head-to-head preference prompt: Maeve vs. Margot.","Vote or comment your pick."),
    (10,"Name DNA: James","Name DNA",["Instagram"],"Authority","Why does James remain relevant across generations?","What makes James work for you?"),
    (11,"Naming Debate: Sibling Used It First","Naming Debate",["Instagram","Stories"],"Participation","Would you use the name you love if your sibling used it first?","Comment your rule."),
    (12,"Nobody’s Talking About: Overlooked Girl Name","Nobody’s Talking About…",["Instagram"],"Saves/Shares","Feature an overlooked girl's name with editorial reasoning.","Save if you want distinctive without strange."),
    (13,"Taste Test: Clara / Margot / Maeve / Elodie","Taste Test",["Instagram","Stories"],"Participation","Prompt: Which immediately feels most like you?","Comment A, B, C, or D."),
    (14,"Sunday Name List: Distinctive Girl Names","Sunday Name List",["Instagram","Pinterest"],"Saves/Shares","Twelve girl names that feel distinctive without feeling unusual.","Save this list."),
    (15,"The Problem With Name Lists","Product Demo",["Instagram"],"Product Understanding","Opening: You don't need another list of 500 baby names. You need a small group of names that actually feel like you.","Try NamEngine when you want names that fit."),
    (16,"If You Love Olivia","If You Love…",["Instagram","TikTok"],"Authority","Show that people may love Olivia for femininity, rhythm, classical feel, familiarity, or literary association; recommend alternatives by dimension.","Which Olivia reason is yours?"),
    (17,"Would You Name Them? Felix vs. Finn","Would You Name Them?",["Instagram","Stories"],"Participation","Head-to-head preference prompt: Felix vs. Finn.","Vote or comment your pick."),
    (18,"What NamEngine Hears","Product Demo",["Instagram"],"Product Understanding","You say: Classic but not boring. Strong but not harsh. Different but not weird. NamEngine hears a taste profile.","Try NamEngine."),
    (19,"Nobody’s Talking About: Underused Name","Nobody’s Talking About…",["Instagram"],"Saves/Shares","Feature another underused name with explanation and feel.","Save this discovery."),
    (20,"Naming Debate: Pronunciation vs. Popularity","Naming Debate",["Instagram","Stories"],"Participation","Which would bother you more: regularly correcting pronunciation or sharing your name with several people in your class?","Pick your tradeoff."),
    (21,"Sunday Name List: Sounds Expensive","Sunday Name List",["Instagram","Pinterest"],"Saves/Shares","Ten names that sound expensive without trying too hard. Tone: playful.","Save for elegant name energy."),
    (22,"Taste Challenge: Style Groups","Taste Test",["Instagram","Stories"],"Participation","A: Arthur/Clara. B: Brooks/Sloane. C: Finn/Maeve. Which pair feels most like your naming style?","Vote A, B, or C."),
    (23,"NamEngine Product Demonstration","Product Demo",["Instagram","TikTok"],"Product Understanding","Show journey: Intake → Initial names → Love / No reactions → Refinement → Improved recommendations. Message: Watch NamEngine learn someone’s naming taste from what they love — and what they rule out.","Try NamEngine."),
    (24,"Audience-Led If You Love…","If You Love…",["Instagram","TikTok"],"Participation","Use a name that performed particularly well in prior audience polls.","Tell us the next name to unpack."),
    (25,"Name DNA: Audience Discussion Name","Name DNA",["Instagram"],"Authority","Analyze a name that generated significant discussion during the month.","What does this name feel like to you?"),
    (26,"The Couple Problem","Product Demo",["Instagram"],"Product Understanding","Opening: She wants timeless. He wants unusual. They may not actually be that far apart. Show overlap names.","Try finding your overlap in NamEngine."),
    (27,"Community Names","Taste Test",["Instagram","Stories"],"Participation","Prompt: What's the best name you've heard recently? Feature selected audience submissions.","Submit a name."),
    (28,"NamEngine Sunday List","Sunday Name List",["Instagram","Pinterest"],"Authority","Twenty names NamEngine believes deserve more attention.","Save/share the NamEngine list."),
    (29,"What We Learned","Taste Test",["Instagram","TikTok"],"Authority","If sufficient real engagement data exists, share anonymous aggregate findings. Do not invent statistics. Possible Taste Index seed.","Follow for more naming intelligence."),
    (30,"Direct Product Invitation","Product Demo",["Instagram","Stories"],"Conversion","You know what names you like. NamEngine figures out why. Then it uses that understanding to help you discover names you may never have found yourself.","Try NamEngine."),
]

queue = [
    {"title":"Day 1 — Why NamEngine Exists","franchise":"Product Demo","hook":"Finding names isn't the problem. Finding your names is.","script":"Open on endless baby-name lists. Contrast quantity with fit. Close: NamEngine is built for names that feel like you.","design":"Reel/TikTok. Visual metaphor: scrolling endless lists → smaller curated set.","review":"Keep product light; this is brand introduction."},
    {"title":"Day 2 — If You Love Theodore","franchise":"If You Love…","hook":"If you love Theodore but want something less common…","carousel":"Slide 1 hook. Slides 2–6: five alternatives with why each shares Theodore’s depth/rhythm/traditional feel/nickname potential. Final slide: save prompt.","pinterest":"Evergreen graphic: If you love Theodore but want something less common.","design":"Carousel + Pinterest. Needs 5 vetted alternatives before design."},
    {"title":"Day 3 — Arthur vs. August","franchise":"Would You Name Them?","hook":"Arthur or August? No overthinking.","script":"Quick contrast: Arthur feels storied and sturdy; August feels warm, polished, slightly grand. Ask for instant pick.","design":"Reel + Story poll. Story poll options: Arthur / August."},
    {"title":"Day 4 — Name DNA: Margot","franchise":"Name DNA","hook":"Why does Margot feel vintage and modern at the same time?","script":"Break down sound, spelling, history/style, and emotional feel. Close with: traditional, stylish, contemporary.","design":"Reel. Use elegant text cards; avoid overclaiming trend data."},
    {"title":"Day 5 — Nobody’s Talking About: Conrad","franchise":"Nobody’s Talking About…","hook":"Nobody’s talking about Conrad enough.","carousel":"Name, origin/history, sound, feel, why it deserves consideration, who it fits for.","design":"Carousel. Tone: established, serious, warm, less frequently encountered."},
    {"title":"Day 6 — Debate: Popularity","franchise":"Naming Debate","hook":"Would popularity stop you from using a name you love?","script":"Set up both sides: love matters vs. distinctiveness matters. Ask audience where they land.","design":"Reel + Story. Story poll: Yes, popularity matters / No, love wins."},
    {"title":"Day 7 — Sunday List: Classic Beyond Obvious","franchise":"Sunday Name List","hook":"Ten classic names beyond the obvious choices.","carousel":"Curated list with one-line rationale per name. Final save/share slide.","pinterest":"Pinterest list graphic with the same 10 names.","design":"Carousel + Pinterest. Needs final name list approval."},
]

ideas = [
    {"idea":"Names people love but say they would not use","verticals":["Baby"],"platforms":["Instagram","TikTok"],"franchise":"Naming Debate","priority":"High","source":"Future NamEngine Taste Index theme; collect via debates and polls."},
    {"idea":"Most polarizing names","verticals":["Baby"],"platforms":["Instagram","TikTok"],"franchise":"Would You Name Them?","priority":"High","source":"Potential aggregate report if real engagement data supports it."},
    {"idea":"Familiar vs. distinctive preference split","verticals":["Baby","Pet","Business"],"platforms":["Instagram","Pinterest"],"franchise":"Taste Test","priority":"High","source":"Core taste dimension for social research layer."},
    {"idea":"Pet names based on personality","verticals":["Pet"],"platforms":["Instagram","TikTok"],"franchise":"Taste Test","priority":"Medium","source":"Longer-term vertical expansion after Baby proves repeatable performance."},
    {"idea":"Why brand names work","verticals":["Business"],"platforms":["Instagram","TikTok","Pinterest"],"franchise":"Name DNA","priority":"Medium","source":"Business vertical expansion: sound symbolism, memorability, category conventions."},
]

created = {"strategy_url": strategy_url, "taste_lab_url": taste_lab_url, "franchises": 0, "calendar": 0, "queue": 0, "ideas": 0}
for f in franchises:
    create_franchise(f); created["franchises"] += 1
for day, t, fr, plats, obj, notes, cta in calendar:
    create_calendar({"title": f"Day {day} — {t}", "franchise": fr, "platforms": plats, "objective": obj, "notes": notes, "cta": cta})
    created["calendar"] += 1
for q in queue:
    create_queue(q); created["queue"] += 1
for i in ideas:
    create_idea(i); created["ideas"] += 1

print(json.dumps(created, indent=2))
