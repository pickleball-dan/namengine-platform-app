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
PET_LIFE_STAGE_OPTIONS = ("Young", "Mature")
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

BABY_GENDER_OPTIONS = ("Girl", "Boy", "Gender-neutral", "Surprise me")
BABY_DISCOVERY_STYLE_OPTIONS = (
    "Classic favorites",
    "Balanced mix",
    "Unexpected finds",
    "Rare but wearable",
)
BABY_STYLE_OPTIONS = (
    "Classic",
    "Modern",
    "Soft and romantic",
    "Strong and tailored",
    "Vintage revival",
    "Nature-inspired",
    "Globally familiar",
)
BABY_DISTINCTIVENESS_OPTIONS = (
    "Strongly timeless",
    "Mostly timeless",
    "Balanced",
    "Mostly distinctive",
    "Strongly distinctive",
)
BABY_FAMILIARITY_OPTIONS = (
    "Very familiar and easy",
    "Recognizable but not overused",
    "A little less common",
    "Memorable and rarer",
)
BABY_SOUND_OPTIONS = (
    "Soft",
    "Bright",
    "Strong",
    "Elegant",
    "Playful",
    "Calm",
    "Warm",
)
BABY_INSPIRATION_OPTIONS = (
    "Family heritage",
    "Nature",
    "Literature",
    "Saints & classics",
    "Music",
    "Places",
    "Meaning first",
    "Modern favorites",
)


PET = VerticalConfig(
    slug="pet",
    display_name="Pet",
    object_label="pet name",
    route_prefix="/pet",
    intake_questions=(
        Question(
            "pet_type",
            "Who's joining the family?",
            required=True,
            choices=PET_TYPE_OPTIONS,
            section="About your pet",
        ),
        Question(
            "pet_gender",
            "Gender",
            choices=PET_GENDER_OPTIONS,
            section="About your pet",
        ),
        Question(
            "pet_breed",
            "Breed",
            placeholder="Golden retriever, tabby, mixed breed...",
            section="About your pet",
        ),
        Question(
            "pet_color",
            "Color",
            placeholder="Honey, black and white, brindle...",
            section="About your pet",
        ),
        Question(
            "pet_life_stage",
            "Young or mature?",
            choices=PET_LIFE_STAGE_OPTIONS,
            section="About your pet",
        ),
        Question(
            "notes",
            "Tell us about your pet",
            kind="textarea",
            placeholder=(
                "Personality, funny quirks, names to avoid, favorite themes..."
            ),
            section="About your pet",
        ),
        Question(
            "discovery_style",
            "How adventurous should we be?",
            choices=PET_DISCOVERY_STYLE_OPTIONS,
            help_text="Choose the lane for this first pass.",
            section="Name style",
        ),
        Question(
            "style",
            "What overall style feels closest?",
            required=True,
            choices=PET_STYLE_OPTIONS,
            section="Name style",
        ),
        Question(
            "timeless_vs_distinctive",
            "Would you lean more timeless or more distinctive?",
            choices=PET_DISTINCTIVENESS_OPTIONS,
            section="Name style",
        ),
        Question(
            "familiarity_preference",
            "How familiar should the name feel?",
            choices=PET_FAMILIARITY_OPTIONS,
            section="Name style",
        ),
        Question(
            "pronunciation_importance",
            "How easy should it be to call?",
            choices=PET_CALLABILITY_OPTIONS,
            section="Fit and feeling",
        ),
        Question(
            "vibe",
            "What personality should the name capture?",
            required=True,
            choices=PET_PERSONALITY_OPTIONS,
            section="Fit and feeling",
        ),
        Question(
            "cultural_context",
            "Name inspiration",
            choices=PET_INSPIRATION_OPTIONS,
            section="Fit and feeling",
        ),
        Question(
            "partner_alignment",
            "Anything you're torn between?",
            kind="textarea",
            placeholder=(
                "Cute or serious, silly or elegant, human-name or pet-name, "
                "everyone else's opinions..."
            ),
            section="Fit and feeling",
        ),
    ),
    prompt_context=(
        "Generate pet names that are easy to call, memorable, emotionally warm, "
        "and matched to the animal's personality and household context."
    ),
    result_field_labels={
        "why_this_name": "Why this name?",
        "fit_note": "Best fit",
        "risks": "Worth noting",
    },
    validation_modules=("pet_callability", "pet_sound_clarity"),
    theme={
        "accent": "#2f9486",
        "accent_deep": "#26364d",
        "accent_pet": "#fcba76",
        "accent_soft": "rgba(47, 148, 134, 0.14)",
        "accent_warm_soft": "rgba(252, 186, 118, 0.26)",
        "surface": "rgba(255, 252, 247, 0.95)",
        "page": "#fff1df",
        "card": "#fffcf7",
        "ink": "#1f2430",
        "muted": "#656b75",
        "line": "rgba(69, 48, 34, 0.11)",
    },
    assets={
        "logo": "images/pet/namengine-pet-logo-transparent.png",
        "share_image": "images/pet/namengine-pet-card-share-v3.jpg",
    },
)


