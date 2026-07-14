"""Shared generation interface for NamEngine."""

from __future__ import annotations

import re

from namengine.core.schemas import (
    NameResult,
    NamingBrief,
    TasteProfile,
    VerticalConfig,
)
from namengine.core.domain_availability import enrich_business_domain_info
from namengine.core.validation import is_baby_name_allowed_for_gender, validate_results


PET_NAME_POOL = [
    ("Milo", "MY-loh", "Friendly, bright, and easy to call."),
    ("Juniper", "JOO-nuh-per", "Nature-leaning with a warm, lively shape."),
    ("Rory", "ROR-ee", "Bouncy, clear, and cheerful without feeling silly."),
    ("Clover", "KLOH-ver", "Soft, lucky, and sweet with outdoor charm."),
    ("Toby", "TOH-bee", "Familiar, loyal, and simple across a room."),
    ("Sierra", "see-AIR-uh", "Open-air, graceful, and calm."),
    ("Maple", "MAY-pul", "Cozy, gentle, and affectionate."),
    ("Finn", "FIN", "Short, crisp, and highly callable."),
]

PET_REFINED_POOL = [
    ("Benny", "BEN-ee", "Sunny, familiar, and affectionate."),
    ("Scout", "SKOWT", "Adventurous and crisp without trying too hard."),
    ("Poppy", "POP-ee", "Bright, sweet, and easy to call."),
    ("Ollie", "AH-lee", "Friendly and playful with a soft landing."),
    ("Winnie", "WIN-ee", "Gentle, cozy, and lovable."),
    ("Remy", "REM-ee", "Warm, stylish, and still pet-ready."),
    ("Sunny", "SUN-ee", "Happy, direct, and hard to misunderstand."),
    ("Hazel", "HAY-zul", "Soft, nature-touched, and grounded."),
]

PET_FINALIST_POOL = [
    ("Milo", "MY-loh", "Friendly, bright, and easy to call."),
    ("Rory", "ROR-ee", "Bouncy, clear, and cheerful without feeling silly."),
    ("Scout", "SKOWT", "Adventurous and crisp without trying too hard."),
    ("Poppy", "POP-ee", "Bright, sweet, and easy to call."),
    ("Remy", "REM-ee", "Warm, stylish, and still pet-ready."),
    ("Hazel", "HAY-zul", "Soft, nature-touched, and grounded."),
]

PET_EXTRA_POOL = [
    ("Archie", "AR-chee", "Cheerful, familiar, and gently vintage."),
    ("Nico", "NEE-koh", "Compact, stylish, and easy to call."),
    ("Lottie", "LOT-ee", "Sweet, warm, and a little old-soul."),
    ("Otis", "OH-tis", "Friendly and grounded with an easygoing feel."),
    ("Mabel", "MAY-bul", "Cozy, classic, and affectionate."),
    ("Ziggy", "ZIG-ee", "Playful, bright, and full of personality."),
    ("Rosie", "ROH-zee", "Warm, lovable, and immediately friendly."),
    ("Theo", "THEE-oh", "Softly classic with a modern pet-ready shape."),
]

PET_ORIGINAL_POOL = [
    ("Lumo", "LOO-moh", "Bright, compact, and invented while staying easy to call."),
    ("Noriu", "NOR-ee-oo", "Softly original with a warm, musical finish."),
    ("Kova", "KOH-vah", "Strong, sleek, and pet-ready without feeling common."),
    ("Mavie", "MAY-vee", "Sweet and lively with a familiar enough shape."),
    ("Talo", "TAH-loh", "Short, grounded, and easy to say out loud."),
    ("Bramblee", "BRAM-blee", "Nature-touched and playful with an invented twist."),
    ("Solvi", "SOL-vee", "Sunny, distinctive, and still wearable."),
    ("Rueby", "ROO-bee", "Cute, bright, and lightly unexpected."),
]

PET_NAME_INSIGHTS = {
    "Milo": "has a soft opening, friendly rhythm, and an easy two-syllable call shape",
    "Juniper": "adds nature texture and a more distinctive shape without becoming hard to say",
    "Rory": "has bright repeated sounds that feel lively, warm, and easy to call across a room",
    "Clover": "brings a lucky, gentle image that still feels wearable for everyday use",
    "Toby": "feels familiar and loyal, with a simple sound that lands quickly",
    "Sierra": "has an open, graceful feel with outdoor energy and a calm finish",
    "Maple": "feels cozy and affectionate, with a soft nature cue that is easy to remember",
    "Finn": "is short, crisp, and especially strong if callability matters most",
    "Benny": "feels sunny and affectionate while staying familiar enough for daily use",
    "Scout": "carries adventurous energy with a crisp one-syllable command-friendly shape",
    "Poppy": "is bright and upbeat, with a repeatable sound that feels playful",
    "Ollie": "has a friendly, rounded sound that feels approachable and affectionate",
    "Winnie": "leans gentle and cozy, with warmth that suits a sweet personality",
    "Remy": "feels stylish but still relaxed enough for a pet name",
    "Sunny": "makes the personality cue immediate and easy for people to remember",
    "Hazel": "adds a grounded nature feel with a softer, vintage edge",
    "Archie": "adds cheerful vintage warmth while staying easy to say",
    "Nico": "keeps the sound compact and stylish without losing callability",
    "Lottie": "leans sweet and affectionate with a soft everyday rhythm",
    "Otis": "feels grounded and friendly with a calm, lovable finish",
    "Mabel": "brings cozy classic charm and a gentle sound",
    "Ziggy": "has lively energy and a memorable two-syllable shape",
    "Rosie": "feels warm, familiar, and naturally affectionate",
    "Theo": "balances a soft classic feel with a clean modern sound",
}

BABY_NAME_POOL = [
    ("Eloise", "EL-oh-eez", "Elegant, literary, and familiar without feeling overused."),
    ("Maya", "MY-uh", "Warm, simple, and internationally recognizable."),
    ("Clara", "KLAIR-uh", "Clear, classic, and gently bright."),
    ("Julian", "JOO-lee-un", "Softly tailored with a timeless, intelligent feel."),
    ("Theo", "THEE-oh", "Friendly, warm, and modern-classic."),
    ("Maren", "MAIR-en", "Calm, uncommon, and easy to wear."),
    ("Nora", "NOR-uh", "Graceful, familiar, and quietly strong."),
    ("Rowan", "ROH-un", "Nature-touched and flexible across styles."),
]

BABY_REFINED_POOL = [
    ("Iris", "EYE-ris", "Floral, crisp, and quietly distinctive."),
    ("Lena", "LEE-nuh", "Soft, international, and easy to say."),
    ("Miles", "MYLZ", "Warm, polished, and friendly."),
    ("Ada", "AY-duh", "Brief, vintage, and substantial."),
    ("Jonah", "JOH-nuh", "Gentle, grounded, and familiar."),
    ("Elian", "EL-ee-un", "Lyrical and uncommon while staying readable."),
    ("Maeve", "MAYV", "Compact, elegant, and strong."),
    ("Silas", "SY-lus", "Tailored, warm, and old-soul."),
    ("Celia", "SEE-lee-uh", "Gentle, melodic, and quietly classic."),
    ("Noemi", "no-EH-mee", "Lyrical, international, and warm."),
    ("Romy", "ROH-mee", "Bright, compact, and stylish."),
    ("Ansel", "AN-sul", "Softly tailored with an artistic old-soul feel."),
    ("Bennett", "BEN-it", "Polished, friendly, and surname-rooted."),
    ("Luca", "LOO-kuh", "Warm, global, and easy to love."),
    ("Mira", "MEER-uh", "Clear, graceful, and gently celestial."),
    ("Owen", "OH-en", "Warm, familiar, and grounded."),
]

BABY_FINALIST_POOL = [
    ("Elodie", "EL-oh-dee", "Romantic, musical, and uncommon but readable."),
    ("June", "JOON", "Clear, vintage, and gently sunny."),
    ("Louisa", "loo-EE-zuh", "Classic, literary, and warmer than formal."),
    ("Margot", "MAR-go", "Polished, vintage, and quietly stylish."),
    ("Arthur", "AR-thur", "Classic, sturdy, and bookish without feeling stiff."),
    ("Felix", "FEE-liks", "Bright, joyful, and old-world friendly."),
    ("Graham", "GRAY-um", "Tailored, calm, and understated."),
    ("Hollis", "HOL-is", "Gentle, surname-style, and gender-flexible."),
    ("Ivy", "EYE-vee", "Botanical, brief, and lively."),
    ("Rafael", "rah-fy-EL", "Warm, elegant, and international."),
    ("Serena", "suh-REE-nuh", "Calm, graceful, and familiar without feeling flat."),
    ("Tessa", "TESS-uh", "Bright, friendly, and unfussy."),
]

