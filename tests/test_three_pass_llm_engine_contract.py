import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from namengine.core.ai_generation import generate_ai_names
from namengine.core.briefs import build_brief
from namengine.verticals import PET


class FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class ThreePassResponses:
    def __init__(self):
        self.calls = []
        self.active_style = ""
        self.active_candidate = ""

    def create(self, **kwargs):
        self.calls.append(kwargs)
        prompt = json.loads(kwargs["input"][1]["content"])
        stage = prompt["engine_stage"]
        if stage == "taste_interpreter_v1":
            self.active_style = prompt["brief"]["inputs"].get("style", "")
            thesis = "warm moonlit comfort" if self.active_style == "Warm" else "bold kinetic spark"
            return FakeResponse(
                json.dumps(
                    {
                        "taste_thesis": thesis,
                        "priority_interpretation": f"Lead with {thesis}.",
                        "hard_constraints": ["Avoid repeats."],
                        "soft_preferences": [self.active_style],
                        "anti_patterns": ["generic filler"],
                        "naming_territories": [
                            {
                                "label": "primary",
                                "description": thesis,
                                "example_style": "Lumi" if self.active_style == "Warm" else "Zuri",
                                "risk": "Can over-index on one lane.",
                            }
                        ],
                        "candidate_rubric": [
                            {
                                "criterion": "taste fit",
                                "weight": 0.7,
                                "what_good_looks_like": thesis,
                            }
                        ],
                        "diversity_plan": "Keep a varied but thesis-led pool.",
                    }
                )
            )
        if stage == "candidate_generator_v1":
            thesis = prompt["taste_strategy"]["taste_thesis"]
            assert ("warm moonlit comfort" in thesis) or ("bold kinetic spark" in thesis)
            self.active_candidate = "Lumi" if "warm" in thesis else "Zuri"
            return FakeResponse(
                json.dumps(
                    {
                        "candidate_pool": [
                            {
                                "name": self.active_candidate,
                                "pronunciation": self.active_candidate,
                                "territory": "primary",
                                "rationale": f"Matches {thesis}.",
                                "strengths": ["taste-fit"],
                                "risks": ["subjective fit"],
                                "tags": ["llm-created"],
                                "scores": {"taste_fit": 0.95, "usability": 0.9, "distinctiveness": 0.8},
                            }
                        ]
                    }
                )
            )
        if stage == "critic_ranker_finalizer_v1":
            assert prompt["candidate_pool"][0]["name"] == self.active_candidate
            name = self.active_candidate
            return FakeResponse(
                json.dumps(
                    {
                        "names": [
                            {
                                "name": name,
                                "pronunciation": name,
                                "tagline": "Chosen by the three-pass engine.",
                                "origin": "LLM candidate pool",
                                "meaning": "Taste-shaped finalist.",
                                "why_this_name": "It best matched the interpreted taste thesis.",
                                "fit_note": "The finalizer selected it from the generated pool.",
                                "risks": ["Review personally."],
                                "tags": ["three-pass"],
                                "scores": {"callability": 0.9, "warmth": 0.86, "distinctiveness": 0.82},
                            }
                        ],
                        "rejected_candidates": [],
                    }
                )
            )
        raise AssertionError(f"Unexpected stage {stage}")


class ThreePassClient:
    def __init__(self):
        self.responses = ThreePassResponses()


class ThreePassLlmEngineContractTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = str(Path(self.tempdir.name) / "namengine.sqlite3")
        create_app()

    def tearDown(self):
        self.tempdir.cleanup()
        if self.previous_db is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db

    def test_three_pass_engine_chains_taste_pool_and_finalizer(self):
        client = ThreePassClient()
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            names = generate_ai_names(PET, brief, round_number=1, count=1, client_factory=lambda: client)

        self.assertEqual([call["input"][1]["content"] for call in client.responses.calls].__len__(), 3)
        self.assertEqual([json.loads(call["input"][1]["content"])["engine_stage"] for call in client.responses.calls], [
            "taste_interpreter_v1",
            "candidate_generator_v1",
            "critic_ranker_finalizer_v1",
        ])
        self.assertEqual(names[0].name, "Lumi")
        self.assertEqual(names[0].metadata["engine_pipeline"], "three_pass_llm_v1")
        self.assertEqual(names[0].metadata["source"], "openai")
        self.assertNotEqual(names[0].metadata.get("provider"), "fallback")
        self.assertEqual(names[0].metadata["candidate_pool"][0]["name"], "Lumi")

    def test_taste_input_materially_changes_final_output(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            warm = generate_ai_names(
                PET,
                build_brief(PET, {"species": "Dog", "style": "Warm"}),
                round_number=1,
                count=1,
                client_factory=lambda: ThreePassClient(),
            )
            bold = generate_ai_names(
                PET,
                build_brief(PET, {"species": "Dog", "style": "Bold"}),
                round_number=1,
                count=1,
                client_factory=lambda: ThreePassClient(),
            )

        self.assertEqual(warm[0].name, "Lumi")
        self.assertEqual(bold[0].name, "Zuri")
        self.assertNotEqual(warm[0].name, bold[0].name)


if __name__ == "__main__":
    unittest.main()
