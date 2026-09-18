import os
import sys
import json
import time
from typing import Any, Dict, List
import requests

TOKEN = os.environ.get("NOTION_API_TOKEN")
VERSION = os.environ.get("NOTION_API_VERSION") or "2026-03-11"
BASE = "https://api.notion.com/v1"

if not TOKEN:
    print("Missing NOTION_API_TOKEN", file=sys.stderr)
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


def patch_page(page_id: str, props: Dict[str, Any]) -> None:
    r = requests.patch(f"{BASE}/pages/{page_id}", headers=headers, json={"properties": props}, timeout=30)
    if r.status_code >= 400:
        print("ERROR", page_id, r.status_code, r.text[:2000], file=sys.stderr)
        raise SystemExit(1)
    time.sleep(0.15)

pages = {
    "day1": "3c0c8498-b23f-8108-bd5b-dff007503701",
    "day2": "3c0c8498-b23f-81e5-b76d-c73d5082d105",
    "day3": "3c0c8498-b23f-8144-92e2-dab95c52f019",
    "day4": "3c0c8498-b23f-8190-ad59-c412ace93f38",
    "day5": "3c0c8498-b23f-8141-b3be-f14370113ede",
    "day6": "3c0c8498-b23f-817d-9e4b-e38f47a1a560",
    "day7": "3c0c8498-b23f-8177-9aa1-c07c28f6e9f0",
}

