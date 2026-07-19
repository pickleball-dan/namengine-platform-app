import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, make_session_id
from namengine.core import build_brief, generate_ai_names, save_session
from namengine.verticals import PET


STRATEGY_RESPONSE = json.dumps(
    {
        "taste_thesis": "Warm, practical dog names with a friendly rescue-story feel.",
        "priority_interpretation": "The user's written note should lead the strategy.",
        "hard_constraints": ["Avoid rejected names"],
        "soft_preferences": ["Friendly sound"],
        "anti_patterns": ["Overly elaborate names"],
        "naming_territories": [
            {"label": "warm-callable", "description": "Easy names with warmth", "example_style": "Milo", "risk": "familiar"}
        ],
        "candidate_rubric": [
            {"criterion": "callability", "weight": 0.4, "what_good_looks_like": "Easy to say aloud"}
        ],
        "diversity_plan": "Mix familiar and fresh sounds.",
    }
)

AI_RESPONSE = json.dumps(
    {
        "candidate_pool": [
            {
                "name": "Lumi",
                "territory": "warm-callable",
                "rationale": "Best fit for a gentle rescue dog with a warm sound.",
                "strengths": ["warm", "callable"],
                "risks": ["less traditional"],
                "scores": {"taste_fit": 0.93, "usability": 0.91, "distinctiveness": 0.78},
                "decision": "finalist",
            },
            {
                "name": "Sunny",
                "territory": "warm-callable",
                "rationale": "Friendly but too expected for the taste thesis.",
                "strengths": ["friendly", "easy"],
                "risks": ["too expected"],
                "scores": {"taste_fit": 0.68, "usability": 0.94, "distinctiveness": 0.4},
                "decision": "rejected",
            },
        ],
        "rejected_candidates": [
            {
                "name": "Sunny",
                "territory": "warm-callable",
                "rejection_reason": "Too expected and less distinctive than Lumi.",
                "lost_to": "Lumi",
                "score_summary": "High usability, weaker distinctiveness.",
            }
        ],
        "names": [
            {
                "name": "Lumi",
                "pronunciation": "LOO-mee",
                "tagline": "Bright, soft, and easy to call.",
                "meaning": "Suggests light and warmth.",
                "why_this_name": "Lumi wins because it matches the warm-callable thesis.",
                "fit_note": "Fits a gentle rescue dog.",
                "risks": ["Less traditional than Max."],
                "tags": ["callable", "warm"],
                "scores": {"callability": 0.92, "warmth": 0.9, "distinctiveness": 0.8},
            }
        ]
    }
)


class FakeResponse:
    output_text = ""

    def __init__(self, output_text, usage):
        self.output_text = output_text
        self.usage = usage


class FakeResponses:
    def __init__(self):
        self.calls = []
        self.responses = [
            FakeResponse(STRATEGY_RESPONSE, {"input_tokens": 100, "output_tokens": 60, "total_tokens": 160}),
            FakeResponse(AI_RESPONSE, {"input_tokens": 200, "output_tokens": 80, "total_tokens": 280}),
            FakeResponse(AI_RESPONSE, {"input_tokens": 180, "output_tokens": 90, "total_tokens": 270}),
        ]

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


class PhaseTwentyOneEngineAuditTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_engine_audit_enabled = os.environ.get("NAMENGINE_ENABLE_ENGINE_AUDIT")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")
        os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = "1"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_engine_audit_enabled is None:
            os.environ.pop("NAMENGINE_ENABLE_ENGINE_AUDIT", None)
        else:
            os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = self.previous_engine_audit_enabled
        self.tempdir.cleanup()

    def test_engine_audit_renders_pipeline_metadata(self):
        brief = build_brief(PET, {"pet_type": "Dog", "style": "Warm", "notes": "gentle rescue"})
        fake_client = FakeClient()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            names = generate_ai_names(PET, brief, 1, client_factory=lambda: fake_client)
        session_id = make_session_id("pet", b"pet_type=Dog&style=Warm&notes=gentle+rescue")
        save_session(session_id, PET.slug, brief, names)

        response = self.client.get(f"/dev/engine-audit/{session_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Engine Audit", body)
        self.assertIn("namengine-taste-engine-v1", body)
        self.assertIn("three_pass_llm_v1", body)
        self.assertIn("critic_ranker_finalizer_v1", body)
        self.assertIn("input 480", body)
        self.assertIn("input_tokens\": 200", body)
        self.assertIn("Candidate pool", body)
        self.assertIn("Rejected candidates", body)
        self.assertIn("Too expected and less distinctive", body)
        self.assertIn("Lumi", body)


if __name__ == "__main__":
    unittest.main()