BABY_EXTRA_POOL = [
    ("Anya", "AHN-yuh", "Warm, compact, and quietly international."),
    ("Calla", "KAL-uh", "Botanical, soft, and uncommon."),
    ("Ellis", "EL-is", "Gentle, tailored, and gender-flexible."),
    ("Hugo", "HYOO-goh", "Bright, classic, and stylish."),
    ("Lyra", "LYE-ruh", "Musical, celestial, and easy to say."),
    ("Reid", "REED", "Clean, strong, and understated."),
    ("Soren", "SOR-en", "Distinctive, calm, and literary."),
    ("Vera", "VAIR-uh", "Clear, vintage, and quietly confident."),
    ("Alden", "ALL-den", "Gentle, literary, and quietly substantial."),
    ("Alma", "AHL-muh", "Warm, vintage, and soulful."),
    ("Beatrice", "BEE-uh-tris", "Classic, lively, and full of character."),
    ("Cassian", "KASS-ee-un", "Ancient-feeling, elegant, and distinctive."),
    ("Daphne", "DAF-nee", "Botanical, bright, and mythic without feeling heavy."),
    ("Emil", "EH-meel", "Compact, European, and soft-spoken."),
    ("Flora", "FLOR-uh", "Garden-like, vintage, and easy to say."),
    ("Greta", "GREH-tuh", "Strong, crisp, and old-world."),
    ("Harlan", "HAR-lun", "Grounded, surname-rooted, and warm."),
    ("Ida", "EYE-duh", "Brief, vintage, and quietly strong."),
    ("Leona", "lee-OH-nuh", "Warm, strong, and graceful."),
    ("Matteo", "mah-TAY-oh", "Lyrical, global, and friendly."),
    ("Nico", "NEE-koh", "Compact, stylish, and easygoing."),
    ("Opal", "OH-pul", "Gemstone-inspired, vintage, and gentle."),
    ("Petra", "PET-ruh", "Strong, international, and distinctive."),
    ("Quinn", "KWIN", "Clean, modern, and gender-flexible."),
    ("Rhea", "REE-uh", "Mythic, brief, and bright."),
    ("Stellan", "STEL-un", "Calm, Nordic, and tailored."),
    ("Thea", "THEE-uh", "Soft, classic, and luminous."),
    ("Zara", "ZAHR-uh", "Sleek, global, and confident."),
]

BABY_WIDE_EXPLORATION_POOL = [
    ("Amara", "ah-MAR-uh", "Warm, lyrical, and meaning-rich."),
    ("Anouk", "ah-NOOK", "Chic, rare, and concise."),
    ("Aurelia", "aw-REEL-ee-uh", "Golden, romantic, and substantial."),
    ("Blythe", "BLYTHE", "Bright, vintage, and rare."),
    ("Cora", "KOR-uh", "Classic, warm, and easy."),
    ("Dalia", "DAHL-yuh", "Botanical, soft, and international."),
    ("Esme", "EZ-may", "Literary, tender, and compact."),
    ("Freya", "FRAY-uh", "Mythic, warm, and current."),
    ("Imogen", "IM-oh-jen", "Literary, distinctive, and wearable."),
    ("Liora", "lee-OR-uh", "Light-filled, graceful, and uncommon."),
    ("Mabel", "MAY-bul", "Cozy, vintage, and affectionate."),
    ("Nina", "NEE-nuh", "Simple, global, and warm."),
    ("Orla", "OR-luh", "Compact, Irish-rooted, and bright."),
    ("Phoebe", "FEE-bee", "Lively, classic, and sunny."),
    ("Sylvie", "SIL-vee", "Woodland-soft, French-leaning, and familiar enough."),
    ("Willa", "WIL-uh", "Gentle, literary, and grounded."),
    ("Ambrose", "AM-brohz", "Old-soul, warm, and distinctive."),
    ("Calvin", "KAL-vin", "Steady, tailored, and familiar."),
    ("Dashiell", "DASH-ul", "Literary, stylish, and energetic."),
    ("Ezra", "EZ-ruh", "Brief, warm, and ancient-modern."),
    ("Finnian", "FIN-ee-un", "Lively, Irish-rooted, and friendly."),
    ("Gideon", "GID-ee-un", "Substantial, warm, and uncommon."),
    ("Jasper", "JAS-per", "Bright, vintage, and nature-adjacent."),
    ("Kieran", "KEER-un", "Gentle, Celtic-rooted, and readable."),
    ("Leif", "LAYF", "Nature-touched, Nordic, and clean."),
    ("Micah", "MY-kuh", "Soft, familiar, and grounded."),
    ("Otto", "AH-toh", "Brief, vintage, and cheerful."),
    ("Rhys", "REES", "Crisp, Welsh-rooted, and elegant."),
    ("Tobias", "toh-BY-us", "Classic, warm, and substantial."),
    ("Xavier", "ZAY-vee-er", "Distinctive, familiar, and energetic."),
    ("Langston", "LANG-stun", "Literary, strong, and deeply tied to African American cultural history."),
    ("Malcolm", "MAL-kum", "Strong, recognizable, and historically resonant without feeling overused."),
    ("Booker", "BOOK-er", "Distinctive, surname-rooted, and historically grounded."),
    ("Thurgood", "THUR-good", "Rare, substantial, and connected to civil-rights history."),
    ("Ellington", "EL-ing-tun", "Musical, polished, and heritage-rich with a distinctive surname style."),
    ("Frederick", "FRED-er-ik", "Classic, strong, and historically substantial."),
    ("Bayard", "BAY-ard", "Rare, principled, and historically meaningful."),
    ("Giovanni", "joh-VAH-nee", "Classic, unmistakably Italian, and warm with substantial history."),
    ("Leonardo", "lee-oh-NAR-doh", "Italian-rooted, artistic, recognizable, and strong."),
    ("Lorenzo", "loh-REN-zoh", "Lyrical, classic, and clearly Italian without feeling obscure."),
    ("Dante", "DAHN-tay", "Literary, strong, and Italian-rooted with a distinctive shape."),
    ("Marco", "MAR-koh", "Familiar, compact, and warmly Italian."),
    ("Enzo", "EN-zoh", "Compact, energetic, and unmistakably Italian."),
    ("Alessio", "ah-LESS-ee-oh", "Lyrical, warm, and Italian-rooted while staying readable."),
    ("Rocco", "ROH-koh", "Strong, distinctive, and Italian-rooted."),
    ("Santino", "san-TEE-noh", "Warm, distinctive, and heritage-rich."),
    ("Vittorio", "vee-TOR-ee-oh", "Substantial, classic, and deeply Italian in cadence."),
    ("Elio", "EH-lee-oh", "Bright, compact, and Mediterranean-feeling."),
    ("Cillian", "KIL-ee-un", "Irish-rooted, distinctive, and strong while staying wearable."),
    ("Ronan", "ROH-nun", "Irish-rooted, warm, and recognizable without being overused."),
    ("Eamon", "AY-mun", "Irish-rooted, substantial, and gently classic."),
    ("Declan", "DEK-lun", "Irish-rooted, strong, and familiar enough for everyday use."),
    ("Cormac", "KOR-mak", "Irish-rooted, literary, and sturdy."),
    ("Seamus", "SHAY-mus", "Irish-rooted, warm, and traditional."),
    ("Lachlan", "LOCK-lun", "Scottish-rooted, strong, and outdoorsy."),
    ("Callum", "KAL-um", "Scottish-rooted, gentle, and familiar."),
    ("Duncan", "DUN-kun", "Scottish-rooted, sturdy, and classic."),
    ("Alistair", "AL-is-ter", "Scottish-rooted, polished, and substantial."),
    ("Hamish", "HAY-mish", "Scottish-rooted, warm, and distinctive."),
    ("Ewan", "YOO-un", "Scottish-rooted, compact, and approachable."),
    ("Nikolai", "NIK-oh-lye", "Russian-rooted, substantial, and elegant."),
    ("Lev", "LEV", "Russian-rooted, brief, and strong."),
    ("Dmitri", "DMEE-tree", "Russian-rooted, classic, and distinctive."),
    ("Mikhail", "mee-KHY-eel", "Russian-rooted, historic, and strong."),
    ("Ivan", "EYE-vun", "Russian-rooted, classic, and direct."),
    ("Viktor", "VIK-tor", "Russian-rooted, strong, and recognizable."),
    ("Kai", "KYE", "Chinese-rooted in many modern uses, compact, and bright."),
    ("Ming", "MING", "Chinese-rooted, clear, and luminous."),
    ("Jian", "JYEN", "Chinese-rooted, concise, and strong."),
    ("Wei", "WAY", "Chinese-rooted, brief, and graceful."),
    ("Jun", "JOON", "Chinese-rooted, compact, and warm."),
    ("Liang", "LYAHNG", "Chinese-rooted, strong, and melodic."),
]

