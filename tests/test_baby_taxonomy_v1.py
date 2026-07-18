import unittest

from namengine.core.baby_intake_adapter import (
    BABY_INTAKE_SCHEMA,
    BABY_INTAKE_VERSION,
    BABY_LEGACY_INTAKE_VERSION,
)
from namengine.core.intake_migrations import migrate_intake
from namengine.verticals.baby_taxonomy import BABY_TAXONOMY, BABY_TAXONOMY_VERSION
from namengine.verticals.configs import (
    BABY,
    BABY_CULTURAL_HERITAGE_OPTIONS,
    BABY_DISCOVERY_STYLE_OPTIONS,
    BABY_DISTINCTIVENESS_OPTIONS,
    BABY_FAMILIARITY_OPTIONS,
    BABY_GENDER_OPTIONS,
    BABY_INSPIRATION_OPTIONS,
    BABY_SOUND_OPTIONS,
    BABY_STYLE_OPTIONS,
)


CURRENT_CHOICES = {
    "gender": ("Girl", "Boy", "Gender-neutral", "Surprise me"),
    "cultural_heritage": (
        "No preference",
        "African",
        "African American",
        "Arab / Middle Eastern",
        "Armenian",
        "Australian",
        "Brazilian",
        "Chinese",
        "Danish",
        "Dutch",
        "English",
        "Filipino",
        "French",
        "German",
        "Greek",
        "Indian",
        "Irish",
        "Italian",
        "Japanese",
        "Jewish",
        "Korean",
        "Mexican",
        "Native American / Indigenous",
        "Norwegian",
        "Persian / Iranian",
        "Polish",
        "Portuguese",
        "Russian",
        "Scottish",
        "Spanish",
        "Swedish",
        "Turkish",
        "Ukrainian",
        "Vietnamese",
        "Welsh",
        "International / blended",
        "Something else — I’ll describe it",
    ),
    "discovery_style": (
        "Classic favorites",
        "Balanced mix",
        "Unexpected finds",
        "Rare but wearable",
    ),
    "style": (
        "Classic",
        "Modern",
        "Soft and romantic",
        "Strong and tailored",
        "Vintage revival",
        "Nature-inspired",
        "Globally familiar",
    ),
    "timeless_vs_distinctive": (
        "Strongly timeless",
        "Mostly timeless",
        "Balanced",
        "Mostly distinctive",
        "Strongly distinctive",
    ),
    "familiarity_preference": (
        "Very familiar and easy",
        "Recognizable but not overused",
        "A little less common",
        "Memorable and rarer",
    ),
    "sound": ("Soft", "Bright", "Strong", "Elegant", "Playful", "Calm", "Warm"),
    "cultural_context": (
        "Family heritage",
        "Nature",
        "Literature",
        "Saints & classics",
        "Music",
        "Places",
        "Meaning first",
        "Modern favorites",
    ),
}

LEGACY_CHOICES = {
    "discovery_style": ("Familiar favorites",),
    "style": ("Elegant",),
    "familiarity_preference": ("Very familiar",),
    "sound": ("Clear", "Crisp"),
    "cultural_context": ("Global inspiration", "Honor names"),
}

DEPRECATED_FIELD_ALIASES = {
    "baby_gender": "gender",
    "sex": "gender",
    "family": "family_context",
    "heritage": "cultural_heritage",
    "discovery": "discovery_style",
    "name_style": "style",
    "distinctiveness": "timeless_vs_distinctive",
    "familiarity": "familiarity_preference",
    "sound_preference": "sound",
    "avoidances": "avoid",
}

LEGACY_MIGRATION_ALIASES = {
    "baby_gender": "gender",
    "sex": "gender",
    "heritage": "cultural_heritage",
    "name_style": "style",
    "distinctiveness": "timeless_vs_distinctive",
    "familiarity": "familiarity_preference",
    "sound_preference": "sound",
}

