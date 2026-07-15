import unittest
from unittest.mock import patch

import app as platform_app
from app import NameGenerationUnavailable, create_app
from namengine.core.briefs import build_brief
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


if __name__ == "__main__":
    unittest.main()