BABY_NAME_INSIGHTS = {
    "Eloise": "carries a polished literary feeling with a soft, graceful rhythm",
    "Maya": "is short, warm, and easy across languages and generations",
    "Clara": "feels clear and timeless, with a bright sound that is easy to spell",
    "Julian": "balances gentle sounds with a tailored, grown-up shape",
    "Theo": "has friendly warmth and a current classic feel without becoming fussy",
    "Maren": "offers a calm coastal sound with uncommon-but-readable strength",
    "Nora": "is familiar and graceful while still feeling substantial",
    "Rowan": "brings nature texture and a flexible, modern sound",
    "Iris": "is compact, botanical, and distinctive without being difficult",
    "Lena": "has a soft international feel and a clean everyday rhythm",
    "Miles": "feels warm, cultured, and easy to picture at every age",
    "Ada": "is brief and vintage with more strength than sweetness",
    "Jonah": "lands gentle and grounded with a friendly cadence",
    "Elian": "adds lyrical freshness while keeping pronunciation approachable",
    "Maeve": "is compact, elegant, and strong in one syllable",
    "Silas": "has old-soul polish with a warm modern edge",
    "Elodie": "adds musical romance while staying readable",
    "June": "feels clear, vintage, and warmly straightforward",
    "Louisa": "balances classic substance with a softer, literary rhythm",
    "Margot": "brings polished vintage style without becoming ornate",
    "Arthur": "offers sturdy classic warmth and a bookish backbone",
    "Langston": "carries literary strength and a clear connection to African American cultural history",
    "Malcolm": "feels strong, recognizable, and historically resonant without being overused",
    "Booker": "brings surname-rooted distinction and historical depth",
    "Thurgood": "is rare, substantial, and tied to civil-rights history",
    "Ellington": "adds musical polish and a heritage-rich surname cadence",
    "Frederick": "balances classic strength with historical substance",
    "Bayard": "feels rare, principled, and historically meaningful",
    "Giovanni": "is classic, unmistakably Italian, and warm with substantial history",
    "Leonardo": "feels Italian-rooted, artistic, recognizable, and strong",
    "Lorenzo": "is lyrical, classic, and clearly Italian without feeling obscure",
    "Dante": "brings literary strength and an Italian-rooted distinctive shape",
    "Marco": "is familiar, compact, and warmly Italian",
    "Enzo": "feels compact, energetic, and unmistakably Italian",
    "Alessio": "is lyrical, warm, and Italian-rooted while staying readable",
    "Rocco": "feels strong, distinctive, and Italian-rooted",
    "Santino": "is warm, distinctive, and heritage-rich",
    "Vittorio": "has substantial classic weight and a deeply Italian cadence",
    "Elio": "feels bright, compact, and Mediterranean",
    "Cillian": "is Irish-rooted, distinctive, and strong while staying wearable",
    "Ronan": "feels Irish-rooted, warm, and recognizable without being overused",
    "Eamon": "is Irish-rooted, substantial, and gently classic",
    "Declan": "feels Irish-rooted, strong, and familiar enough for everyday use",
    "Cormac": "brings Irish literary roots with sturdy warmth",
    "Seamus": "is Irish-rooted, warm, and traditional",
    "Lachlan": "feels Scottish-rooted, strong, and outdoorsy",
    "Callum": "is Scottish-rooted, gentle, and familiar",
    "Duncan": "brings sturdy Scottish-rooted classic strength",
    "Alistair": "feels Scottish-rooted, polished, and substantial",
    "Hamish": "is Scottish-rooted, warm, and distinctive",
    "Ewan": "feels Scottish-rooted, compact, and approachable",
    "Nikolai": "is Russian-rooted, substantial, and elegant",
    "Lev": "feels Russian-rooted, brief, and strong",
    "Dmitri": "is Russian-rooted, classic, and distinctive",
    "Mikhail": "feels Russian-rooted, historic, and strong",
    "Ivan": "is Russian-rooted, classic, and direct",
    "Viktor": "feels Russian-rooted, strong, and recognizable",
    "Kai": "is compact and bright with Chinese-rooted modern use",
    "Ming": "feels Chinese-rooted, clear, and luminous",
    "Jian": "is Chinese-rooted, concise, and strong",
    "Wei": "feels Chinese-rooted, brief, and graceful",
    "Jun": "is Chinese-rooted, compact, and warm",
    "Liang": "feels Chinese-rooted, strong, and melodic",
    "Felix": "feels bright and joyful with old-world polish",
    "Graham": "lands tailored and calm with understated strength",
    "Hollis": "has a gentle surname feel with flexible modern wearability",
    "Ivy": "is short, botanical, and lively without being complicated",
    "Rafael": "adds international warmth and an elegant cadence",
    "Serena": "feels graceful and calm with an easy familiar shape",
    "Tessa": "is bright, friendly, and unfussy",
}

BUSINESS_NAME_POOL = [
    ("Northmark", "NORTH-mark", "Credible, directional, and built for a scalable brand."),
    ("Brightline", "BRYTE-line", "Clear, energetic, and easy to picture on a launch card."),
    ("Crestwell", "KREST-wel", "Polished and optimistic with a practical business sound."),
    ("Signal House", "SIG-nul hows", "Memorable, strategic, and strong for a service brand."),
    ("Launchmere", "LAWNCH-meer", "Founder-friendly with a modern momentum cue."),
    ("Fieldstone", "FEELD-stohn", "Grounded, trustworthy, and substantial."),
    ("Motive Lane", "MOH-tiv lane", "Human, purposeful, and flexible across categories."),
    ("Arc & Anchor", "ARK and AN-kur", "Balanced between momentum and trust."),
]

BUSINESS_REFINED_POOL = [
    ("Kindred Works", "KIN-drid werks", "Warm, professional, and relationship-led."),
    ("Blueframe", "BLOO-fraym", "Structured, modern, and easy to brand visually."),
    ("Goldleaf", "GOHLD-leef", "Premium and approachable with a refined finish."),
    ("Tradecraft", "TRAYD-kraft", "Skilled, practical, and category-flexible."),
    ("Vista & Co.", "VIS-tuh and koh", "Open, polished, and ready for a broader offer."),
    ("Foundry Point", "FOWN-dree poynt", "Maker-minded with a clear launch signal."),
    ("Noble Signal", "NOH-bul SIG-nul", "Credible and memorable without feeling cold."),
    ("Relay North", "REE-lay NORTH", "Energetic, operational, and easy to extend."),
]

BUSINESS_FINALIST_POOL = [
    ("Northmark", "NORTH-mark", "Credible, directional, and built for a scalable brand."),
    ("Brightline", "BRYTE-line", "Clear, energetic, and easy to picture on a launch card."),
    ("Signal House", "SIG-nul hows", "Memorable, strategic, and strong for a service brand."),
    ("Kindred Works", "KIN-drid werks", "Warm, professional, and relationship-led."),
    ("Blueframe", "BLOO-fraym", "Structured, modern, and easy to brand visually."),
    ("Foundry Point", "FOWN-dree poynt", "Maker-minded with a clear launch signal."),
]

BUSINESS_EXTRA_POOL = [
    ("Oakline", "OHK-line", "Grounded and simple with durable brand texture."),
    ("Beacon & Field", "BEE-kun and FEELD", "Clear guidance plus practical reach."),
    ("Summitry", "SUH-mit-ree", "Aspirational, compact, and ownable."),
    ("Coppernote", "KAH-per-noht", "Warm and distinctive with an editorial feel."),
    ("Truecourse", "TROO-kors", "Confident, useful, and directionally clear."),
    ("Hearthmark", "HARTH-mark", "Warm, trusted, and suited to people-centered work."),
    ("Lumen Yard", "LOO-men yard", "Bright, creative, and approachable."),
    ("Atlas Bloom", "AT-lus BLOOM", "Growth-oriented with a broader market feel."),
]