BABY = VerticalConfig(
    slug="baby",
    display_name="Baby",
    object_label="baby name",
    route_prefix="/baby",
    intake_questions=(
        Question(
            "gender",
            "Any gender direction?",
            required=True,
            choices=BABY_GENDER_OPTIONS,
            section="About your baby",
        ),
        Question(
            "family_context",
            "Sibling, surname, or family context",
            placeholder="Last name, sibling names, family names, initials...",
            section="About your baby",
        ),
        Question(
            "notes",
            "Tell us what matters",
            kind="textarea",
            placeholder="Meanings you love, family dynamics, cultural notes, names already on your list...",
            section="About your baby",
        ),
        Question(
            "discovery_style",
            "How adventurous should we be?",
            choices=BABY_DISCOVERY_STYLE_OPTIONS,
            help_text="Choose the lane for this first pass.",
            section="Name style",
        ),
        Question(
            "style",
            "What style do you naturally like?",
            required=True,
            choices=BABY_STYLE_OPTIONS,
            section="Name style",
        ),
        Question(
            "timeless_vs_distinctive",
            "Would you lean more timeless or more distinctive?",
            choices=BABY_DISTINCTIVENESS_OPTIONS,
            section="Name style",
        ),
        Question(
            "familiarity_preference",
            "How familiar should the name feel?",
            choices=BABY_FAMILIARITY_OPTIONS,
            section="Name style",
        ),
        Question(
            "sound",
            "What sound should the name have?",
            required=True,
            choices=BABY_SOUND_OPTIONS,
            section="Fit and feeling",
        ),
        Question(
            "cultural_context",
            "Name inspiration",
            choices=BABY_INSPIRATION_OPTIONS,
            section="Fit and feeling",
        ),
        Question(
            "partner_alignment",
            "Anything you're torn between?",
            kind="textarea",
            placeholder="One parent likes classic, one likes modern; honoring family without copying exactly...",
            section="Fit and feeling",
        ),
        Question(
            "avoid",
            "Anything to avoid?",
            placeholder="Names, initials, sounds, popularity levels, associations...",
            section="Fit and feeling",
        ),
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
        "accent": "#7d95c7",
        "accent_deep": "#29344f",
        "accent_pet": "#f0b8c8",
        "accent_soft": "rgba(125, 149, 199, 0.15)",
        "accent_warm_soft": "rgba(240, 184, 200, 0.25)",
        "surface": "rgba(249, 251, 255, 0.96)",
        "page": "#f7fbff",
        "card": "#ffffff",
        "ink": "#172033",
        "muted": "#62708a",
        "line": "rgba(41, 52, 79, 0.13)",
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
