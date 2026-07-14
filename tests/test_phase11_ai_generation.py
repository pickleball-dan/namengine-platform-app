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
    build_taste_interpreter_prompt,
    generate_ai_names,
    generate_names,
    parse_ai_generation_response,
    parse_generation_audit_response,
    parse_taste_strategy_response,
    refine_session,
    save_reaction,
)
from namengine.core.ai_generation import (
    AIGenerationError,
    NAME_GENERATION_SCHEMA_NAME,
    TASTE_STRATEGY_SCHEMA_NAME,
    name_generation_response_format,
    taste_strategy_response_format,
)
from namengine.verticals import PET


STRATEGY_RESPONSE = json.dumps(
    {
        "taste_thesis": "Warm, bright, easy-to-call pet names with a gentle but fresh feel.",
        "priority_interpretation": "Style should lead, but callability remains a hard practical filter.",
        "hard_constraints": ["Avoid names that sound like rejected examples."],
        "soft_preferences": ["Warm vowels", "Compact friendly sound"],
        "anti_patterns": ["Overly ornate invented names"],
        "naming_territories": [
            {
                "label": "bright-soft",
                "description": "Light-filled names with warmth and simplicity.",
                "example_style": "Lumi, Nori",
                "risk": "Can feel too cute if overdone.",
            }
        ],
        "candidate_rubric": [
            {
                "criterion": "callability",
                "weight": 0.35,
                "what_good_looks_like": "Clear two-syllable names that are easy to say aloud.",
            }
        ],
        "diversity_plan": "Balance bright/soft names with one crisper alternative.",
    }
)


