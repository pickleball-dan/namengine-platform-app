import unittest

from namengine.core import (
    NamingBrief,
    NameResult,
    Reaction,
    ReactionValue,
    ValidationResult,
    ValidationStatus,
)
from namengine.core.schemas import to_plain_data
from namengine.verticals import VERTICALS


class PhaseOneContractTest(unittest.TestCase):
    def test_vertical_slugs_are_unique_and_route_ready(self):
        self.assertEqual(set(VERTICALS), {"baby", "business", "character", "pet", "product"})
        for slug, config in VERTICALS.items():
            self.assertEqual(config.slug, slug)
            self.assertTrue(config.route_prefix.startswith("/"))
            self.assertGreaterEqual(len(config.intake_questions), 4)

    def test_reactions_are_the_shared_three_choice_contract(self):
        self.assertEqual(
            {item.value for item in ReactionValue},
            {"love", "maybe", "no"},
        )

    def test_name_result_carries_validation_metadata(self):
        result = NameResult(
            id="pet-1",
            name="Mochi",
            slug="mochi",
            why_this_name="Soft, friendly, and easy to call.",
            validation=[
                ValidationResult(
                    module="pet_callability",
                    status=ValidationStatus.PASS,
                    label="Callability",
                    message="Two clear syllables.",
                    score=0.92,
                )
            ],
        )

        data = to_plain_data(result)

        self.assertEqual(data["validation"][0]["status"], "pass")
        self.assertEqual(data["validation"][0]["module"], "pet_callability")

    def test_brief_reaction_payload_is_json_friendly(self):
        brief = NamingBrief(
            vertical="pet",
            inputs={"species": "dog", "style": "warm but not too cute"},
            avoid=["human names"],
        )
        reaction = Reaction(
            session_id="session-1",
            result_id="pet-1",
            value=ReactionValue.LOVE,
        )

        self.assertEqual(to_plain_data(brief)["vertical"], "pet")
        self.assertEqual(to_plain_data(reaction)["value"], "love")


if __name__ == "__main__":
    unittest.main()