drafts = {
    "day1": {
        "Hook": "Finding names isn’t the problem. Finding your names is.",
        "Reel / TikTok Script": "FORMAT: Reel/TikTok, 20–30 seconds\n\nON-SCREEN HOOK:\nFinding names isn’t the problem. Finding your names is.\n\nSCRIPT / VOICEOVER:\nThere are already endless baby-name lists.\nTop 100 names. Vintage names. Rare names. Classic names. Names from every language, every style, every trend.\n\nBut more names do not always make the decision easier.\nSometimes they make it harder.\n\nBecause the real question is not: “Can I find more names?”\nIt is: “Which names actually feel like us?”\n\nNamEngine is built around that question.\nIt helps you move from a giant list of possibilities to names that fit your taste.\n\nTEXT BEATS:\n1. Endless baby-name lists are not the problem.\n2. The problem is knowing which names feel like yours.\n3. NamEngine helps you discover names that fit your taste.\n\nCAPTION:\nMost naming tools give you more names. NamEngine is built to understand your taste — the names you love, the names you rule out, and the patterns behind both.\n\nCTA:\nFollow for smarter baby-name ideas and naming taste tests.",
        "Carousel Copy": "Optional carousel adaptation:\nSlide 1: Finding names isn’t the problem. Finding your names is.\nSlide 2: There are already endless baby-name lists.\nSlide 3: More options can make naming feel harder, not easier.\nSlide 4: Because the real question is: which names actually feel like us?\nSlide 5: NamEngine helps you discover names that fit your taste.\nSlide 6: Follow for naming ideas with a point of view.",
        "Pinterest Copy": "Pin title: Finding your baby name is not about bigger lists\nPin description: Most baby-name tools give you more names. NamEngine helps you think about which names actually fit your taste.",
        "Design Notes": "Use fast visual contrast: chaotic scrolling list → calm short curated set. Keep the product appearance subtle; this is the brand-introduction post, not a hard demo. Use soft, warm baby-name aesthetic without looking like a generic nursery board.",
        "Reviewer Notes": "Review for tone: intelligent, warm, not anti-list in a smug way. Avoid overexplaining AI. Status moved to Needs Review.",
    },
    "day2": {
        "Hook": "If you love Theodore but want something less common…",
        "Reel / TikTok Script": "FORMAT: Reel/TikTok adaptation, 25–35 seconds\n\nON-SCREEN HOOK:\nIf you love Theodore but want something less common…\n\nSCRIPT / VOICEOVER:\nIf Theodore is on your list, you may not just love the name.\nYou may love the shape of it: traditional, substantial, warm, and nickname-friendly.\n\nSo instead of replacing Theodore with random rare names, look for names that share some of that same DNA.\n\nFrederick has the same old-soul weight and strong nickname potential.\nArthur feels classic and storied, but a little less polished.\nEdmund has that literary, traditional feel without sounding expected.\nHugo keeps the warmth and vintage charm in a shorter package.\nAmbrose is more distinctive, but still rooted and elegant.\n\nThat is the trick: do not just ask what is similar. Ask what you loved about Theodore in the first place.\n\nCAPTION:\nThe smartest alternatives are not just “names like Theodore.” They are names that share the part of Theodore you actually love: the history, the rhythm, the warmth, the nickname potential, or the old-soul feeling.\n\nCTA:\nWhich Theodore alternative would you actually consider?",
        "Carousel Copy": "Slide 1: If you love Theodore but want something less common…\nSlide 2: First, ask what you love about Theodore. Is it the history? The softness? The nickname potential? The old-soul feel?\nSlide 3: Frederick — substantial, traditional, and full of nickname options. It has Theodore’s weight, but a slightly more formal edge.\nSlide 4: Arthur — classic, storied, and sturdy. It feels old without feeling dusty.\nSlide 5: Edmund — literary, traditional, and quietly handsome. Familiar in shape, less expected in use.\nSlide 6: Hugo — warm, vintage, and compact. A good fit if you love Theodore’s charm but want something shorter.\nSlide 7: Ambrose — rooted, elegant, and distinctive. More unusual, but not invented or flimsy.\nSlide 8: The point is not to find a Theodore clone. It is to understand what Theodore is doing for your taste.\nSlide 9: Save this if Theodore is on your list.",
        "Pinterest Copy": "Pin title: If you love Theodore but want something less common\nPin description: Thoughtful baby-name alternatives to Theodore: Frederick, Arthur, Edmund, Hugo, and Ambrose — with notes on what each shares with Theodore’s classic, warm, old-soul feel.",
        "Design Notes": "Carousel first, Pinterest second. Design should feel editorial and saveable. Use one name per slide with a short taste reason, not a dictionary-style meaning dump. Pinterest can be a taller graphic summarizing all five alternatives.",
        "Reviewer Notes": "Needs human review of the five alternatives. None require popularity statistics. Avoid claiming Theodore is objectively too popular; frame as “if it feels too common for you.”",
    },
    "day3": {
        "Hook": "Arthur or August? No overthinking.",
        "Reel / TikTok Script": "FORMAT: Reel + Story poll, 10–18 seconds\n\nON-SCREEN HOOK:\nArthur or August? No overthinking.\n\nSCRIPT / VOICEOVER:\nTwo classic-feeling names. Very different energy.\n\nArthur feels sturdy, storied, a little knightly, and quietly serious.\nAugust feels warm, polished, golden, and slightly grand.\n\nIf you had to name a baby boy today: Arthur or August?\n\nTEXT BEATS:\nArthur: sturdy / storied / classic\nAugust: warm / polished / grand\n\nCAPTION:\nThis is exactly why naming is taste, not just preference. Arthur and August can both feel classic — but they do very different things emotionally.\n\nCTA:\nVote: Arthur or August?",
        "Carousel Copy": "Optional simple post adaptation:\nSlide 1: Arthur or August?\nSlide 2: Arthur feels sturdy, storied, and classic.\nSlide 3: August feels warm, polished, and golden.\nSlide 4: Both can feel timeless. Which one feels more like you?",
        "Pinterest Copy": "Not primary for this post. If adapted: Arthur vs. August — two classic boy names with very different style energy.",
        "Design Notes": "Story poll options: Arthur / August. Reel should be minimal and fast. Use split-screen design: Arthur on one side, August on the other. No winner declared.",
        "Reviewer Notes": "Participation post. Keep it lightweight and do not over-explain. Good candidate for collecting early preference language from comments.",
    },
    "day4": {
        "Hook": "Why does Margot feel vintage and modern at the same time?",
        "Reel / TikTok Script": "FORMAT: Reel, 25–35 seconds\n\nON-SCREEN HOOK:\nWhy does Margot feel vintage and modern at the same time?\n\nSCRIPT / VOICEOVER:\nMargot is interesting because it carries a few signals at once.\n\nIt has history. It is connected to Margaret, so it does not feel newly invented.\n\nBut the ending gives it a cleaner, more stylish shape than Margaret. That final “o” sound makes it feel a little unexpected in English, but still easy to say.\n\nIt also has a tailored quality. Not frilly, not harsh. Polished without feeling cold.\n\nThat is why Margot can feel traditional, stylish, and contemporary all at the same time.\n\nTEXT BEATS:\nMargot\nRooted in Margaret\nClean final sound\nTailored, stylish, warm\nVintage and modern\n\nCAPTION:\nSome names work because they carry more than one style signal. Margot feels rooted, but not heavy. Stylish, but not made-up. Distinctive, but still familiar.\n\nCTA:\nWhat does Margot feel like to you?",
        "Carousel Copy": "Optional carousel adaptation:\nSlide 1: Name DNA: Margot\nSlide 2: Why does it feel vintage and modern at the same time?\nSlide 3: It has roots through Margaret, so it does not feel invented.\nSlide 4: The cleaner ending makes it feel more tailored and contemporary.\nSlide 5: It is distinctive without being difficult.\nSlide 6: Margot’s energy: traditional / stylish / polished / warm.\nSlide 7: Would you use Margot?",
        "Pinterest Copy": "Pin title: Name DNA: Margot\nPin description: Why Margot feels traditional, stylish, and contemporary at the same time — a baby-name style breakdown from NamEngine.",
        "Design Notes": "Use elegant typography. Avoid overclaiming current trend/popularity. Visual rhythm: name large → 3–4 short analysis cards → final question. Keep the tone like editorial name analysis, not a lecture.",
        "Reviewer Notes": "Authority post. Claims are style-analysis based, not statistical. Good brand-building piece for “NamEngine understands why names work.”",
    },
    "day5": {
        "Hook": "Nobody’s talking about Conrad enough.",
        "Reel / TikTok Script": "FORMAT: Reel adaptation, 20–30 seconds\n\nON-SCREEN HOOK:\nNobody’s talking about Conrad enough.\n\nSCRIPT / VOICEOVER:\nConrad is one of those names that feels established without feeling overexposed.\n\nIt has a strong sound, but it is not sharp.\nIt feels traditional, but not predictable.\nAnd it has a grounded, intelligent quality that makes it feel very wearable on an adult.\n\nIf you like names such as Arthur, Frederick, Edmund, or Walter, Conrad probably belongs in the conversation.\n\nCAPTION:\nConrad is a strong candidate for parents who want something established, substantial, and less frequently encountered than the most familiar classics.\n\nCTA:\nWould you add Conrad to the list?",
        "Carousel Copy": "Slide 1: Nobody’s talking about Conrad enough.\nSlide 2: Conrad feels established without feeling overexposed.\nSlide 3: It has a strong sound, but not a harsh one.\nSlide 4: It sits near names like Arthur, Frederick, Edmund, and Walter — classic, serious, and grown-up.\nSlide 5: The style: grounded, intelligent, traditional, quietly distinctive.\nSlide 6: Best for someone who wants a real classic that is not one of the obvious choices.\nSlide 7: Would you consider Conrad?\nSlide 8: Save this if you like underused classics.",
        "Pinterest Copy": "Pin title: Nobody’s talking about Conrad enough\nPin description: Conrad is an underused classic boy name with a grounded, intelligent, traditional feel. A strong option if you like Arthur, Frederick, Edmund, or Walter.",
        "Design Notes": "Carousel with slightly masculine/classic editorial feel; avoid cliché old-map or knight imagery. Keep it warm enough for baby-name audience. Use “less frequently encountered” rather than unsupported rarity claims.",
        "Reviewer Notes": "Discovery post. If we later cite popularity, add source before making any numeric claim. Current copy intentionally avoids stats.",
    },
    "day6": {
        "Hook": "Would popularity stop you from using a name you love?",
        "Reel / TikTok Script": "FORMAT: Reel + Story, 15–25 seconds\n\nON-SCREEN HOOK:\nWould popularity stop you from using a name you love?\n\nSCRIPT / VOICEOVER:\nHere is the naming dilemma.\n\nYou find a name you really love. It fits. It feels right. You can imagine saying it every day.\n\nThen you realize it is becoming popular.\n\nDo you keep it because love matters most?\nOr do you move on because distinctiveness matters to you too?\n\nThere is no correct answer. But your answer says a lot about your naming taste.\n\nCAPTION:\nPopularity is one of the biggest naming tradeoffs. Some people want a name that feels familiar and loved. Others want something with more room around it. Neither instinct is wrong — it is taste.\n\nCTA:\nWould popularity stop you? Yes or no?",
        "Carousel Copy": "Optional carousel adaptation:\nSlide 1: Would popularity stop you from using a name you love?\nSlide 2: Side A: If you love it, use it.\nSlide 3: Side B: Distinctiveness matters too.\nSlide 4: Popularity is not just data. It changes how a name feels.\nSlide 5: Your answer says something about your naming taste.\nSlide 6: Would it stop you?",
        "Pinterest Copy": "Not primary. If adapted: Would popularity stop you from using your favorite baby name? A naming debate about love, familiarity, and distinctiveness.",
        "Design Notes": "Story poll: Yes, I’d move on / No, love wins. Reel should invite comments, not settle the debate. Use balanced visual framing: “Love wins” vs “I need more distinctiveness.”",
        "Reviewer Notes": "Participation and taste-insight post. Strong candidate for saving comment language into the Taste Lab.",
    },
    "day7": {
        "Hook": "Ten classic names beyond the obvious choices.",
        "Reel / TikTok Script": "Optional Reel adaptation, 25–35 seconds:\n\nON-SCREEN HOOK:\nTen classic names beyond the obvious choices.\n\nSCRIPT / VOICEOVER:\nIf you like classic names but do not want the first ten names everyone thinks of, try looking one layer deeper.\n\nNot obscure. Not invented. Just established names with a little more breathing room.\n\nCelia.\nLouisa.\nBeatrice.\nHarriet.\nSusannah.\nArthur.\nFrederick.\nEdmund.\nConrad.\nHugo.\n\nClassic does not have to mean obvious.\n\nCAPTION:\nA classic name does not have to be one of the same few names on every list. These feel rooted, wearable, and familiar enough — with a little more room around them.\n\nCTA:\nWhich one deserves more attention?",
        "Carousel Copy": "Slide 1: Ten classic names beyond the obvious choices\nSlide 2: Celia — graceful, compact, and quietly literary.\nSlide 3: Louisa — warm, elegant, and familiar without feeling overused.\nSlide 4: Beatrice — vintage, bright, and full of character.\nSlide 5: Harriet — sturdy, charming, and wonderfully old-soul.\nSlide 6: Susannah — melodic, traditional, and softer than it first appears.\nSlide 7: Arthur — storied, sturdy, and deeply classic.\nSlide 8: Frederick — formal, substantial, and rich with nickname potential.\nSlide 9: Edmund — literary, grounded, and quietly handsome.\nSlide 10: Conrad — strong, established, and less expected.\nSlide 11: Hugo — warm, vintage, and easy to wear.\nSlide 12: Classic does not have to mean obvious. Save this list.",
        "Pinterest Copy": "Pin title: Ten classic baby names beyond the obvious choices\nPin description: Classic baby names with a little more breathing room: Celia, Louisa, Beatrice, Harriet, Susannah, Arthur, Frederick, Edmund, Conrad, and Hugo.",
        "Design Notes": "Carousel + Pinterest. This should be highly saveable. Consider separate girl/boy color-neutral sections or a single editorial list. Avoid presenting as definitive ranking. Pinterest graphic should include all ten names plus a short subtitle: “Rooted, wearable, less obvious.”",
        "Reviewer Notes": "Needs review of the final 10-name list. Current list balances girls/boys and overlaps with prior Theodore/Conrad content for launch-week coherence.",
    },
}

for key, data in drafts.items():
    props = {name: {"rich_text": rich(value)} for name, value in data.items()}
    props["Status"] = {"status": {"name": "Needs Review"}}
    patch_page(pages[key], props)

print(json.dumps({"updated": len(drafts), "status": "Needs Review"}, indent=2))
