import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from namengine.core.ai_generation import AIGenerationError, _call_openai_with_metadata
from namengine.core.openai_telemetry import (
    IMAGE_USAGE_PREFIX,
    TEXT_USAGE_PREFIX,
    extract_text_usage,
    log_image_usage,
    log_text_usage,
    openai_telemetry_context,
)


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def create(self, **kwargs):
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.responses = FakeResponses(response=response, error=error)


def response_with_usage(text="{\"names\": []}"):
    return SimpleNamespace(
        id="resp_telemetry_test",
        model="gpt-test-returned",
        output_text=text,
        status="completed",
        incomplete_details=None,
        output=[],
        usage=SimpleNamespace(
            input_tokens=120,
            output_tokens=45,
            total_tokens=165,
            input_tokens_details=SimpleNamespace(cached_tokens=80),
            output_tokens_details=SimpleNamespace(reasoning_tokens=12),
        ),
    )


def logged_payload(logger_mock):
    _, prefix, raw_payload = logger_mock.warning.call_args.args
    return prefix, json.loads(raw_payload)


class OpenAIUsageTelemetryTest(unittest.TestCase):
    def test_extracts_all_responses_api_token_counts(self):
        usage = extract_text_usage(response_with_usage().usage)

        self.assertEqual(
            usage,
            {
                "input_tokens": 120,
                "cached_input_tokens": 80,
                "output_tokens": 45,
                "reasoning_tokens": 12,
                "total_tokens": 165,
            },
        )

    def test_supports_legacy_usage_names_and_missing_optional_fields(self):
        usage = extract_text_usage(
            {
                "prompt_tokens": 9,
                "completion_tokens": 4,
                "prompt_tokens_details": {"cached_tokens": 3},
            }
        )

        self.assertEqual(usage["input_tokens"], 9)
        self.assertEqual(usage["cached_input_tokens"], 3)
        self.assertEqual(usage["output_tokens"], 4)
        self.assertEqual(usage["reasoning_tokens"], 0)
        self.assertEqual(usage["total_tokens"], 0)
        self.assertEqual(extract_text_usage(None)["total_tokens"], 0)

    def test_text_log_includes_context_model_response_retry_and_fallback(self):
        with patch("namengine.core.openai_telemetry.logger") as logger:
            with openai_telemetry_context(
                session_id="baby-session-r2",
                parent_session_id="baby-session",
                vertical="baby",
                round_number=2,
            ):
                log_text_usage(
                    response=response_with_usage(),
                    model_requested="gpt-test-requested",
                    duration_ms=321,
                    status="success",
                    retry_number=2,
                    fallback_used=True,
                    action="generate_refinement",
                )

        prefix, payload = logged_payload(logger)
        self.assertEqual(prefix, TEXT_USAGE_PREFIX)
        self.assertEqual(payload["session_id"], "baby-session-r2")
        self.assertEqual(payload["parent_session_id"], "baby-session")
        self.assertEqual(payload["model_requested"], "gpt-test-requested")
        self.assertEqual(payload["model_returned"], "gpt-test-returned")
        self.assertEqual(payload["response_id"], "resp_telemetry_test")
        self.assertEqual(payload["retry_number"], 2)
        self.assertTrue(payload["fallback_used"])

    def test_failed_request_logs_only_safe_error_type(self):
        secret = "customer note and sk-secret-value"
        with patch("namengine.core.openai_telemetry.logger") as logger:
            with self.assertRaises(AIGenerationError):
                _call_openai_with_metadata(
                    prompt={
                        "engine_stage": "candidate_generator_v1",
                        "vertical": "baby",
                        "round_number": 1,
                        "customer_intake": secret,
                    },
                    model="gpt-test",
                    client_factory=lambda: FakeClient(error=RuntimeError(secret)),
                )

        prefix, payload = logged_payload(logger)
        serialized = json.dumps(payload)
        self.assertEqual(prefix, TEXT_USAGE_PREFIX)
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["error_type"], "RuntimeError")
        self.assertNotIn(secret, serialized)
        self.assertNotIn("customer_intake", serialized)

    def test_successful_call_output_is_unchanged_when_telemetry_logging_fails(self):
        response = response_with_usage("unchanged output")
        with patch(
            "namengine.core.openai_telemetry.logger.warning",
            side_effect=RuntimeError("logging unavailable"),
        ):
            result = _call_openai_with_metadata(
                prompt={
                    "engine_stage": "critic_ranker_finalizer_v1",
                    "vertical": "pet",
                    "round_number": 1,
                },
                model="gpt-test",
                client_factory=lambda: FakeClient(response=response),
            )

        self.assertEqual(result["text"], "unchanged output")
        self.assertEqual(result["model"], "gpt-test")
        self.assertEqual(result["usage"]["total_tokens"], 165)

    def test_image_usage_is_a_separate_structured_event(self):
        with patch("namengine.core.openai_telemetry.logger") as logger:
            log_image_usage(
                response={"id": "img_test"},
                chosen_id="chosen-test",
                session_id="baby-session",
                vertical="baby",
                action="generate_chosen_keepsake",
                model="gpt-image-test",
                size="1024x1024",
                quality="medium",
                number_of_images=1,
                duration_ms=456,
                status="success",
                retry_number=0,
            )

        prefix, payload = logged_payload(logger)
        self.assertEqual(prefix, IMAGE_USAGE_PREFIX)
        self.assertEqual(payload["response_id"], "img_test")
        self.assertEqual(payload["number_of_images"], 1)
        self.assertEqual(payload["quality"], "medium")
        self.assertNotIn("input_tokens", payload)

    def test_unapproved_context_content_never_enters_logs(self):
        forbidden = {
            "prompt": "complete prompt",
            "customer_intake": {"email": "parent@example.com"},
            "generated_names": ["Private Name"],
            "cookie": "session-cookie",
        }
        with patch("namengine.core.openai_telemetry.logger") as logger:
            log_text_usage(
                response=response_with_usage(),
                model_requested="gpt-test",
                duration_ms=1,
                status="success",
                context={"session_id": "safe-session", **forbidden},
            )

        _, payload = logged_payload(logger)
        serialized = json.dumps(payload)
        self.assertEqual(payload["session_id"], "safe-session")
        for key in forbidden:
            self.assertNotIn(key, payload)
        self.assertNotIn("parent@example.com", serialized)
        self.assertNotIn("Private Name", serialized)


if __name__ == "__main__":
    unittest.main()
