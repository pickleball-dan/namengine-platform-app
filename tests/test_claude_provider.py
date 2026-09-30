import json
import os
import unittest
from unittest.mock import patch

from namengine.core import ai_generation
from namengine.core.ai_generation import generate_ai_names
from namengine.core.briefs import build_brief
from namengine.core.schemas import ModelProvider
from namengine.verticals import PET


class _FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        stage = json.loads(kwargs["messages"][0]["content"])["engine_stage"]
        if stage == "taste_interpreter_v1":
            text = json.dumps(
                {
                    "taste_thesis": "warm coastal companion names",
                    "priority_interpretation": "prioritize warmth and callability",
                    "hard_constraints": ["avoid repeats"],
                    "soft_preferences": ["gentle sound"],
                    "anti_patterns": ["generic filler"],
                    "naming_territories": [
                        {
                            "label": "harbor warmth",
                            "description": "soft coastal names",
                            "example_style": "Marin",
                            "risk": "too nautical",
                        }
                    ],
                    "candidate_rubric": [
                        {
                            "criterion": "callability",
                            "weight": 0.5,
                            "what_good_looks_like": "easy to repeat",
                        }
                    ],
                    "diversity_plan": "mix warm and coastal sounds",
                }
            )
        elif stage == "candidate_generator_v1":
            text = json.dumps(
                {
                    "candidate_pool": [
                        {
                            "name": "Marin",
                            "pronunciation": "MAIR-in",
                            "territory": "coastal warmth",
                            "rationale": "soft and callable",
                            "strengths": ["warm", "clear"],
                            "risks": ["may feel place-based"],
                            "tags": ["warm", "coastal"],
                            "scores": {
                                "taste_fit": 0.91,
                                "usability": 0.9,
                                "distinctiveness": 0.72,
                            },
                        },
                        {
                            "name": "Bram",
                            "pronunciation": "BRAM",
                            "territory": "compact warmth",
                            "rationale": "short and strong",
                            "strengths": ["short", "clear"],
                            "risks": ["less soft"],
                            "tags": ["callable"],
                            "scores": {
                                "taste_fit": 0.87,
                                "usability": 0.91,
                                "distinctiveness": 0.68,
                            },
                        },
                    ]
                }
            )
        else:
            text = json.dumps(
                {
                    "names": [
                        {
                            "name": "Marin",
                            "pronunciation": "MAIR-in",
                            "tagline": "Warm, coastal, and easy to call.",
                            "origin": "Place-inspired",
                            "meaning": "Of the sea",
                            "why_this_name": "Marin fits the warm coastal direction with a soft call shape.",
                            "fit_note": "Best for a gentle pet with an outdoorsy feel.",
                            "matched_preferences": [
                                {
                                    "preference": "Style: Warm",
                                    "evidence": "soft ending and familiar rhythm",
                                    "fit": "feels affectionate without becoming cutesy",
                                }
                            ],
                            "risks": ["may read as place-inspired"],
                            "tags": ["warm", "callable"],
                            "scores": {
                                "callability": 0.92,
                                "warmth": 0.9,
                                "distinctiveness": 0.74,
                            },
                        },
                        {
                            "name": "Bram",
                            "pronunciation": "BRAM",
                            "tagline": "Compact, warm, and clear.",
                            "origin": "Short form",
                            "meaning": "Bramble or Abraham-rooted",
                            "why_this_name": "Bram gives the list a crisp, friendly counterpoint.",
                            "fit_note": "Best for a pet whose name should carry across a room.",
                            "matched_preferences": [
                                {
                                    "preference": "Sound: Clear",
                                    "evidence": "one strong syllable",
                                    "fit": "keeps the call simple and direct",
                                }
                            ],
                            "risks": ["less gentle than Marin"],
                            "tags": ["short", "callable"],
                            "scores": {
                                "callability": 0.94,
                                "warmth": 0.82,
                                "distinctiveness": 0.7,
                            },
                        },
                    ],
                    "rejected_candidates": [
                        {
                            "name": "Bay",
                            "territory": "coastal",
                            "rejection_reason": "too noun-like",
                            "lost_to": "Marin",
                            "score_summary": "less complete fit",
                        }
                    ],
                }
            )
        return {
            "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            "stop_reason": "end_turn",
        }


class _FakeClaudeClient:
    def __init__(self):
        self.messages = _FakeMessages()


class ClaudeProviderTest(unittest.TestCase):
    def test_claude_uses_shared_prompt_parse_validation_and_quality_pipeline(self):
        client = _FakeClaudeClient()
        brief = build_brief(
            PET,
            {
                "pet_type": "Dog",
                "vibe": "Gentle",
                "style": "Warm",
                "taste_strength_style": "90",
            },
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"}, clear=False), patch(
            "namengine.core.ai_generation.validate_results",
            wraps=ai_generation.validate_results,
        ) as validate:
            results = generate_ai_names(
                vertical=PET,
                brief=brief,
                round_number=2,
                previous_names=["Milo"],
                count=2,
                provider=ModelProvider.CLAUDE,
                client_factory=lambda: client,
            )

        self.assertEqual([result.name for result in results], ["Marin", "Bram"])
        validate.assert_called_once()
        self.assertTrue(all(result.metadata["provider"] == "claude" for result in results))
        self.assertTrue(all(result.metadata["source"] == "claude" for result in results))
        self.assertTrue(all(result.metadata["engine_pipeline"] == "three_pass_llm_v1" for result in results))
        self.assertTrue(all(result.metadata.get("quality_scores") for result in results))

        calls = client.messages.calls
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(call["model"] == "claude-sonnet-4-5-20250929" for call in calls))

        first_prompt = json.loads(calls[0]["messages"][0]["content"])
        self.assertEqual(first_prompt["vertical"], "pet")
        self.assertEqual(first_prompt["brief"]["inputs"]["pet_type"], "Dog")
        self.assertEqual(first_prompt["round_number"], 2)
        self.assertEqual(first_prompt["previous_names"], ["Milo"])

        candidate_prompt = json.loads(calls[1]["messages"][0]["content"])
        self.assertEqual(candidate_prompt["taste_strategy"]["taste_thesis"], "warm coastal companion names")
        self.assertEqual(candidate_prompt["count"], 2)

        ai_calls = results[0].metadata["ai_calls"]
        self.assertEqual([call["provider"] for call in ai_calls], ["claude", "claude", "claude"])
        self.assertEqual([call["usage"]["total_tokens"] for call in ai_calls], [30, 30, 30])

    def test_claude_requires_anthropic_api_key(self):
        brief = build_brief(PET, {"pet_type": "Dog", "style": "Warm"})

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            with self.assertRaisesRegex(Exception, "ANTHROPIC_API_KEY is not configured"):
                generate_ai_names(
                    vertical=PET,
                    brief=brief,
                    round_number=1,
                    count=1,
                    provider=ModelProvider.CLAUDE,
                    client_factory=lambda: _FakeClaudeClient(),
                )