BUSINESS_NAME_INSIGHTS = {
    "Northmark": "suggests direction, durability, and a business with a clear point of view",
    "Brightline": "signals clarity and momentum while staying easy to say and remember",
    "Crestwell": "feels credible and optimistic without locking the company into one narrow service",
    "Signal House": "frames the business as strategic, memorable, and built around clear communication",
    "Launchmere": "adds launch energy while staying softer than a hard-tech name",
    "Fieldstone": "creates trust through grounded, durable imagery",
    "Motive Lane": "keeps the name human and purpose-driven while leaving room to grow",
    "Arc & Anchor": "balances forward motion with stability",
    "Kindred Works": "suggests relationship, care, and useful work",
    "Blueframe": "feels structured, visual, and modern enough for a brand system",
    "Goldleaf": "adds a premium cue without sounding cold",
    "Tradecraft": "signals skill, process, and practical credibility",
    "Vista & Co.": "creates room for a broad, polished service offer",
    "Foundry Point": "suggests making, building, and a clear market position",
    "Noble Signal": "combines trust with a memorable communication cue",
    "Relay North": "sounds active, operational, and directionally useful",
}

PRODUCT_NAME_POOL = [
    ("Hearthkit", "HARTH-kit", "Warm, useful, and ready for a package label."),
    ("Lumaform", "LOO-muh-form", "Bright, tactile, and flexible across product lines."),
    ("Kindle & Co.", "KIN-dul and koh", "Friendly, giftable, and easy to frame visually."),
    ("Brightpack", "BRYTE-pak", "Clear, energetic, and direct for shelf or listing use."),
    ("Fieldmint", "FEELD-mint", "Fresh, natural, and product-ready without feeling generic."),
    ("Nestory", "NES-tor-ee", "Cozy, memorable, and lightly invented."),
    ("Vela Goods", "VAY-luh goods", "Warm, polished, and premium without being cold."),
    ("Oakhue", "OHK-hyoo", "Grounded, tactile, and visually distinctive."),
]

PRODUCT_REFINED_POOL = [
    ("Labelwise", "LAY-bul-wyze", "Practical, smart, and easy to understand."),
    ("Softcraft", "SOFT-kraft", "Tactile and maker-minded with warm shelf appeal."),
    ("Copperleaf", "KAH-per-leef", "Warm, premium, and visually rich."),
    ("Dailywell", "DAY-lee-wel", "Routine-friendly and clear for consumer products."),
    ("Motive Kit", "MOH-tiv kit", "Purposeful, useful, and modular."),
    ("Bloomcase", "BLOOM-kays", "Fresh and package-ready with optimistic lift."),
    ("Trueform", "TROO-form", "Confident, simple, and product-line friendly."),
    ("Havenly", "HAY-vun-lee", "Soft, comforting, and buyer-friendly."),
]

PRODUCT_FINALIST_POOL = [
    ("Hearthkit", "HARTH-kit", "Warm, useful, and ready for a package label."),
    ("Lumaform", "LOO-muh-form", "Bright, tactile, and flexible across product lines."),
    ("Fieldmint", "FEELD-mint", "Fresh, natural, and product-ready without feeling generic."),
    ("Vela Goods", "VAY-luh goods", "Warm, polished, and premium without being cold."),
    ("Softcraft", "SOFT-kraft", "Tactile and maker-minded with warm shelf appeal."),
    ("Trueform", "TROO-form", "Confident, simple, and product-line friendly."),
]

PRODUCT_EXTRA_POOL = [
    ("Goodlabel", "GOOD-lay-bul", "Plainspoken and trustworthy for packaging."),
    ("Morrow Made", "MOR-oh mayd", "Thoughtful, crafted, and line-extension friendly."),
    ("Tendril", "TEN-dril", "Organic, compact, and visually distinctive."),
    ("Northgoods", "NORTH-goodz", "Practical, durable, and consumer-ready."),
    ("Linenly", "LIN-en-lee", "Soft, tactile, and approachable."),
    ("Arcwell", "ARK-wel", "Simple, structured, and wellness-adjacent."),
    ("Madebright", "MAYD-brite", "Optimistic, clear, and retail-friendly."),
    ("Pouch & Point", "POWCH and POYNT", "Memorable and packaging-forward."),
]

PRODUCT_NAME_INSIGHTS = {
    "Hearthkit": "signals warmth, utility, and a product that belongs in everyday routines",
    "Lumaform": "combines brightness with shape, making it flexible for visual packaging",
    "Kindle & Co.": "feels friendly and giftable while leaving room for a broader line",
    "Brightpack": "makes the product context immediate and keeps the sound energetic",
    "Fieldmint": "adds freshness and natural texture without overexplaining the category",
    "Nestory": "suggests cozy use and a lightly invented brandable shape",
    "Vela Goods": "feels polished and tangible, with room for a product family",
    "Oakhue": "pairs grounded material imagery with a visual color cue",
    "Labelwise": "signals practical clarity and product decision support",
    "Softcraft": "leans tactile, warm, and maker-minded",
    "Copperleaf": "adds premium warmth and a strong packaging image",
    "Dailywell": "connects the product to routine and everyday benefit",
    "Motive Kit": "frames the product as useful, modular, and purposeful",
    "Bloomcase": "suggests freshness and containment in a package-friendly shape",
    "Trueform": "feels clear, confident, and extensible across product variants",
    "Havenly": "creates comfort and buyer warmth with a soft consumer sound",
}


