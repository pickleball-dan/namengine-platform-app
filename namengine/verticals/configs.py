"""Initial vertical contracts for the shared NamEngine platform."""

from __future__ import annotations

from namengine.core import Question, VerticalConfig


PET_DISCOVERY_STYLE_OPTIONS = (
    "Classic favorites",
    "Balanced mix",
    "Unexpected finds",
    "Completely original",
)

PET_TYPE_OPTIONS = ("Dog", "Cat", "Horse", "Bird", "Rabbit", "Reptile", "Other")
PET_GENDER_OPTIONS = ("Male", "Female", "Neutral")
PET_STYLE_OPTIONS = (
    "Classic",
    "Modern",
    "Soft and romantic",
    "Strong and tailored",
    "Uncommon but usable",
)
PET_DISTINCTIVENESS_OPTIONS = (
    "Strongly timeless",
    "Mostly timeless",
    "Balanced",
    "Mostly distinctive",
    "Strongly distinctive",
)
PET_FAMILIARITY_OPTIONS = (
    "Very familiar and easy",
    "Recognizable but not overused",
    "A little less common",
    "Memorable and rarer",
)
PET_CALLABILITY_OPTIONS = (
    "Very important",
    "Helpful but not absolute",
    "Open to slight friction",
)
PET_PERSONALITY_OPTIONS = (
    "Playful",
    "Loyal",
    "Elegant",
    "Brave",
    "Curious",
    "Gentle",
    "Mischievous",
    "Regal",
    "Adventurous",
    "Quirky",
    "Sweet",
    "Tough",
)
PET_INSPIRATION_OPTIONS = (
    "Nature",
    "Mythology",
    "Human names",
    "Food & drink",
    "Literature",
    "Movies & TV",
    "Music",
    "Geography",
    "Vintage",
    "Pop culture",
)


PET = VerticalConfig(
    slug="pet",
    display_name="Pet",
    object_label="pet name",
    route_prefix="/pet",
    intake_questions=(
        Question(
            "discovery_style",
            "Discovery style",
            choices=PET_DISCOVERY_STYLE_OPTIONS,
        ),
        Question(
            "pet_type",
            "Who's joining the family?",
            choices=PET_TYPE_OPTIONS,
        ),
        Question(
            "style",
            "What overall style feels closest?",
            choices=PET_STYLE_OPTIONS,
        ),
        Question(
            "pet_gender",
            "Gender",
            choices=PET_GENDER_OPTIONS,
        ),
        Question(
            "timeless_vs_distinctive",
            "Would you lean more timeless or more distinctive?",
            choices=PET_DISTINCTIVENESS_OPTIONS,
        ),
        Question(
            "familiarity_preference",
            "How familiar should the name feel?",
            choices=PET_FAMILIARITY_OPTIONS,
        ),
        Question(
            "pronunciation_importance",
            "How easy should it be to call?",
            choices=PET_CALLABILITY_OPTIONS,
        ),
        Question(
            "vibe",
            "What personality should the name capture?",
            choices=PET_PERSONALITY_OPTIONS,
        ),
        Question(
            "cultural_context",
            "Name inspiration",
            choices=PET_INSPIRATION_OPTIONS,
        ),
        Question(
            "partner_alignment",
            "Anything you're torn between?",
            placeholder=(
                "Cute or serious, silly or elegant, human-name or pet-name, "
                "everyone else's opinions..."
            ),
        ),
        Question(
            "notes",
            "Tell us about your pet",
            kind="textarea",
            placeholder=(
                "Breed, coloring, personality, funny quirks, names to avoid, "
                "favorite themes..."
            ),
        ),
    ),
    prompt_context=(
        "Generate pet names that are easy to call, memorable, emotionally warm, "
        "and matched to the animal's personality and household context."
    ),
    result_field_labels={
        "why_this_name": "Why this name?",
        "fit_note": "Best fit",
        "risks": "Watch-outs",
    },
    validation_modules=("pet_callability", "pet_sound_clarity"),
    theme={
        "accent": "#f2b84b",
        "surface": "#fff8ed",
        "page": "#fffaf1",
        "card": "#ffffff",
        "ink": "#18212f",
        "muted": "#607086",
    },
    assets={
        "logo": "images/pet-logo.svg",
        "share_image": "images/pet-share.svg",
    },
)


