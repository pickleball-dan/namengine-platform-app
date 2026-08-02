import unittest

import app as platform_app
from namengine.core import build_brief
from namengine.verticals import get_vertical


class IntakeBackendLimitsTest(unittest.TestCase):
    def test_build_brief_clips_direct_posted_baby_text_fields(self):
        vertical = get_vertical("baby")
        brief = build_brief(
            vertical,
            {
                "gender": "girl",
                "style": "classic",
                "sound": "soft",
                "family_context": "F" * 1200,
                "notes": "N" * 1200,
                "partner_alignment": "P" * 900,
                "avoid": "A" * 700,
            },
        )

        self.assertEqual(len(brief.inputs["family_context"]), 1000)
        self.assertEqual(len(brief.inputs["notes"]), 1000)
        self.assertEqual(len(brief.inputs["partner_alignment"]), 750)
        self.assertEqual(len(brief.inputs["avoid"]), 500)
        self.assertEqual(len(brief.avoid[0]), 500)

    def test_build_brief_clips_direct_posted_business_text_fields(self):
        vertical = get_vertical("business")
        brief = build_brief(
            vertical,
            {
                "business_description": "B" * 1200,
                "industry": "I" * 220,
                "audience": "A" * 220,
                "style": "S" * 220,
                "avoid": "X" * 700,
            },
        )

        self.assertEqual(len(brief.inputs["business_description"]), 1000)
        self.assertEqual(len(brief.inputs["industry"]), 140)
        self.assertEqual(len(brief.inputs["audience"]), 180)
        self.assertEqual(len(brief.inputs["style"]), 180)
        self.assertEqual(len(brief.inputs["avoid"]), 500)

    def test_build_brief_clips_direct_posted_pet_text_fields_and_aliases(self):
        vertical = get_vertical("pet")
        brief = build_brief(
            vertical,
            {
                "pet_type": "dog",
                "pet_color": "C" * 220,
                "pet_breed": "B" * 220,
                "pet_details": "D" * 900,
                "vibe": "playful",
                "style": "friendly",
                "partner_alignment": "A" * 900,
            },
        )

        self.assertEqual(len(brief.inputs["pet_color"]), 120)
        self.assertEqual(len(brief.inputs["pet_breed"]), 140)
        self.assertEqual(len(brief.inputs["pet_details"]), 750)
        self.assertEqual(len(brief.inputs["avoid"]), 500)

    def test_route_sanitizer_clips_other_choices_and_drops_unknown_payload(self):
        vertical = get_vertical("baby")
        sanitized = platform_app._sanitize_intake_source(
            vertical,
            {
                "gender": "Other",
                "gender_other": "G" * 200,
                "notes": "N" * 1200,
                "unknown_big_payload": "X" * 5000,
                "taste_strength_story": "100000000000000000000",
            },
        )

        self.assertEqual(len(sanitized["gender"]), 120)
        self.assertEqual(len(sanitized["notes"]), 1000)
        self.assertEqual(sanitized["taste_strength_story"], "10000000")
        self.assertNotIn("unknown_big_payload", sanitized)


if __name__ == "__main__":
    unittest.main()