AI_RESPONSE = json.dumps(
    {
        "candidate_pool": [
            {
                "name": "Lumi",
                "territory": "bright-soft",
                "rationale": "Best match for warm, fresh callability.",
                "strengths": ["warm", "easy to say"],
                "risks": ["less traditional"],
                "scores": {"taste_fit": 0.94, "usability": 0.9, "distinctiveness": 0.82},
                "decision": "finalist",
            },
            {
                "name": "Nova",
                "territory": "bright-soft",
                "rationale": "Bright but too common in the current pet lane.",
                "strengths": ["bright", "short"],
                "risks": ["trendier than requested"],
                "scores": {"taste_fit": 0.72, "usability": 0.88, "distinctiveness": 0.55},
                "decision": "rejected",
            },
        ],
        "rejected_candidates": [
            {
                "name": "Nova",
                "territory": "bright-soft",
                "rejection_reason": "Too trendy and less aligned with the gentle warmth thesis.",
                "lost_to": "Lumi",
                "score_summary": "Strong usability, weaker distinctiveness and taste fit.",
            }
        ],
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


class FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class FakeResponses:
    def __init__(self, output_texts):
        self.output_texts = list(output_texts)
        self.calls = []
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        self.calls.append(kwargs)
        if not self.output_texts:
            raise AssertionError("No fake AI responses left")
        return FakeResponse(self.output_texts.pop(0))


class FakeClient:
    def __init__(self, *output_texts):
        self.responses = FakeResponses(output_texts)


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

    def test_taste_interpreter_prompt_includes_user_text_and_rules(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm", "notes": "gentle rescue, not too cute"})
        prompt = build_taste_interpreter_prompt(
            vertical=PET,
            brief=brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            count=8,
        )

        self.assertEqual(prompt["engine_stage"], "taste_interpreter_v1")
        self.assertEqual(prompt["brief"]["inputs"]["notes"], "gentle rescue, not too cute")
        self.assertTrue(prompt["interpretation_rules"]["user_written_text_is_first_class_signal"])
        self.assertTrue(prompt["interpretation_rules"]["feelings_scale_changes_strategy_not_just_order"])
        self.assertIn("candidate_rubric", prompt["output_contract"]["required_fields"])

    def test_structured_output_schemas_are_strict(self):
        strategy_format = taste_strategy_response_format()
        names_format = name_generation_response_format()

        self.assertEqual(strategy_format["type"], "json_schema")
        self.assertEqual(strategy_format["name"], TASTE_STRATEGY_SCHEMA_NAME)
        self.assertTrue(strategy_format["strict"])
        self.assertFalse(strategy_format["schema"]["additionalProperties"])
        self.assertIn("taste_thesis", strategy_format["schema"]["required"])

        self.assertEqual(names_format["type"], "json_schema")
        self.assertEqual(names_format["name"], NAME_GENERATION_SCHEMA_NAME)
        self.assertTrue(names_format["strict"])
        self.assertIn("candidate_pool", names_format["schema"]["required"])
        self.assertIn("rejected_candidates", names_format["schema"]["required"])
        self.assertIn("names", names_format["schema"]["required"])
        self.assertIn("scores", names_format["schema"]["properties"]["names"]["items"]["required"])

    def test_generation_prompt_includes_brief_taste_round_goal_and_strategy(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        strategy = parse_taste_strategy_response(STRATEGY_RESPONSE)
        prompt = build_generation_prompt(
            vertical=PET,
            brief=brief,
            round_number=3,
            taste_profile=None,
            previous_names=["Milo"],
            count=6,
            taste_strategy=strategy,
        )

        self.assertEqual(prompt["round_goal"], "Finalists: produce the most choose-worthy names only.")
        self.assertEqual(prompt["brief"]["inputs"]["species"], "Dog")
        self.assertEqual(prompt["engine_stage"], "candidate_generator_ranker_v1")
        self.assertEqual(prompt["taste_strategy"]["taste_thesis"], strategy["taste_thesis"])
        self.assertEqual(prompt["previous_names"], ["Milo"])
        self.assertTrue(prompt["diversity_rules"]["do_not_repeat_previous_names"])
        self.assertTrue(prompt["diversity_rules"]["treat_previous_names_as_hard_exclusions"])
        self.assertEqual(prompt["output_contract"]["top_level_keys"], ["candidate_pool", "rejected_candidates", "names"])

    def test_parse_ai_response_dedupes_and_maps_to_name_results(self):
        results = parse_ai_generation_response(AI_RESPONSE, "pet")

        self.assertEqual([item.name for item in results], ["Lumi", "Nori"])
        self.assertEqual(results[0].id, "pet-1")
        self.assertEqual(results[0].metadata["source"], "openai")

    def test_parse_generation_audit_response_extracts_candidate_pool(self):
        audit = parse_generation_audit_response(AI_RESPONSE)

        self.assertEqual(audit["candidate_pool"][0]["name"], "Lumi")
        self.assertEqual(audit["rejected_candidates"][0]["name"], "Nova")
        self.assertIn("Too trendy", audit["rejected_candidates"][0]["rejection_reason"])

    def test_parse_ai_response_rejects_invalid_json(self):
        with self.assertRaises(AIGenerationError):
            parse_ai_generation_response("not json", "pet")

    def test_generate_ai_names_validates_ai_output(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        fake_client = FakeClient(STRATEGY_RESPONSE, AI_RESPONSE)

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
        self.assertEqual(results[0].metadata["engine_pipeline"], "taste_interpreter_v1+candidate_ranker_v1")
        self.assertEqual(results[0].metadata["candidate_pool"][0]["name"], "Lumi")
        self.assertEqual(results[0].metadata["rejected_candidates"][0]["name"], "Nova")
        self.assertEqual(len(fake_client.responses.calls), 2)
        self.assertEqual(fake_client.responses.calls[0]["timeout"], 7.0)
        self.assertEqual(fake_client.responses.calls[1]["timeout"], 7.0)
        self.assertEqual(
            fake_client.responses.calls[0]["text"]["format"]["name"],
            TASTE_STRATEGY_SCHEMA_NAME,
        )
        self.assertEqual(
            fake_client.responses.calls[1]["text"]["format"]["name"],
            NAME_GENERATION_SCHEMA_NAME,
        )
        self.assertEqual(
            results[0].metadata["ai_calls"][0]["schema_name"],
            TASTE_STRATEGY_SCHEMA_NAME,
        )

    def test_generate_names_falls_back_without_api_key(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})

        with patch.dict(os.environ, {}, clear=True):
            results = generate_names(PET, brief, use_ai=True)

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
            refine_session(session_id, PET, instruction="warmer", use_ai=True)

        self.assertEqual(mocked.call_args.kwargs["taste_profile"].summary, profile.summary)
        self.assertGreaterEqual(len(mocked.call_args.kwargs["previous_names"]), 1)

    def test_results_route_falls_back_when_router_raises(self):
        with patch("namengine.core.model_router.generate_with_router", side_effect=RuntimeError("router boom")):
            response = self.client.get("/baby/results?gender=Boy&style=Classic&sound=Soft")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("NamEngine Baby Results", body)
        self.assertIn("Baby names shaped from your taste", body)
        self.assertIn("Validation", body)

    def test_baby_results_complex_query_uses_fast_default_generation(self):
        url = (
            "/baby/results?gender=Boy&family_context=african+american"
            "&notes=strong+historical+relevance&discovery_style=Unexpected+finds"
            "&style=Classic&timeless_vs_distinctive=Strongly+distinctive"
            "&familiarity_preference=Recognizable+but+not+overused&sound=Strong"
            "&cultural_context=Family+heritage&taste_strength_about_your_baby=34"
            "&taste_strength_name_style=33&taste_strength_fit_and_feeling=33"
        )
        with patch("namengine.core.model_router.generate_with_router") as mocked_router:
            response = self.client.get(url)

        mocked_router.assert_not_called()
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("NamEngine Baby Results", body)
        self.assertIn("Baby names shaped from your taste", body)


if __name__ == "__main__":
    unittest.main()
