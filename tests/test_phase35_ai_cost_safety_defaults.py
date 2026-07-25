import os
import unittest
from unittest.mock import patch

import app as platform_app
from app import create_app
from namengine.verticals import get_vertical


class PhaseThirtyFiveAiCostSafetyDefaultsTest(unittest.TestCase):
    def setUp(self):
        create_app()
        self.previous_ai_verticals = os.environ.get("NAMENGINE_AI_PRIMARY_VERTICALS")
        os.environ.pop("NAMENGINE_AI_PRIMARY_VERTICALS", None)

    def tearDown(self):
        if self.previous_ai_verticals is None:
            os.environ.pop("NAMENGINE_AI_PRIMARY_VERTICALS", None)
        else:
            os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = self.previous_ai_verticals

    def test_baby_and_pet_default_to_ai_primary_when_openai_is_configured(self):
        baby = get_vertical("baby")
        pet = get_vertical("pet")
        business = get_vertical("business")
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True):
            self.assertTrue(platform_app._should_use_ai_for_vertical(baby))
            self.assertTrue(platform_app._should_use_ai_for_vertical(pet))
            self.assertFalse(platform_app._should_use_ai_for_vertical(business))

    def test_ai_primary_env_override_can_narrow_vertical_opt_in(self):
        baby = get_vertical("baby")
        pet = get_vertical("pet")
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "baby"
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True):
            self.assertTrue(platform_app._should_use_ai_for_vertical(baby))
            self.assertFalse(platform_app._should_use_ai_for_vertical(pet))


if __name__ == "__main__":
    unittest.main()
