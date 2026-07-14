"""Selected-name fact cards for NamEngine.

This is a beta-safe local fact layer: concise, supportive, and clearly framed as
approximate where usage data is not connected to a live source yet.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


BABY_NAME_FACTS: dict[str, dict[str, Any]] = {
    "ada": {
        "origin_meaning": "Germanic roots; often connected with nobility, brightness, or adornment.",
        "approx_usage": "Approx. US use: familiar vintage choice; historically tens of thousands of recorded births.",
        "famous_namesakes": ["Ada Lovelace", "Ada Limón"],
        "nicknames_variants": ["Addie", "Adah", "Aida"],
        "similar_names": ["Ida", "Adele", "Alma", "Vera"],
    },
    "alessio": {
        "origin_meaning": "Italian form related to Alexios/Alexis; often associated with helping or defending.",
        "approx_usage": "Approx. US use: uncommon; a distinctive Italian-rooted choice.",
        "famous_namesakes": ["Alessio Romagnoli", "Alessio Boni"],
        "nicknames_variants": ["Alessandro", "Alex", "Ales"],
        "similar_names": ["Matteo", "Elio", "Lorenzo", "Dario"],
    },
    "ansel": {
        "origin_meaning": "Germanic origin; often interpreted around divine protection.",
        "approx_usage": "Approx. US use: rare-to-uncommon; much less common than classic staples.",
        "famous_namesakes": ["Ansel Adams", "Ansel Elgort"],
        "nicknames_variants": ["Anselm", "Ansell"],
        "similar_names": ["Arlo", "Otto", "Silas", "Alden"],
    },
    "bennett": {
        "origin_meaning": "English surname from Benedict; traditionally linked with blessed.",
        "approx_usage": "Approx. US use: familiar and rising; a modern surname-style favorite.",
        "famous_namesakes": ["Bennett Miller", "Tony Bennett"],
        "nicknames_variants": ["Ben", "Benny", "Benedict"],
        "similar_names": ["Everett", "Beckett", "Benson", "Emmett"],
    },
    "celia": {
        "origin_meaning": "Latin-rooted; often connected with heavenly or celestial meanings.",
        "approx_usage": "Approx. US use: familiar but not overused; a long-standing classic.",
        "famous_namesakes": ["Celia Cruz", "Celia Johnson"],
        "nicknames_variants": ["Cece", "Cecilia", "Celia"],
        "similar_names": ["Clara", "Cecilia", "Sylvia", "Lydia"],
    },
    "clara": {
        "origin_meaning": "Latin origin; means clear, bright, or famous.",
        "approx_usage": "Approx. US use: familiar classic; historically well over 100,000 recorded births.",
        "famous_namesakes": ["Clara Barton", "Clara Schumann"],
        "nicknames_variants": ["Claire", "Clare", "Clarie"],
        "similar_names": ["Cora", "Nora", "Alice", "Louisa"],
    },
    "cora": {
        "origin_meaning": "Greek-rooted name often linked with maiden or heart.",
        "approx_usage": "Approx. US use: familiar vintage revival; historically many tens of thousands of recorded births.",
        "famous_namesakes": ["Cora Coralina", "Cora Crawley (fictional)"],
        "nicknames_variants": ["Coralie", "Corinne", "Cori"],
        "similar_names": ["Clara", "Nora", "Flora", "Ada"],
    },
    "dante": {
        "origin_meaning": "Italian form related to Durante; often interpreted as enduring.",
        "approx_usage": "Approx. US use: familiar but not everywhere; a recognizable Italian-literary choice.",
        "famous_namesakes": ["Dante Alighieri", "Dante Basco"],
        "nicknames_variants": ["Durante", "Donte"],
        "similar_names": ["Luca", "Marco", "Enzo", "Matteo"],
    },
    "elian": {
        "origin_meaning": "Multilingual-feeling name related in some uses to Elian/Élian; often associated with light or sun-like sound.",
        "approx_usage": "Approx. US use: uncommon; distinctive but readable.",
        "famous_namesakes": ["Elián González"],
        "nicknames_variants": ["Eli", "Elio", "Elian"],
        "similar_names": ["Elias", "Elio", "Julian", "Lucian"],
    },
    "elio": {
        "origin_meaning": "Italian/Spanish form connected with Helios; sun.",
        "approx_usage": "Approx. US use: uncommon but rising in style awareness.",
        "famous_namesakes": ["Elio Germano", "Elio (Call Me by Your Name, fictional)"],
        "nicknames_variants": ["Helios", "Eli", "Elian"],
        "similar_names": ["Luca", "Enzo", "Matteo", "Milo"],
    },
    "elodie": {
        "origin_meaning": "French form often linked with foreign riches or wealth.",
        "approx_usage": "Approx. US use: uncommon; stylish and increasingly familiar.",
        "famous_namesakes": ["Élodie Yung", "Élodie Bouchez"],
        "nicknames_variants": ["Ellie", "Lodie", "Elodia"],
        "similar_names": ["Eloise", "Amelie", "Sylvie", "Celine"],
    },
    "eloise": {
        "origin_meaning": "French/Germanic roots; often associated with healthy, wide, or famous in battle depending on source.",
        "approx_usage": "Approx. US use: familiar and rising; historically tens of thousands of recorded births.",
        "famous_namesakes": ["Eloise Mumford", "Eloise (book character)"],
        "nicknames_variants": ["Ellie", "Lola", "Lou", "Heloise"],
        "similar_names": ["Elodie", "Louisa", "Clara", "Celia"],
    },
    "enzo": {
        "origin_meaning": "Italian short form connected with names like Lorenzo, Vincenzo, or Enrico.",
        "approx_usage": "Approx. US use: increasingly familiar; modern, compact, and international.",
        "famous_namesakes": ["Enzo Ferrari", "Enzo Francescoli"],
        "nicknames_variants": ["Lorenzo", "Vincenzo", "Enrico"],
        "similar_names": ["Luca", "Elio", "Nico", "Marco"],
    },
    "evander": {
        "origin_meaning": "Greek origin; often interpreted as good man or strong man.",
        "approx_usage": "Approx. US use: rare-to-uncommon; distinctive with classical weight.",
        "famous_namesakes": ["Evander Holyfield"],
        "nicknames_variants": ["Evan", "Van", "Evandro"],
        "similar_names": ["Leander", "Alexander", "Caspian", "Dorian"],
    },
    "fiona": {
        "origin_meaning": "Scottish literary name often linked with fair or white.",
        "approx_usage": "Approx. US use: familiar but not overused; a gentle Scottish-feeling option.",
        "famous_namesakes": ["Fiona Apple", "Fiona Shaw"],
        "nicknames_variants": ["Fee", "Fia", "Finola"],
        "similar_names": ["Flora", "Freya", "Nora", "Isla"],
    },
    "giovanni": {
        "origin_meaning": "Italian form of John; traditionally means God is gracious.",
        "approx_usage": "Approx. US use: familiar Italian classic; widely recognized but not top-tier common.",
        "famous_namesakes": ["Giovanni Boccaccio", "Giovanni Ribisi"],
        "nicknames_variants": ["Gio", "Gianni", "John", "Juan"],
        "similar_names": ["Leonardo", "Lorenzo", "Matteo", "Santino"],
    },
    "iris": {
        "origin_meaning": "Greek origin; rainbow. Also a flower name.",
        "approx_usage": "Approx. US use: familiar botanical classic; historically many tens of thousands of recorded births.",
        "famous_namesakes": ["Iris Apfel", "Iris Murdoch"],
        "nicknames_variants": ["Irisa", "Irie"],
        "similar_names": ["Ivy", "Violet", "Flora", "Cora"],
    },
    "jonah": {
        "origin_meaning": "Hebrew origin; dove.",
        "approx_usage": "Approx. US use: familiar biblical choice; widely used in recent decades.",
        "famous_namesakes": ["Jonah Hill", "Jonah Lomu"],
        "nicknames_variants": ["Jonas", "Jon", "Jo"],
        "similar_names": ["Noah", "Jude", "Elias", "Silas"],
    },
    "june": {
        "origin_meaning": "Month name tied to Juno, the Roman goddess.",
        "approx_usage": "Approx. US use: familiar vintage revival; historically many tens of thousands of recorded births.",
        "famous_namesakes": ["June Carter Cash", "June Squibb"],
        "nicknames_variants": ["Junie", "Juno"],
        "similar_names": ["Jane", "Mae", "Rose", "Pearl"],
    },
    "julian": {
        "origin_meaning": "Latin family name Julius; often linked with youthful or downy-bearded in traditional etymology.",
        "approx_usage": "Approx. US use: familiar classic; historically well over 100,000 recorded births.",
        "famous_namesakes": ["Julian Lennon", "Julian Edelman"],
        "nicknames_variants": ["Jules", "Julien", "Julius"],
        "similar_names": ["Lucian", "Adrian", "Elias", "Simon"],
    },
    "lena": {
        "origin_meaning": "Often a short form of Helena, Magdalena, or related names; meanings vary by root.",
        "approx_usage": "Approx. US use: familiar, international, and long-used.",
        "famous_namesakes": ["Lena Horne", "Lena Dunham"],
        "nicknames_variants": ["Helena", "Magdalena", "Lina"],
        "similar_names": ["Mira", "Nina", "Lila", "Maya"],
    },
    "leon": {
        "origin_meaning": "Greek/Latin-rooted; lion.",
        "approx_usage": "Approx. US use: familiar vintage classic; historically well over 100,000 recorded births.",
        "famous_namesakes": ["Leon Bridges", "Leon Trotsky"],
        "nicknames_variants": ["Leo", "León", "Leonardo"],
        "similar_names": ["Leo", "Hugo", "Otto", "Louis"],
    },
    "leonardo": {
        "origin_meaning": "Italian/Germanic roots; brave lion.",
        "approx_usage": "Approx. US use: familiar and strongly recognized; boosted by art, film, and international use.",
        "famous_namesakes": ["Leonardo da Vinci", "Leonardo DiCaprio"],
        "nicknames_variants": ["Leo", "Leon", "Nardo"],
        "similar_names": ["Lorenzo", "Giovanni", "Matteo", "Dante"],
    },
    "lorenzo": {
        "origin_meaning": "Italian/Spanish form of Laurence; traditionally linked with laurel.",
        "approx_usage": "Approx. US use: familiar international choice; recognizable without feeling ordinary.",
        "famous_namesakes": ["Lorenzo de’ Medici", "Lorenzo Cain"],
        "nicknames_variants": ["Enzo", "Renzo", "Laurence"],
        "similar_names": ["Leonardo", "Matteo", "Giovanni", "Alessio"],
    },
    "louisa": {
        "origin_meaning": "Feminine form of Louis; often linked with renowned warrior.",
        "approx_usage": "Approx. US use: familiar vintage classic; less common than Louise historically.",
        "famous_namesakes": ["Louisa May Alcott", "Louisa Jacobson"],
        "nicknames_variants": ["Lou", "Lulu", "Louise", "Luisa"],
        "similar_names": ["Eloise", "Clara", "Celia", "Beatrice"],
    },
    "luca": {
        "origin_meaning": "Italian form of Lucas/Luke; traditionally linked with Lucania or light associations.",
        "approx_usage": "Approx. US use: popular and rising; a very familiar modern international choice.",
        "famous_namesakes": ["Luca Guadagnino", "Luka Dončić (variant spelling)"],
        "nicknames_variants": ["Luka", "Lucas", "Luke"],
        "similar_names": ["Matteo", "Nico", "Enzo", "Elio"],
    },
    "maeve": {
        "origin_meaning": "Irish origin; traditionally associated with she who intoxicates or brings joy.",
        "approx_usage": "Approx. US use: increasingly familiar; stylish and rising.",
        "famous_namesakes": ["Queen Medb/Maeve of Connacht", "Maeve Binchy"],
        "nicknames_variants": ["Mae", "Meabh", "Medb"],
        "similar_names": ["Maren", "Mabel", "Nora", "Fiona"],
    },
    "marco": {
        "origin_meaning": "Italian form of Mark; traditionally linked with Mars.",
        "approx_usage": "Approx. US use: familiar Italian classic; recognizable and easy to say.",
        "famous_namesakes": ["Marco Polo", "Marco Rubio"],
        "nicknames_variants": ["Mark", "Marcus", "Marcello"],
        "similar_names": ["Matteo", "Luca", "Dante", "Enzo"],
    },
    "maren": {
        "origin_meaning": "Scandinavian/Danish form often related to Maria; meanings vary by root.",
        "approx_usage": "Approx. US use: uncommon but very wearable; a quiet distinctive choice.",
        "famous_namesakes": ["Maren Morris", "Maren Mjelde"],
        "nicknames_variants": ["Mara", "Maren", "Marin"],
        "similar_names": ["Maeve", "Mira", "Rowan", "Greta"],
    },
    "matteo": {
        "origin_meaning": "Italian form of Matthew; traditionally means gift of God.",
        "approx_usage": "Approx. US use: familiar and rising; a well-liked international choice.",
        "famous_namesakes": ["Matteo Berrettini", "Matteo Bocelli"],
        "nicknames_variants": ["Teo", "Mattia", "Matthew"],
        "similar_names": ["Luca", "Leonardo", "Lorenzo", "Santino"],
    },
    "maya": {
        "origin_meaning": "Multicultural name with Sanskrit, Hebrew, Greek, and Spanish-language associations; meanings vary by tradition.",
        "approx_usage": "Approx. US use: very familiar; widely used across recent decades.",
        "famous_namesakes": ["Maya Angelou", "Maya Rudolph"],
        "nicknames_variants": ["Maia", "Maja", "May"],
        "similar_names": ["Mira", "Lena", "Nina", "Mila"],
    },
    "miles": {
        "origin_meaning": "English/Latin-rooted name; meanings vary, often linked with soldier or gracious.",
        "approx_usage": "Approx. US use: familiar and popular; a modern classic.",
        "famous_namesakes": ["Miles Davis", "Miles Teller"],
        "nicknames_variants": ["Myles", "Milo"],
        "similar_names": ["Owen", "Julian", "Simon", "Elliot"],
    },
    "mira": {
        "origin_meaning": "Multilingual name; can be connected with wonderful, peace, ocean, or admirable depending on language.",
        "approx_usage": "Approx. US use: uncommon-to-familiar; short and international.",
        "famous_namesakes": ["Mira Nair", "Mira Sorvino"],
        "nicknames_variants": ["Meera", "Mirabel", "Mirella"],
        "similar_names": ["Maya", "Lena", "Nina", "Mila"],
    },
    "noemi": {
        "origin_meaning": "Italian/Spanish/Hungarian form related to Naomi; pleasantness.",
        "approx_usage": "Approx. US use: uncommon but recognizable; softer alternative to Naomi.",
        "famous_namesakes": ["Noemí Sanín", "Noemi (Italian singer)"],
        "nicknames_variants": ["Naomi", "Noémie", "Nomi"],
        "similar_names": ["Mira", "Elodie", "Lena", "Celia"],
    },
    "nora": {
        "origin_meaning": "Often a short form of Honora or Eleanor; meanings include honor or light depending on root.",
        "approx_usage": "Approx. US use: very familiar; historically well over 100,000 recorded births.",
        "famous_namesakes": ["Nora Ephron", "Nora Roberts"],
        "nicknames_variants": ["Norah", "Eleanora", "Honora"],
        "similar_names": ["Cora", "Clara", "Mara", "Ada"],
    },
    "owen": {
        "origin_meaning": "Welsh origin; often linked with youth, noble-born, or well-born.",
        "approx_usage": "Approx. US use: popular modern classic; widely familiar.",
        "famous_namesakes": ["Owen Wilson", "Owen Hart"],
        "nicknames_variants": ["Eoin", "Owain"],
        "similar_names": ["Miles", "Rowan", "Theo", "Jonah"],
    },
    "rocco": {
        "origin_meaning": "Italian name often linked with rest or rock, depending on etymological source.",
        "approx_usage": "Approx. US use: uncommon but recognizable; bold Italian feel.",
        "famous_namesakes": ["Saint Rocco", "Rocco Ritchie"],
        "nicknames_variants": ["Rocky", "Roc"],
        "similar_names": ["Enzo", "Dante", "Marco", "Bruno"],
    },
    "romy": {
        "origin_meaning": "Often a short form of Rosemary/Romilly or a standalone European-style name.",
        "approx_usage": "Approx. US use: rare-to-uncommon; stylish and compact.",
        "famous_namesakes": ["Romy Schneider", "Romy Madley Croft"],
        "nicknames_variants": ["Romilly", "Rosemary", "Roma"],
        "similar_names": ["Remy", "Mira", "Lena", "Nola"],
    },
    "rowan": {
        "origin_meaning": "Nature name from the rowan tree; also has Irish/Scottish surname roots.",
        "approx_usage": "Approx. US use: familiar and rising; used across genders.",
        "famous_namesakes": ["Rowan Atkinson", "Rowan Blanchard"],
        "nicknames_variants": ["Ro", "Rowen", "Rohan"],
        "similar_names": ["Owen", "Maren", "River", "Ronan"],
    },
    "santino": {
        "origin_meaning": "Italian name related to santo; little saint.",
        "approx_usage": "Approx. US use: uncommon but recognizable; warm and heritage-forward.",
        "famous_namesakes": ["Santino Fontana", "Santino Marella"],
        "nicknames_variants": ["Tino", "Santi", "Santo"],
        "similar_names": ["Matteo", "Giovanni", "Lorenzo", "Alessio"],
    },
    "silas": {
        "origin_meaning": "Biblical/Latin-Greek roots; often connected with forest or asked-for meanings depending on source.",
        "approx_usage": "Approx. US use: familiar and rising; a current old-soul favorite.",
        "famous_namesakes": ["Silas Weir Mitchell", "Silas Wright"],
        "nicknames_variants": ["Si", "Silvan", "Sylas"],
        "similar_names": ["Jonah", "Ezra", "Ansel", "Miles"],
    },
    "theo": {
        "origin_meaning": "Greek-rooted short form tied to Theodore/Theodora; gift of God.",
        "approx_usage": "Approx. US use: familiar and rising as both nickname and standalone.",
        "famous_namesakes": ["Theo James", "Theo Epstein"],
        "nicknames_variants": ["Theodore", "Theodora", "Teo"],
        "similar_names": ["Leo", "Milo", "Owen", "Finn"],
    },
    "vittorio": {
        "origin_meaning": "Italian form related to Victor; victory.",
        "approx_usage": "Approx. US use: rare; very heritage-forward and distinctive.",
        "famous_namesakes": ["Vittorio De Sica", "Vittorio Emanuele II"],
        "nicknames_variants": ["Vito", "Vittore", "Victor"],
        "similar_names": ["Lorenzo", "Giovanni", "Alessio", "Dante"],
    },
}


def build_name_fact_card(vertical_slug: str, result: Mapping[str, Any]) -> dict[str, Any] | None:
    if vertical_slug != "baby":
        return None

    name = str(result.get("name", "")).strip()
    if not name:
        return None

    key = _key(name)
    facts = BABY_NAME_FACTS.get(key, {})
    tags = [str(item) for item in result.get("tags", []) if item]
    validation = result.get("validation") or []

    origin_meaning = facts.get("origin_meaning") or _fallback_origin_meaning(result)
    pronunciation = str(result.get("pronunciation") or "").strip()
    popularity_snapshot = facts.get("approx_usage") or _fallback_popularity_snapshot(result)
    famous_namesakes = facts.get("famous_namesakes") or ["Namesake data is being expanded for this beta card."]
    nicknames_variants = facts.get("nicknames_variants") or _fallback_variants(name)
    similar_names = facts.get("similar_names") or _fallback_similar_names(name, tags)
    good_to_know = _good_to_know(name, result, validation, facts)

    return {
        "title": f"{name} name card",
        "origin_meaning": origin_meaning,
        "pronunciation": pronunciation,
        "popularity_snapshot": popularity_snapshot,
        "famous_namesakes": famous_namesakes,
        "nicknames_variants": nicknames_variants,
        "style_vibe": _style_vibe(result, tags),
        "similar_names": similar_names,
        "good_to_know": good_to_know,
        "why_it_fits": str(result.get("why_this_name") or result.get("fit_note") or ""),
        "source_note": "Beta fact card: usage figures are approximate snapshots and should be verified before publication.",
    }


def _key(name: str) -> str:
    return "".join(char for char in name.lower() if char.isalnum())


def _fallback_origin_meaning(result: Mapping[str, Any]) -> str:
    meaning = str(result.get("meaning") or "").strip()
    if meaning and not meaning.startswith("A baby name shaped"):
        return meaning
    return "Origin and meaning data is being expanded; this card currently emphasizes fit, sound, and usage context."


def _fallback_popularity_snapshot(result: Mapping[str, Any]) -> str:
    scores = result.get("scores") or {}
    popularity_score = float(scores.get("baby_popularity", scores.get("distinctiveness", 0.74)) or 0.74)
    if popularity_score <= 0.62:
        return "Approx. US use: familiar choice; likely many tens of thousands of historical recorded births."
    if popularity_score <= 0.75:
        return "Approx. US use: recognizable but not everywhere; likely thousands to tens of thousands of historical recorded births."
    return "Approx. US use: distinctive but wearable; likely lower historical use than mainstream classics."


def _fallback_variants(name: str) -> list[str]:
    if len(name) <= 4:
        return [name]
    return [name, name[:3]]


def _fallback_similar_names(name: str, tags: list[str]) -> list[str]:
    if "warm" in tags:
        return ["Mira", "Nora", "Luca"]
    if "family-ready" in tags:
        return ["Clara", "Julian", "Eloise"]
    return ["Clara", "Maren", "Theo"]


def _style_vibe(result: Mapping[str, Any], tags: list[str]) -> list[str]:
    vibes = [item.replace("-", " ").title() for item in tags[:4]]
    tagline = str(result.get("tagline") or "").lower()
    for cue in ("Classic", "Warm", "Soft", "Modern", "Elegant", "Distinctive", "International"):
        if cue.lower() in tagline and cue not in vibes:
            vibes.append(cue)
    return vibes[:5] or ["Wearable", "Warm", "Family Ready"]


def _good_to_know(
    name: str,
    result: Mapping[str, Any],
    validation: list[Any],
    facts: Mapping[str, Any],
) -> list[str]:
    notes: list[str] = []
    pronunciation = str(result.get("pronunciation") or "").strip()
    if pronunciation:
        notes.append("Has a clear pronunciation cue for sharing with family.")
    if facts.get("nicknames_variants"):
        notes.append("Has natural nickname or spelling-variant options.")
    if len(name) <= 5:
        notes.append("Short enough to pair easily with many surnames.")
    else:
        notes.append("Worth saying out loud with the surname for rhythm.")

    popularity_message = " ".join(
        str(item.get("message", "")) if isinstance(item, Mapping) else str(getattr(item, "message", ""))
        for item in validation
    ).lower()
    if "familiar" in popularity_message:
        notes.append("Familiarity may be part of its comfort and charm.")
    elif "distinctive" in popularity_message:
        notes.append("Distinctive enough to feel considered without feeling hard to use.")
    return notes[:4]
