import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, make_session_id
from namengine.core import (
    build_brief,
    build_generation_prompt,
    build_reaction,
    build_taste_profile,
    generate_ai_names,
    generate_names,
    parse_ai_generation_response,
    refine_session,
    save_reaction,
)
from namengine.core.ai_generation import AIGenerationError
from namengine.verticals import PET


AI_RESPONSE = json.dumps(
    {
        "names": [
            {
                "name": "Lumi",
                "pronunciation": "LOO-mee",
                "tagline": "Bright, soft, and easy to call.",
                "meaning": "Suggests light and warmth.",
                "why_this_name": "Lumi fits a gentle dog while feeling fresh.",
                "fit_note": "Best for a warm, affectionate pet.",
                "risks": ["Less traditional than Max or Bella."],
                "tags": ["callable", "warm", "fresh"],
                "scores": {
                    "callability": 0.92,
                    "warmth": 0.9,
                    "distinctiveness": 0.82,
                },
            },
            {
                "name": "Lumi",
                "pronunciation": "LOO-mee",
            },
            {
                "name": "Nori",
                "pronunciation": "NOR-ee",
                "tagline": "Small, crisp, and memorable.",
                "meaning": "Compact sound with friendly energy.",
                "why_this_name": "Nori gives the list a sharper option.",
                "fit_note": "Best for a playful pet.",
                "risks": [],
                "tags": ["callable", "crisp"],
                "scores": {"callability": 0.94},
            },
        ]
    }
)


class FakeResponses:
    def __init__(self, output_text):
        self.output_text = output_text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self


class FakeClient:
    def __init__(self, output_text):
        self.responses = FakeResponses(output_text)


class PhaseElevenAIGenerationTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def test_prompt_includes_brief_taste_and_round_goal(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        prompt = build_generation_prompt(
            vertical=PET,
            brief=brief,
            round_number=3,
            taste_profile=None,
            previous_names=["Milo"],
            count=6,
        )

        self.assertEqual(prompt["round_goal"], "Finalists: produce the most choose-worthy names only.")
        self.assertEqual(prompt["brief"]["inputs"]["species"], "Dog")
        self.assertEqual(prompt["previous_names"], ["Milo"])
        self.assertEqual(prompt["output_contract"]["top_level_key"], "names")

    def test_parse_ai_response_dedupes_and_maps_to_name_results(self):
        results = parse_ai_generation_response(AI_RESPONSE, "pet")

        self.assertEqual([item.name for item in results], ["Lumi", "Nori"])
        self.assertEqual(results[0].id, "pet-1")
        self.assertEqual(results[0].metadata["source"], "openai")

    def test_parse_ai_response_rejects_invalid_json(self):
        with self.assertRaises(AIGenerationError):
            parse_ai_generation_response("not json", "pet")

    def test_generate_ai_names_validates_ai_output(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        fake_client = FakeClient(AI_RESPONSE)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "NAMENGINE_OPENAI_TIMEOUT_SECONDS": "7"}):
            results = generate_ai_names(
                PET,
                brief,
                round_number=1,
                client_factory=lambda: fake_client,
            )

        self.assertEqual(results[0].name, "Lumi")
        self.assertEqual(len(results[0].validation), 2)
        self.assertIn("pet_callability", results[0].scores)
        self.assertEqual(fake_client.responses.last_kwargs["timeout"], 7.0)

    def test_generate_names_falls_back_without_api_key(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})

        with patch.dict(os.environ, {}, clear=True):
            results = generate_names(PET, brief)

        self.assertEqual(results[0].metadata["provider"], "fallback")
        self.assertIn("Milo", [item.name for item in results])

    def test_refinement_passes_taste_profile_to_ai_layer(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        profile = build_taste_profile(session_id)

        with patch("namengine.core.model_router.generate_ai_names") as mocked:
            mocked.side_effect = AIGenerationError("skip live call")
            refine_session(session_id, PET, instruction="warmer")

        self.assertEqual(mocked.call_args.kwargs["taste_profile"].summary, profile.summary)
        self.assertIn("Milo", mocked.call_args.kwargs["previous_names"])


if __name__ == "__main__":
    unittest.main()
