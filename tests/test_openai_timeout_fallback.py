import unittest
from unittest.mock import patch

import httpx
from openai import APITimeoutError

import app as platform_app
import namengine.core.model_router as model_router
from app import NameGenerationUnavailable, create_app
from namengine.core.ai_generation import AIGenerationError, _default_client, _openai_timeout_seconds
from namengine.core.briefs import build_brief
from namengine.core.schemas import ModelProvider
from namengine.verticals import get_vertical


def _openai_timeout(*args, **kwargs):
    try:
        raise APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    except APITimeoutError as exc:
        raise AIGenerationError("request timed out") from exc


def _openai_incomplete(*args, **kwargs):
    raise AIGenerationError(
        "OpenAI response incomplete stage=critic_ranker_finalizer_v1 model=gpt-4.1-mini "
        "status=incomplete reason=max_output_tokens output_json_chars=12102"
    )


class OpenAITimeoutFallbackTest(unittest.TestCase):
    def setUp(self):
        create_app()
        self.vertical = get_vertical("baby")
        self.brief = build_brief(
            self.vertical,
            {"gender": "Girl", "style": "Playful", "sound": "Soft and flowing"},
        )

    def test_production_timeout_allows_three_pass_quality_generation_and_sdk_retries_are_disabled(self):
        with patch.dict("os.environ", {"NAMENGINE_OPENAI_TIMEOUT_SECONDS": "8"}), patch(
            "openai.OpenAI"
        ) as client_factory:
            _default_client()
            timeout_seconds = _openai_timeout_seconds()

        self.assertEqual(timeout_seconds, 60.0)
        client_factory.assert_called_once_with(max_retries=0)

    def test_openai_timeout_is_a_concise_expected_provider_event(self):
        with patch.object(model_router, "_openai_provider", side_effect=_openai_timeout):
            with self.assertLogs(model_router.logger, level="WARNING") as captured:
                results = model_router.route_generation(
                    self.vertical, self.brief, 1, None, [], [ModelProvider.OPENAI]
                )

        self.assertEqual(results[0].status, "error")
        self.assertIn("Provider timeout provider=openai", captured.output[0])
        self.assertNotIn("Traceback", "\n".join(captured.output))

    def test_successful_fallback_runs_after_openai_timeout(self):
        with patch.object(model_router, "_openai_provider", side_effect=_openai_timeout):
            results = model_router.route_generation(
                self.vertical,
                self.brief,
                1,
                None,
                [],
                [ModelProvider.OPENAI],
                fallback_on_provider_error=True,
            )

        self.assertEqual(
            [ModelProvider.OPENAI, ModelProvider.FALLBACK],
            [result.provider for result in results],
        )
        self.assertEqual(["error", "ok"], [result.status for result in results])

    def test_incomplete_openai_response_is_expected_and_falls_back_without_traceback(self):
        with patch.object(model_router, "_openai_provider", side_effect=_openai_incomplete):
            with self.assertLogs(model_router.logger, level="WARNING") as captured:
                results = model_router.route_generation(
                    self.vertical,
                    self.brief,
                    2,
                    None,
                    ["Maya", "Nora"],
                    [ModelProvider.OPENAI],
                    fallback_on_provider_error=True,
                )

        self.assertEqual(
            [ModelProvider.OPENAI, ModelProvider.FALLBACK],
            [result.provider for result in results],
        )
        self.assertEqual(["error", "ok"], [result.status for result in results])
        output = "\n".join(captured.output)
        self.assertIn("Provider incomplete response provider=openai", output)
        self.assertIn("max_output_tokens", output)
        self.assertNotIn("Traceback", output)
        self.assertTrue(results[1].names)

    def test_fallback_failure_keeps_unexpected_traceback(self):
        with patch.object(model_router, "_openai_provider", side_effect=_openai_timeout), patch.object(
            model_router, "_fallback_provider", side_effect=RuntimeError("fallback exploded")
        ):
            with self.assertLogs(model_router.logger, level="WARNING") as captured:
                results = model_router.route_generation(
                    self.vertical,
                    self.brief,
                    1,
                    None,
                    [],
                    [ModelProvider.OPENAI],
                    fallback_on_provider_error=True,
                )

        self.assertEqual(["error", "error"], [result.status for result in results])
        output = "\n".join(captured.output)
        self.assertIn("Provider timeout provider=openai", output)
        self.assertIn("Model provider failed provider=fallback", output)
        self.assertIn("Traceback", output)

    def test_user_receives_fallback_results_after_openai_timeout(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            model_router, "_openai_provider", side_effect=_openai_timeout
        ), patch.dict("os.environ", {"NAMENGINE_AI_PRIMARY_VERTICALS": "baby"}):
            names = platform_app._generate_names_for_route(self.vertical, self.brief)

        self.assertTrue(names)
        self.assertTrue(all(name.metadata["provider"] == "fallback" for name in names))
        self.assertTrue(all(name.metadata["source"] != "openai" for name in names))
        self.assertTrue(all(name.metadata["llm_required"] is False for name in names))
        self.assertTrue(all(name.metadata["ai_primary_fallback"] is True for name in names))
        self.assertTrue(all(name.metadata["ai_primary_requested"] is True for name in names))

    def test_user_sees_unavailable_only_when_both_providers_fail(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            model_router, "_openai_provider", side_effect=_openai_timeout
        ), patch.object(
            model_router, "_fallback_provider", side_effect=RuntimeError("fallback exploded")
        ), patch.dict("os.environ", {"NAMENGINE_AI_PRIMARY_VERTICALS": "baby"}):
            with self.assertRaises(NameGenerationUnavailable):
                platform_app._generate_names_for_route(self.vertical, self.brief)


if __name__ == "__main__":
    unittest.main()

