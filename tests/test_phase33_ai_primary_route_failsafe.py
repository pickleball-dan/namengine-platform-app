import unittest
from unittest.mock import patch

import app as platform_app
from app import create_app
from namengine.core.schemas import NameResult
from namengine.verticals import get_vertical
from namengine.core.briefs import build_brief


class PhaseThirtyThreeAiPrimaryRouteFailsafeTest(unittest.TestCase):
    def setUp(self):
        create_app()
        self.vertical = get_vertical("baby")
        self.brief = build_brief(self.vertical, {"gender": "Girl", "style": "Playful"})

    def test_route_generation_falls_back_if_ai_primary_raises_unexpected_error(self):
        fallback = [
            NameResult(
                id="baby-1",
                name="Clara",
                slug="clara",
                metadata={"source": "baby_fallback", "provider": "fallback"},
            )
        ]

        def fake_generate(vertical, brief, use_ai=False):
            if use_ai:
                raise RuntimeError("simulated live AI failure")
            return fallback

        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_names", side_effect=fake_generate
        ):
            names = platform_app._generate_names_for_route(self.vertical, self.brief)

        self.assertEqual([name.name for name in names], ["Clara"])
        self.assertTrue(names[0].metadata["route_generation_fallback"])
        self.assertEqual(names[0].metadata["route_generation_fallback_reason"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
