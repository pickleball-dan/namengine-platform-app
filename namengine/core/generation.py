"""Shared generation interface for NamEngine."""

from __future__ import annotations

import re

from namengine.core.schemas import (
    NameResult,
    NamingBrief,
    TasteProfile,
    VerticalConfig,
)
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
    "Felix": "feels bright and joyful with old-world polish",
    "Graham": "lands tailored and calm with understated strength",
    "Hollis": "has a gentle surname feel with flexible modern wearability",
    "Ivy": "is short, botanical, and lively without being complicated",
    "Rafael": "adds international warmth and an elegant cadence",
    "Serena": "feels graceful and calm with an easy familiar shape",
    "Tessa": "is bright, friendly, and unfussy",
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
    use_ai: bool = True,
) -> list[NameResult]:
    if use_ai:
        from namengine.core.model_router import generate_with_router

        routed = generate_with_router(
            vertical=vertical,
            brief=brief,
            round_number=round_number,
            taste_profile=taste_profile,
            previous_names=previous_names or [],
        )
        if routed:
            return routed

    return generate_fallback_names(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_summary=taste_summary,
        previous_names=previous_names or [],
    )


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

    species = _brief_text(brief, "pet_type") or _brief_text(brief, "species", "pet")
    personality = _brief_text(brief, "vibe") or _brief_text(brief, "personality")
    style = _brief_text(brief, "style", "warm and wearable")
    avoid_text = ", ".join(brief.avoid)

    pool = PET_NAME_POOL
    if brief.inputs.get("original_mode") == "true" or _brief_text(brief, "discovery_style") == "Completely original":
        pool = PET_ORIGINAL_POOL
    elif round_number == 2:
        pool = PET_REFINED_POOL
    elif round_number >= 4:
        pool = PET_EXTRA_POOL
    elif round_number >= 3:
        pool = PET_FINALIST_POOL

    if round_number >= 4:
        previous = {name.lower() for name in (previous_names or [])}
        filtered_pool = [item for item in pool if item[0].lower() not in previous]
        if filtered_pool:
            pool = filtered_pool

    starting_letter = _brief_text(brief, "starting_letter").lower()[:1]
    if starting_letter:
        matching = [item for item in pool if item[0].lower().startswith(starting_letter)]
        if matching:
            pool = matching + [item for item in pool if item not in matching]

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

    pool = BABY_NAME_POOL
    if round_number == 2:
        pool = BABY_REFINED_POOL + BABY_WIDE_EXPLORATION_POOL
    elif round_number >= 4:
        pool = BABY_EXTRA_POOL + BABY_WIDE_EXPLORATION_POOL
    elif round_number >= 3:
        pool = BABY_FINALIST_POOL + BABY_EXTRA_POOL + BABY_WIDE_EXPLORATION_POOL

    result_count = 6 if round_number >= 3 else vertical.default_result_count
    pool = _filter_baby_pool_for_gender(brief, pool, minimum_count=result_count)

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


def _filter_baby_pool_for_gender(
    brief: NamingBrief,
    pool: list[tuple[str, str, str]],
    minimum_count: int,
) -> list[tuple[str, str, str]]:
    filtered_pool = [
        item for item in pool if is_baby_name_allowed_for_gender(brief, item[0])
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
        if name.lower() in seen or not is_baby_name_allowed_for_gender(brief, name):
            continue
        filtered_pool.append(item)
        seen.add(name.lower())
        if len(filtered_pool) >= minimum_count:
            return filtered_pool

    if len(filtered_pool) < min(6, len(pool)):
        return pool
    return filtered_pool