CONFIG_CHOICE_EXPORTS = {
    "gender": BABY_GENDER_OPTIONS,
    "cultural_heritage": BABY_CULTURAL_HERITAGE_OPTIONS,
    "discovery_style": BABY_DISCOVERY_STYLE_OPTIONS,
    "style": BABY_STYLE_OPTIONS,
    "timeless_vs_distinctive": BABY_DISTINCTIVENESS_OPTIONS,
    "familiarity_preference": BABY_FAMILIARITY_OPTIONS,
    "sound": BABY_SOUND_OPTIONS,
    "cultural_context": BABY_INSPIRATION_OPTIONS,
}


class BabyTaxonomyV1Test(unittest.TestCase):
    def test_taxonomy_reproduces_every_current_baby_intake_choice(self):
        self.assertEqual("baby-taxonomy-v1", BABY_TAXONOMY_VERSION)
        self.assertEqual(BABY_TAXONOMY_VERSION, BABY_TAXONOMY.version)

        questions = {question.id: question for question in BABY.intake_questions}
        self.assertEqual(
            set(CURRENT_CHOICES),
            {question.id for question in BABY.intake_questions if question.choices},
        )
        for field_id, expected in CURRENT_CHOICES.items():
            with self.subTest(field_id=field_id):
                self.assertEqual(expected, BABY_TAXONOMY.current_choices(field_id))
                self.assertEqual(expected, CONFIG_CHOICE_EXPORTS[field_id])
                self.assertEqual(expected, questions[field_id].choices)

    def test_intake_schema_accepts_taxonomy_current_and_legacy_choices(self):
        definitions = {field.name: field for field in BABY_INTAKE_SCHEMA.fields}
        for field_id, current in CURRENT_CHOICES.items():
            with self.subTest(field_id=field_id):
                expected = current + LEGACY_CHOICES.get(field_id, ())
                self.assertEqual(expected, BABY_TAXONOMY.accepted_choices(field_id))
                self.assertEqual(expected, definitions[field_id].allowed_values)

    def test_taxonomy_resolves_every_existing_deprecated_field_alias(self):
        definitions = {field.name: field for field in BABY_INTAKE_SCHEMA.fields}
        for alias, field_id in DEPRECATED_FIELD_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertEqual(field_id, BABY_TAXONOMY.resolve_field_id(alias))
                self.assertIn(alias, definitions[field_id].deprecated_aliases)

    def test_taxonomy_resolves_legacy_choice_labels_without_rewording_them(self):
        for field_id, choices in LEGACY_CHOICES.items():
            for choice in choices:
                with self.subTest(field_id=field_id, choice=choice):
                    self.assertEqual(choice, BABY_TAXONOMY.resolve_choice(field_id, choice))
                    self.assertEqual(
                        choice,
                        BABY_TAXONOMY.resolve_choice(field_id, f"  {choice.swapcase()}  "),
                    )
        self.assertEqual("Elegant", BABY_TAXONOMY.resolve_choice("name_style", "elegant"))
        self.assertIsNone(BABY_TAXONOMY.resolve_choice("style", "Not a Baby style"))

    def test_registered_legacy_migration_uses_taxonomy_alias_mapping(self):
        self.assertEqual(
            LEGACY_MIGRATION_ALIASES,
            BABY_TAXONOMY.legacy_migration_mapping(),
        )
        payload = {
            "baby_gender": "Girl",
            "heritage": "Irish",
            "name_style": "Elegant",
            "distinctiveness": "Mostly timeless",
            "familiarity": "Very familiar",
            "sound_preference": "Clear",
        }

        migrated = migrate_intake(
            "baby",
            payload,
            BABY_LEGACY_INTAKE_VERSION,
            BABY_INTAKE_VERSION,
        )

        self.assertEqual(
            {
                "gender": "Girl",
                "cultural_heritage": "Irish",
                "style": "Elegant",
                "timeless_vs_distinctive": "Mostly timeless",
                "familiarity_preference": "Very familiar",
                "sound": "Clear",
            },
            migrated.payload,
        )


if __name__ == "__main__":
    unittest.main()
