import unittest
from unittest.mock import patch

import app as platform_app
from app import NameGenerationUnavailable, create_app
from namengine.core.briefs import build_brief
from namengine.core.generation import generate_fallback_names
from namengine.verticals import get_vertical


class PhaseThirtyThreeAiPrimaryRouteFailsafeTest(unittest.TestCase):
    def setUp(self):
        create_app()
        self.vertical = get_vertical("baby")
        self.brief = build_brief(self.vertical, {"gender": "Girl", "style": "Playful"})

    def test_ai_primary_route_raises_clear_unavailable_error_instead_of_falling_back(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_with_router", side_effect=RuntimeError("simulated live AI failure")
        ), patch.dict("os.environ", {"NAMENGINE_AI_PRIMARY_VERTICALS": "baby"}):
            with self.assertRaises(NameGenerationUnavailable):
                platform_app._generate_names_for_route(self.vertical, self.brief)

    def test_ai_primary_route_rejects_empty_llm_response_instead_of_falling_back(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_with_router", return_value=[]
        ), patch.dict("os.environ", {"NAMENGINE_AI_PRIMARY_VERTICALS": "baby"}):
            with self.assertRaises(NameGenerationUnavailable):
                platform_app._generate_names_for_route(self.vertical, self.brief)

    def test_business_ai_primary_rejects_cached_fallback_results_instead_of_serving_them(self):
        business = get_vertical("business")
        brief = build_brief(business, {"business_description": "Founder coaching studio", "style": "Premium"})
        fallback_names = generate_fallback_names(business, brief)
        for name in fallback_names:
            name.metadata["provider"] = "fallback"
            name.metadata["source"] = "business_fallback"
            name.metadata["ai_primary_requested"] = True
            name.metadata["ai_primary_fallback"] = True

        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.dict(
            "os.environ", {"NAMENGINE_AI_PRIMARY_VERTICALS": "business"}
        ):
            self.assertFalse(platform_app._cached_names_match_current_rules(business, brief, fallback_names))

    def test_baby_ai_primary_can_still_accept_current_marked_fallback_results(self):
        fallback_names = generate_fallback_names(self.vertical, self.brief)
        for name in fallback_names:
            name.metadata["provider"] = "fallback"
            name.metadata["source"] = "baby_fallback"
            name.metadata["ai_primary_requested"] = True
            name.metadata["ai_primary_fallback"] = True

        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.dict(
            "os.environ", {"NAMENGINE_AI_PRIMARY_VERTICALS": "baby"}
        ):
            self.assertTrue(platform_app._cached_names_match_current_rules(self.vertical, self.brief, fallback_names))


if __name__ == "__main__":
    unittest.main()