def slugify(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean or "name"


def _brief_text(brief: NamingBrief, key: str, default: str = "") -> str:
    value = brief.inputs.get(key, default)
    return str(value).strip()


def _pet_fit_note(name: str, species: str, personality: str) -> str:
    animal = (species or "pet").lower()
    if personality:
        return f"Best for a {personality.lower()} {animal} whose name should feel natural in everyday use."
    return f"Best for a {animal} whose name should be easy to say, remember, and share."


def _baby_fit_note(name: str, gender: str, sound: str) -> str:
    direction = f" for a {gender.lower()} direction" if gender else ""
    if sound:
        return f"Best{direction} if you want a {sound.lower()} name that can grow from childhood into adulthood."
    return f"Best{direction} if you want a name that feels warm now and still substantial later."


def generate_names(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int = 1,
    taste_summary: str = "",
    taste_profile: TasteProfile | None = None,
    previous_names: list[str] | None = None,
    use_ai: bool = False,
) -> list[NameResult]:
    fallback = generate_fallback_names(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_summary=taste_summary,
        previous_names=previous_names or [],
    )
    for name in fallback:
        name.metadata.setdefault("provider", "fallback")

    if use_ai:
        try:
            from namengine.core.model_router import generate_with_router

            routed = generate_with_router(
                vertical=vertical,
                brief=brief,
                round_number=round_number,
                taste_profile=taste_profile,
                previous_names=previous_names or [],
            )
        except Exception as exc:  # pragma: no cover - production safety net
            for name in fallback:
                name.metadata["ai_requested"] = True
                name.metadata["ai_fell_back"] = True
                name.metadata["ai_fallback_reason"] = type(exc).__name__
                name.metadata["ai_fallback_message"] = str(exc)[:500]
            return fallback

        if routed:
            if vertical.slug == "business":
                return enrich_business_domain_info(routed)
            return routed

    return fallback


def generate_fallback_names(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int = 1,
    taste_summary: str = "",
    previous_names: list[str] | None = None,
) -> list[NameResult]:
    if vertical.slug == "baby":
        return _generate_baby_fallback_names(
            vertical=vertical,
            brief=brief,
            round_number=round_number,
            taste_summary=taste_summary,
            previous_names=previous_names or [],
        )
    if vertical.slug == "business":
        return _generate_business_fallback_names(
            vertical=vertical,
            brief=brief,
            round_number=round_number,
            taste_summary=taste_summary,
            previous_names=previous_names or [],
        )
    if vertical.slug == "product":
        return _generate_product_fallback_names(
            vertical=vertical,
            brief=brief,
            round_number=round_number,
            taste_summary=taste_summary,
            previous_names=previous_names or [],
        )

    species = _brief_text(brief, "pet_type") or _brief_text(brief, "species", "pet")
    personality = _brief_text(brief, "vibe") or _brief_text(brief, "personality")
    style = _brief_text(brief, "style", "warm and wearable")
    avoid_text = ", ".join(brief.avoid)

    pool = PET_NAME_POOL + PET_REFINED_POOL + PET_EXTRA_POOL
    if brief.inputs.get("original_mode") == "true" or _brief_text(brief, "discovery_style") == "Completely original":
        pool = PET_ORIGINAL_POOL
    elif round_number == 2:
        pool = PET_REFINED_POOL + PET_EXTRA_POOL
    elif round_number >= 4:
        pool = PET_EXTRA_POOL + PET_ORIGINAL_POOL
    elif round_number >= 3:
        pool = PET_FINALIST_POOL + PET_EXTRA_POOL

    if round_number >= 4:
        previous = {name.lower() for name in (previous_names or [])}
        filtered_pool = [item for item in pool if item[0].lower() not in previous]
        if len(filtered_pool) >= min(6, vertical.default_result_count):
            pool = filtered_pool

    starting_letter = _brief_text(brief, "starting_letter").lower()[:1]
    if starting_letter:
        matching = [item for item in pool if item[0].lower().startswith(starting_letter)]
        if matching:
            pool = matching + [item for item in pool if item not in matching]

    pool = _rank_pool_for_taste(vertical.slug, brief, pool)

    results: list[NameResult] = []
    for index, (name, pronunciation, opener) in enumerate(pool, start=1):
        result_id = f"{vertical.slug}-{index}"
        risks = []
        if name.lower() in {item.lower() for item in brief.avoid}:
            risks.append("This name matches something in the avoid list.")
        if len(name) > 8:
            risks.append("Slightly longer name; test how it feels when called.")

        if not risks:
            risks.append("Low practical risk; still test it out loud.")

        insight = PET_NAME_INSIGHTS.get(
            name,
            "balances original sound, everyday usability, and a memorable emotional cue",
        )
        why = (
            f"{name} works because it {insight}. "
            f"It stays in the {style.lower()} lane while giving a {species.lower()} name a distinct point of view."
        )
        if taste_summary:
            why += f" {taste_summary}"
        if avoid_text:
            why += f" It also stays mindful of your avoid list: {avoid_text}."

        results.append(
            NameResult(
                id=result_id,
                name=name,
                slug=slugify(name),
                pronunciation=pronunciation,
                tagline=opener,
                meaning="A wearable pet name shaped for callability and warmth.",
                why_this_name=why,
                fit_note=_pet_fit_note(name, species, personality),
                risks=risks,
                tags=["callable", "warm", "pet-ready"],
                scores={
                    "callability": 0.92 if len(name) <= 5 else 0.84,
                    "warmth": 0.88,
                    "distinctiveness": 0.62 if name in {"Milo", "Toby", "Finn"} else 0.76,
                },
                metadata={"source": "phase3_fallback", "round_number": round_number},
            )
        )

    if round_number >= 3:
        return validate_results(vertical, brief, results[:6])
    return validate_results(vertical, brief, results[: vertical.default_result_count])



def _taste_strengths(brief: NamingBrief) -> dict[str, float]:
    strengths: dict[str, float] = {}
    for key, value in brief.inputs.items():
        if not str(key).startswith("taste_strength_"):
            continue
        section = str(key)[len("taste_strength_") :]
        try:
            strengths[section] = max(0.0, min(100.0, float(value))) / 100.0
        except (TypeError, ValueError):
            continue
    return strengths


def _field_section_key(key: str, vertical: str) -> str:
    section_map = {
        "baby": {
            "gender": "about_your_baby",
            "family_context": "about_your_baby",
            "notes": "about_your_baby",
            "discovery_style": "name_style",
            "style": "name_style",
            "timeless_vs_distinctive": "name_style",
            "familiarity_preference": "name_style",
            "sound": "fit_and_feeling",
            "cultural_context": "fit_and_feeling",
            "partner_alignment": "fit_and_feeling",
            "avoid": "fit_and_feeling",
        },
        "pet": {
            "pet_type": "about_your_pet",
            "species": "about_your_pet",
            "pet_gender": "about_your_pet",
            "pet_breed": "about_your_pet",
            "pet_color": "about_your_pet",
            "pet_life_stage": "about_your_pet",
            "notes": "about_your_pet",
            "discovery_style": "name_style",
            "style": "name_style",
            "timeless_vs_distinctive": "name_style",
            "familiarity_preference": "name_style",
            "pronunciation_importance": "fit_and_feeling",
            "vibe": "fit_and_feeling",
            "cultural_context": "fit_and_feeling",
            "partner_alignment": "fit_and_feeling",
        },
        "business": {
            "business_description": "about_the_business",
            "industry": "about_the_business",
            "stage": "about_the_business",
            "audience": "about_the_business",
            "notes": "about_the_business",
            "style": "name_style",
            "name_shape": "name_style",
            "timeless_vs_distinctive": "name_style",
            "cultural_context": "name_style",
            "domain_preference": "launch_fit",
            "partner_alignment": "launch_fit",
            "avoid": "launch_fit",
        },
        "product": {
            "product_description": "about_the_product",
            "category": "about_the_product",
            "stage": "about_the_product",
            "audience": "about_the_product",
            "notes": "about_the_product",
            "style": "name_style",
            "name_shape": "name_style",
            "timeless_vs_distinctive": "name_style",
            "cultural_context": "name_style",
            "sales_channel": "shelf_fit",
            "partner_alignment": "shelf_fit",
            "avoid": "shelf_fit",
        },
    }
    return section_map.get(vertical, {}).get(key, "")


def _tokenize_taste(value: str) -> set[str]:
    raw = re.findall(r"[a-z]+", value.lower())
    expansions = {
        "classic": {"classic", "timeless", "familiar", "traditional", "vintage"},
        "timeless": {"classic", "timeless", "familiar", "traditional"},
        "rare": {"rare", "distinctive", "uncommon", "ownable", "unexpected"},
        "distinctive": {"rare", "distinctive", "uncommon", "memorable", "ownable"},
        "strong": {"strong", "bold", "tailored", "sturdy", "crisp"},
        "soft": {"soft", "gentle", "warm", "lyrical", "romantic"},
        "warm": {"warm", "gentle", "friendly", "cozy", "kindred"},
        "modern": {"modern", "sleek", "fresh", "current"},
        "premium": {"premium", "refined", "polished", "elegant"},
        "clear": {"clear", "credible", "direct", "descriptive"},
        "playful": {"playful", "bright", "bouncy", "quirky"},
        "nature": {"nature", "botanical", "outdoor", "field", "leaf", "stone"},
        "italian": {"italian", "italy", "mediterranean"},
        "italy": {"italian", "italy", "mediterranean"},
        "irish": {"irish", "ireland", "gaelic", "celtic"},
        "ireland": {"irish", "ireland", "gaelic", "celtic"},
        "scottish": {"scottish", "scotland", "gaelic", "celtic"},
        "scotland": {"scottish", "scotland", "gaelic", "celtic"},
        "russian": {"russian", "slavic"},
        "russia": {"russian", "slavic"},
        "chinese": {"chinese", "mandarin", "sino"},
        "china": {"chinese", "mandarin", "sino"},
    }
    tokens = set(raw)
    for token in raw:
        tokens.update(expansions.get(token, set()))
    return tokens


GENERIC_CONTEXT_TOKENS = {
    "background",
    "context",
    "cultural",
    "culture",
    "family",
    "heritage",
    "inspiration",
}


def _taste_tokens_for_field(key: str, value: str) -> set[str]:
    tokens = _tokenize_taste(value)
    if key in {"family_context", "cultural_context"}:
        # Generic words like "heritage" and "family" should tell us which
        # response bucket matters, but they should not make every heritage-tagged
        # candidate look relevant. Specific identity tokens must carry the match.
        tokens -= GENERIC_CONTEXT_TOKENS
    return tokens


HERITAGE_GROUP_TOKENS = {
    "african_american": {"african", "american", "black"},
    "italian": {"italian", "italy", "mediterranean"},
    "irish": {"irish", "ireland"},
    "scottish": {"scottish", "scotland"},
    "russian": {"russian", "slavic"},
    "chinese": {"chinese", "mandarin", "sino"},
}


def _heritage_groups_from_tokens(tokens: set[str]) -> set[str]:
    groups: set[str] = set()
    for group, group_tokens in HERITAGE_GROUP_TOKENS.items():
        if group == "african_american":
            if {"african", "american"} <= tokens or "black" in tokens:
                groups.add(group)
            continue
        if tokens & group_tokens:
            groups.add(group)
    return groups


def _requested_heritage_groups(brief: NamingBrief) -> set[str]:
    tokens: set[str] = set()
    for key in ("family_context", "cultural_context", "notes"):
        value = brief.inputs.get(key)
        if value:
            tokens.update(_taste_tokens_for_field(key, str(value)))
    return _heritage_groups_from_tokens(tokens)


USER_TEXT_KEYS = {
    "notes",
    "family_context",
    "partner_alignment",
    "avoid",
    "business_description",
    "product_description",
    "industry",
    "category",
    "pet_breed",
    "pet_color",
}


NAME_TRAITS = {
    # Baby
    "eloise": "classic elegant literary soft warm polished graceful",
    "maya": "warm simple familiar global soft",
    "clara": "classic clear timeless gentle bright familiar",
    "julian": "classic soft tailored timeless intelligent gentle",
    "theo": "classic warm friendly modern familiar",
    "maren": "calm uncommon coastal distinctive soft",
    "nora": "classic familiar graceful strong warm",
    "rowan": "nature modern flexible warm distinctive",
    "iris": "botanical crisp distinctive floral classic",
    "lena": "soft warm international simple gentle",
    "miles": "warm polished friendly classic",
    "ada": "vintage classic brief strong substantial",
    "jonah": "gentle grounded familiar warm",
    "elian": "lyrical uncommon distinctive soft",
    "maeve": "compact elegant strong distinctive",
    "silas": "tailored warm old-soul classic",
    "celia": "gentle melodic classic soft",
    "noemi": "lyrical international warm distinctive",
    "romy": "bright compact stylish modern",
    "ansel": "tailored artistic old-soul distinctive",
    "bennett": "polished friendly surname classic",
    "luca": "italian italy mediterranean warm global friendly modern recognizable",
    "mira": "clear graceful celestial soft",
    "owen": "warm familiar grounded classic",
    "elodie": "romantic musical uncommon readable soft",
    "june": "clear vintage sunny classic",
    "louisa": "classic literary warm substantial",
    "margot": "polished vintage stylish classic",
    "arthur": "classic sturdy bookish warm",
    "felix": "bright joyful classic friendly",
    "graham": "tailored calm understated classic",
    "hollis": "gentle surname modern flexible",
    "ivy": "botanical brief lively nature",
    "rafael": "warm elegant international",
    "serena": "calm graceful familiar soft",
    "tessa": "bright friendly unfussy familiar",
    "anya": "warm compact international",
    "calla": "botanical soft uncommon nature",
    "ellis": "gentle tailored flexible modern",
    "hugo": "bright classic stylish",
    "lyra": "musical celestial distinctive soft",
    "reid": "clean strong understated",
    "soren": "distinctive calm literary",
    "vera": "clear vintage confident classic",
    "alden": "gentle literary substantial",
    "alma": "warm vintage soulful soft",
    "beatrice": "classic lively character vintage",
    "cassian": "ancient elegant distinctive strong",
    "daphne": "botanical bright mythic nature",
    "emil": "compact european soft",
    "flora": "garden vintage botanical nature",
    "greta": "strong crisp old-world",
    "harlan": "grounded surname warm strong",
    "ida": "brief vintage strong",
    "leona": "warm strong graceful",
    "matteo": "italian italy mediterranean lyrical global friendly classic recognizable",
    "nico": "italian italy mediterranean compact stylish easygoing recognizable",
    "opal": "gemstone vintage gentle",
    "petra": "strong international distinctive",
    "quinn": "clean modern flexible",
    "rhea": "mythic brief bright",
    "stellan": "calm nordic tailored distinctive",
    "thea": "soft classic luminous",
    "zara": "sleek global confident strong",
    "langston": "african american black heritage historical history literary strong distinctive classic recognizable cultural",
    "malcolm": "african american black heritage historical history civil rights strong distinctive classic recognizable cultural",
    "booker": "african american black heritage historical history surname strong distinctive uncommon recognizable cultural",
    "thurgood": "african american black heritage historical history civil rights rare strong distinctive substantial cultural",
    "ellington": "african american black heritage historical history musical jazz polished surname distinctive cultural",
    "frederick": "african american black heritage historical history classic strong recognizable substantial cultural",
    "bayard": "african american black heritage historical history civil rights rare principled distinctive strong cultural",
    "giovanni": "italian italy mediterranean heritage classic strong recognizable lyrical cultural",
    "leonardo": "italian italy mediterranean heritage classic strong artistic recognizable cultural",
    "lorenzo": "italian italy mediterranean heritage classic strong lyrical recognizable cultural",
    "dante": "italian italy mediterranean heritage literary classic strong distinctive recognizable cultural",
    "marco": "italian italy mediterranean heritage classic strong familiar recognizable cultural",
    "enzo": "italian italy mediterranean heritage compact strong distinctive recognizable cultural",
    "alessio": "italian italy mediterranean heritage lyrical distinctive recognizable cultural",
    "rocco": "italian italy mediterranean heritage strong distinctive familiar cultural",
    "santino": "italian italy mediterranean heritage warm classic distinctive cultural",
    "vittorio": "italian italy mediterranean heritage classic strong distinctive cultural",
    "elio": "italian italy mediterranean heritage warm compact lyrical distinctive cultural",
    "cillian": "irish ireland gaelic celtic heritage strong distinctive recognizable cultural",
    "ronan": "irish ireland gaelic celtic heritage warm strong recognizable cultural",
    "eamon": "irish ireland gaelic celtic heritage classic substantial warm cultural",
    "declan": "irish ireland gaelic celtic heritage strong familiar recognizable cultural",
    "cormac": "irish ireland gaelic celtic heritage literary sturdy strong cultural",
    "seamus": "irish ireland gaelic celtic heritage traditional warm recognizable cultural",
    "lachlan": "scottish scotland gaelic celtic heritage strong outdoorsy distinctive cultural",
    "callum": "scottish scotland gaelic celtic heritage gentle familiar recognizable cultural",
    "duncan": "scottish scotland heritage classic sturdy strong recognizable cultural",
    "alistair": "scottish scotland heritage polished substantial classic distinctive cultural",
    "hamish": "scottish scotland heritage warm distinctive recognizable cultural",
    "ewan": "scottish scotland heritage compact approachable recognizable cultural",
    "nikolai": "russian slavic heritage substantial elegant classic distinctive cultural",
    "lev": "russian slavic heritage brief strong classic distinctive cultural",
    "dmitri": "russian slavic heritage classic distinctive recognizable cultural",
    "mikhail": "russian slavic heritage historic strong classic recognizable cultural",
    "ivan": "russian slavic heritage classic direct recognizable cultural",
    "viktor": "russian slavic heritage strong recognizable classic cultural",
    "kai": "chinese mandarin sino heritage compact bright modern recognizable cultural",
    "ming": "chinese mandarin sino heritage clear luminous compact cultural",
    "jian": "chinese mandarin sino heritage concise strong compact cultural",
    "wei": "chinese mandarin sino heritage brief graceful compact cultural",
    "jun": "chinese mandarin sino heritage compact warm recognizable cultural",
    "liang": "chinese mandarin sino heritage strong melodic distinctive cultural",
    # Pet
    "milo": "dog friendly bright callable familiar playful",
    "juniper": "cat rabbit nature distinctive warm",
    "rory": "dog bird bright bouncy callable playful",
    "clover": "rabbit soft lucky sweet nature",
    "toby": "dog familiar loyal callable",
    "sierra": "horse reptile outdoor graceful calm",
    "maple": "rabbit dog cozy gentle nature",
    "finn": "dog crisp short callable",
    "benny": "dog sunny familiar affectionate",
    "scout": "dog horse adventurous crisp",
    "poppy": "bird rabbit bright sweet playful",
    "ollie": "dog friendly rounded",
    "winnie": "rabbit cat gentle cozy",
    "remy": "cat stylish warm",
    "sunny": "bird dog happy bright",
    "hazel": "cat rabbit nature vintage soft",
    "archie": "dog cheerful vintage familiar",
    "lottie": "rabbit sweet soft",
    "otis": "dog grounded friendly",
    "mabel": "rabbit cozy classic",
    "ziggy": "bird dog playful quirky bright",
    "rosie": "dog rabbit warm familiar",
    "lumo": "bird reptile bright invented original",
    "noriu": "bird soft musical original",
    "kova": "reptile strong sleek original",
    "mavie": "cat sweet lively original",
    "talo": "reptile grounded short original",
    "bramblee": "rabbit nature playful original",
    "solvi": "bird sunny distinctive original",
    "rueby": "rabbit cute bright original",
    # Business
    "northmark": "credible directional durable clear business scalable",
    "brightline": "clear energetic modern memorable business",
    "crestwell": "polished optimistic premium credible",
    "signal house": "strategic memorable service communication credible",
    "launchmere": "modern momentum founder launch distinctive",
    "fieldstone": "grounded trustworthy substantial local",
    "motive lane": "human purposeful flexible friendly",
    "arc & anchor": "momentum trust balanced premium",
    "kindred works": "warm professional relationship friendly",
    "blueframe": "structured modern visual distinctive",
    "goldleaf": "premium refined warm elegant",
    "tradecraft": "skilled practical credible craft",
    "vista & co.": "open polished broad premium",
    "foundry point": "maker building launch clear",
    "noble signal": "credible memorable trust premium",
    "relay north": "energetic operational directional",
    "oakline": "grounded simple durable",
    "beacon & field": "clear guidance practical field",
    "summitry": "aspirational compact ownable distinctive",
    "coppernote": "warm distinctive editorial",
    "truecourse": "confident useful clear directional",
    "hearthmark": "warm trusted people-centered",
    "lumen yard": "bright creative approachable",
    "atlas bloom": "growth broad aspirational",
    # Product
    "hearthkit": "warm useful everyday family practical",
    "lumaform": "bright tactile flexible modern sleek",
    "kindle & co.": "friendly giftable warm approachable",
    "brightpack": "clear energetic shelf ready direct",
    "fieldmint": "fresh natural product ready botanical",
    "nestory": "cozy memorable invented warm",
    "vela goods": "warm polished premium tangible",
    "oakhue": "grounded tactile visual distinctive",
    "labelwise": "practical smart clear descriptive",
    "softcraft": "tactile warm maker shelf",
    "copperleaf": "warm premium visual refined",
    "dailywell": "routine friendly clear wellness",
    "motive kit": "purposeful useful modular modern",
    "bloomcase": "fresh package optimistic shelf",
    "trueform": "clear confident product-line sleek",
    "havenly": "soft comforting buyer warm",
    "goodlabel": "plainspoken trustworthy clear packaging",
    "morrow made": "thoughtful crafted warm",
    "tendril": "organic compact visual distinctive",
    "northgoods": "practical durable consumer",
    "linenly": "soft tactile approachable",
    "arcwell": "simple structured wellness sleek",
    "madebright": "optimistic clear retail",
    "pouch & point": "memorable packaging distinctive",
}


def _candidate_traits(name: str, opener: str) -> set[str]:
    key = name.lower()
    traits = NAME_TRAITS.get(key, "")
    return _tokenize_taste(f"{name} {opener} {traits}")


def _score_candidate_for_taste(
    vertical: str,
    brief: NamingBrief,
    name: str,
    opener: str,
) -> float:
    strengths = _taste_strengths(brief)
    traits = _candidate_traits(name, opener)
    requested_heritage_groups = _requested_heritage_groups(brief)
    candidate_heritage_groups = _heritage_groups_from_tokens(traits)
    if not strengths:
        strengths = {"__default__": 1 / 3}

    score = 0.0
    if requested_heritage_groups:
        matched_heritage_groups = requested_heritage_groups & candidate_heritage_groups
        if matched_heritage_groups:
            score += 28.0 * len(matched_heritage_groups)
        elif candidate_heritage_groups:
            # Avoid letting generic style words pull in the wrong heritage lane.
            score -= 14.0

    for key, value in brief.inputs.items():
        if str(key).startswith("taste_strength_"):
            continue
        section = _field_section_key(str(key), vertical)
        section_strength = strengths.get(section, 0.34 if strengths else 1.0)
        text = str(value)
        tokens = _taste_tokens_for_field(str(key), text)
        if not tokens:
            continue
        overlap = len(tokens & traits)
        if overlap:
            score += overlap * (1.0 + section_strength * 2.2)
        if key in USER_TEXT_KEYS:
            # User-entered language should be at least as strong as preset inputs.
            score += overlap * 1.8
            for token in tokens:
                if token in traits:
                    score += 0.8

    if brief.avoid and _clean_name_key(name) in {_clean_name_key(item) for item in brief.avoid}:
        score -= 100
    return score


def _rank_pool_for_taste(
    vertical: str,
    brief: NamingBrief,
    pool: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    scored = [
        (_score_candidate_for_taste(vertical, brief, name, opener), index, item)
        for index, item in enumerate(pool)
        for name, _pronunciation, opener in [item]
    ]
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [item for _score, _index, item in scored]


def _generate_baby_fallback_names(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_summary: str = "",
    previous_names: list[str] | None = None,
) -> list[NameResult]:
    gender = _brief_text(brief, "gender")
    sound = _brief_text(brief, "sound")
    style = _brief_text(brief, "style", "warm and wearable")
    family_context = _brief_text(brief, "family_context")
    avoid_text = ", ".join(brief.avoid)

    pool = BABY_NAME_POOL + BABY_REFINED_POOL + BABY_FINALIST_POOL + BABY_EXTRA_POOL + BABY_WIDE_EXPLORATION_POOL
    if round_number == 2:
        pool = BABY_REFINED_POOL + BABY_WIDE_EXPLORATION_POOL
    elif round_number >= 4:
        pool = BABY_EXTRA_POOL + BABY_WIDE_EXPLORATION_POOL
    elif round_number >= 3:
        pool = BABY_FINALIST_POOL + BABY_EXTRA_POOL + BABY_WIDE_EXPLORATION_POOL

    result_count = 6 if round_number >= 3 else vertical.default_result_count
    pool = _rank_pool_for_taste(vertical.slug, brief, pool)
    pool = _filter_baby_pool_for_brief(brief, pool, minimum_count=result_count)

    previous = {name.lower() for name in (previous_names or [])}
    if previous:
        filtered_pool = [item for item in pool if item[0].lower() not in previous]
        if len(filtered_pool) >= min(6, vertical.default_result_count):
            pool = filtered_pool

    results: list[NameResult] = []
    for index, (name, pronunciation, opener) in enumerate(pool, start=1):
        risks = []
        if name.lower() in {item.lower() for item in brief.avoid}:
            risks.append("This name matches something in the avoid list.")
        if len(name) <= 3:
            risks.append("Short name; test it with the surname for rhythm and initials.")
        if not risks:
            risks.append("Low practical risk; still test initials, surname flow, and family associations.")

        insight = BABY_NAME_INSIGHTS.get(
            name,
            "balances sound, warmth, and everyday wearability",
        )
        why = (
            f"{name} works because it {insight}. "
            f"It stays in the {style.lower()} lane while giving the name enough substance for every stage of life."
        )
        if family_context:
            why += f" It should be tested against your family context: {family_context}."
        if taste_summary:
            why += f" {taste_summary}"
        if avoid_text:
            why += f" It also stays mindful of your avoid list: {avoid_text}."

        results.append(
            NameResult(
                id=f"{vertical.slug}-{index}",
                name=name,
                slug=slugify(name),
                pronunciation=pronunciation,
                tagline=opener,
                meaning="A baby name shaped for sound, warmth, family fit, and long-term wearability.",
                why_this_name=why,
                fit_note=_baby_fit_note(name, gender, sound),
                risks=risks,
                tags=["wearable", "warm", "family-ready"],
                scores={
                    "callability": 0.9 if len(name) <= 6 else 0.82,
                    "warmth": 0.88,
                    "distinctiveness": 0.58 if name in {"Maya", "Nora", "Theo"} else 0.74,
                },
                metadata={"source": "baby_fallback", "round_number": round_number},
            )
        )

    return validate_results(vertical, brief, results)[:result_count]


def _generate_business_fallback_names(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_summary: str = "",
    previous_names: list[str] | None = None,
) -> list[NameResult]:
    business_description = _brief_text(brief, "business_description")
    industry = _brief_text(brief, "industry", "business")
    audience = _brief_text(brief, "audience", "customers")
    style = _brief_text(brief, "style", "credible and launch-ready")
    domain_preference = _brief_text(brief, "domain_preference")
    avoid_text = ", ".join(brief.avoid)

    pool = BUSINESS_NAME_POOL + BUSINESS_REFINED_POOL + BUSINESS_EXTRA_POOL
    if round_number == 2:
        pool = BUSINESS_REFINED_POOL + BUSINESS_EXTRA_POOL
    elif round_number >= 4:
        pool = BUSINESS_EXTRA_POOL
    elif round_number >= 3:
        pool = BUSINESS_FINALIST_POOL

    previous = {name.lower() for name in (previous_names or [])}
    if previous:
        filtered_pool = [item for item in pool if item[0].lower() not in previous]
        if len(filtered_pool) >= min(6, vertical.default_result_count):
            pool = filtered_pool

    result_count = 6 if round_number >= 3 else vertical.default_result_count
    pool = _rank_pool_for_taste(vertical.slug, brief, pool)
    results: list[NameResult] = []
    for index, (name, pronunciation, opener) in enumerate(pool, start=1):
        clean_name = _clean_name_key(name)
        risks = [
            "Run trademark, domain, and social-handle checks before committing."
        ]
        if clean_name in {_clean_name_key(item) for item in brief.avoid}:
            risks.insert(0, "This name matches something in the avoid list.")
        if len(clean_name) > 13 or "and" in clean_name:
            risks.append("Longer brand shape; test email, logo, and handle fit.")
        if domain_preference == "Exact .com matters":
            risks.append("Exact .com priority may require a modifier or alternate spelling.")

        insight = BUSINESS_NAME_INSIGHTS.get(
            name,
            "balances memorability, category flexibility, and a credible launch feel",
        )
        context = (
            f" for {audience.lower()}" if audience and audience != "Other" else ""
        )
        why = (
            f"{name} works because it {insight}. It stays in the "
            f"{style.lower()} lane while giving a {industry.lower()} brand room to grow{context}."
        )
        if business_description:
            why += f" It should be tested against the core offer: {business_description}."
        if taste_summary:
            why += f" {taste_summary}"
        if avoid_text:
            why += f" It also stays mindful of your avoid list: {avoid_text}."

        results.append(
            NameResult(
                id=f"{vertical.slug}-{index}",
                name=name,
                slug=slugify(name),
                pronunciation=pronunciation,
                tagline=opener,
                meaning=(
                    "A business name shaped for category fit, memorability, "
                    "brand stretch, and practical launch review."
                ),
                why_this_name=why,
                fit_note=_business_fit_note(industry, audience, style),
                risks=risks,
                tags=["brandable", "launch-ready", "business"],
                scores={
                    "memorability": 0.88 if len(clean_name) <= 11 else 0.78,
                    "category_fit": 0.82 if industry else 0.68,
                    "launch_readiness": 0.72,
                },
                metadata={"source": "business_fallback", "round_number": round_number},
            )
        )

    validated = validate_results(vertical, brief, results)[:result_count]
    return enrich_business_domain_info(validated)


def _generate_product_fallback_names(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_summary: str = "",
    previous_names: list[str] | None = None,
) -> list[NameResult]:
    product_description = _brief_text(brief, "product_description")
    category = _brief_text(brief, "category", "product")
    audience = _brief_text(brief, "audience", "buyers")
    style = _brief_text(brief, "style", "clear and shelf-ready")
    sales_channel = _brief_text(brief, "sales_channel")
    avoid_text = ", ".join(brief.avoid)

    pool = PRODUCT_NAME_POOL + PRODUCT_REFINED_POOL + PRODUCT_EXTRA_POOL
    if round_number == 2:
        pool = PRODUCT_REFINED_POOL + PRODUCT_EXTRA_POOL
    elif round_number >= 4:
        pool = PRODUCT_EXTRA_POOL
    elif round_number >= 3:
        pool = PRODUCT_FINALIST_POOL

    previous = {name.lower() for name in (previous_names or [])}
    if previous:
        filtered_pool = [item for item in pool if item[0].lower() not in previous]
        if len(filtered_pool) >= min(6, vertical.default_result_count):
            pool = filtered_pool

    result_count = 6 if round_number >= 3 else vertical.default_result_count
    pool = _rank_pool_for_taste(vertical.slug, brief, pool)
    results: list[NameResult] = []
    for index, (name, pronunciation, opener) in enumerate(pool, start=1):
        clean_name = _clean_name_key(name)
        risks = [
            "Check trademark, category claims, packaging fit, and marketplace similarity before launch."
        ]
        if clean_name in {_clean_name_key(item) for item in brief.avoid}:
            risks.insert(0, "This name matches something in the avoid list.")
        if len(clean_name) > 13 or "and" in clean_name:
            risks.append("Longer product shape; test label, SKU, and small-screen listing fit.")
        if sales_channel == "Retail shelf":
            risks.append("Retail shelf use needs an extra quick-read test at package distance.")

        insight = PRODUCT_NAME_INSIGHTS.get(
            name,
            "balances shelf clarity, buyer appeal, and product-line flexibility",
        )
        context = (
            f" for {audience.lower()}" if audience and audience != "Other" else ""
        )
        why = (
            f"{name} works because it {insight}. It stays in the "
            f"{style.lower()} lane while giving a {category.lower()} product a clear first impression{context}."
        )
        if product_description:
            why += f" It should be tested against the product promise: {product_description}."
        if taste_summary:
            why += f" {taste_summary}"
        if avoid_text:
            why += f" It also stays mindful of your avoid list: {avoid_text}."

        results.append(
            NameResult(
                id=f"{vertical.slug}-{index}",
                name=name,
                slug=slugify(name),
                pronunciation=pronunciation,
                tagline=opener,
                meaning=(
                    "A product name shaped for shelf clarity, buyer appeal, "
                    "category fit, and launch review."
                ),
                why_this_name=why,
                fit_note=_product_fit_note(category, audience, style, sales_channel),
                risks=risks,
                tags=["shelf-ready", "buyer-friendly", "product"],
                scores={
                    "shelf_clarity": 0.88 if len(clean_name) <= 11 else 0.76,
                    "buyer_appeal": 0.82,
                    "launch_readiness": 0.7,
                },
                metadata={"source": "product_fallback", "round_number": round_number},
            )
        )

    return validate_results(vertical, brief, results)[:result_count]


def _business_fit_note(industry: str, audience: str, style: str) -> str:
    audience_note = f" for {audience.lower()}" if audience and audience != "Other" else ""
    return (
        f"Best if you want a {style.lower()} name that can signal "
        f"{industry.lower()} credibility{audience_note} without boxing in future growth."
    )


def _product_fit_note(category: str, audience: str, style: str, sales_channel: str) -> str:
    audience_note = f" for {audience.lower()}" if audience and audience != "Other" else ""
    channel_note = f" in a {sales_channel.lower()} context" if sales_channel else ""
    return (
        f"Best if you want a {style.lower()} name that gives a "
        f"{category.lower()} product a clear buyer signal{audience_note}{channel_note}."
    )


def _filter_baby_pool_for_brief(
    brief: NamingBrief,
    pool: list[tuple[str, str, str]],
    minimum_count: int,
) -> list[tuple[str, str, str]]:
    avoid = {_clean_name_key(item) for item in brief.avoid}

    def allowed(item: tuple[str, str, str]) -> bool:
        name = item[0]
        return (
            is_baby_name_allowed_for_gender(brief, name)
            and _clean_name_key(name) not in avoid
        )

    filtered_pool = [
        item for item in pool if allowed(item)
    ]
    if len(filtered_pool) >= minimum_count:
        return filtered_pool

    supplemental_pool = (
        BABY_NAME_POOL
        + BABY_REFINED_POOL
        + BABY_FINALIST_POOL
        + BABY_EXTRA_POOL
        + BABY_WIDE_EXPLORATION_POOL
    )
    seen = {item[0].lower() for item in filtered_pool}
    for item in supplemental_pool:
        name = item[0]
        if name.lower() in seen or not allowed(item):
            continue
        filtered_pool.append(item)
        seen.add(name.lower())
        if len(filtered_pool) >= minimum_count:
            return filtered_pool

    return filtered_pool


def _clean_name_key(name: str) -> str:
    return "".join(character for character in name.lower() if character.isalpha())