BABY = VerticalConfig(
    slug="baby",
    display_name="Baby",
    object_label="baby name",
    route_prefix="/baby",
    intake_questions=(
        Question("gender", "Any gender direction?"),
        Question("style", "What style do you naturally like?"),
        Question("family_context", "Any sibling, surname, or family context?"),
        Question("avoid", "Anything to avoid?"),
    ),
    prompt_context=(
        "Generate baby names with warmth, pronunciation clarity, cultural care, "
        "and enough explanation to help parents judge fit."
    ),
    result_field_labels={
        "pronunciation": "Pronunciation",
        "meaning": "Meaning",
        "why_this_name": "Why this name?",
        "risks": "Considerations",
    },
    validation_modules=("baby_pronunciation", "baby_initials", "baby_popularity"),
    theme={
        "accent": "#6ea8fe",
        "surface": "#f3f8ff",
        "page": "#f7fbff",
        "card": "#ffffff",
        "ink": "#172033",
        "muted": "#62708a",
    },
    assets={
        "logo": "images/baby-logo.svg",
        "share_image": "images/baby-share.svg",
    },
)


BUSINESS = VerticalConfig(
    slug="business",
    display_name="Business",
    object_label="business name",
    route_prefix="/business",
    intake_questions=(
        Question("business_description", "What does the business do?", required=True),
        Question("audience", "Who is it for?"),
        Question("industry", "What industry or category is it in?"),
        Question("style", "What should the name signal?"),
        Question("avoid", "Anything to avoid?"),
    ),
    prompt_context=(
        "Generate business names that balance brandability, category fit, "
        "pronunciation, memorability, and practical launch risk."
    ),
    result_field_labels={
        "tagline": "Positioning hint",
        "why_this_name": "Why this name?",
        "fit_note": "Brand fit",
        "risks": "Launch risks",
    },
    validation_modules=("business_domain", "business_category_fit", "business_similarity"),
    theme={
        "accent": "#d9a441",
        "surface": "#f7f9fc",
        "page": "#f5f7fb",
        "card": "#ffffff",
        "ink": "#162033",
        "muted": "#5d687c",
    },
    assets={
        "logo": "images/business-logo.svg",
        "share_image": "images/business-share.svg",
    },
)


CHARACTER = VerticalConfig(
    slug="character",
    display_name="Character",
    object_label="character name",
    route_prefix="/character",
    intake_questions=(
        Question("genre", "What genre or world is this for?", required=True),
        Question("role", "Who is the character?"),
        Question("tone", "What should the name feel like?"),
        Question("avoid", "Anything to avoid?"),
    ),
    prompt_context=(
        "Generate character names with genre fit, memorability, era/world "
        "consistency, and a clear sense of story role."
    ),
    result_field_labels={
        "why_this_name": "Why this name?",
        "fit_note": "Story fit",
        "risks": "Continuity risks",
    },
    validation_modules=("character_genre_fit", "character_era_fit"),
    theme={
        "accent": "#9a7cff",
        "surface": "#f7f3ff",
        "page": "#fbf8ff",
        "card": "#ffffff",
        "ink": "#1f1830",
        "muted": "#6c6380",
    },
    assets={
        "logo": "images/character-logo.svg",
        "share_image": "images/character-share.svg",
    },
)


VERTICALS = {
    PET.slug: PET,
    BABY.slug: BABY,
    BUSINESS.slug: BUSINESS,
    CHARACTER.slug: CHARACTER,
}


def get_vertical(slug: str) -> VerticalConfig:
    return VERTICALS[slug]
