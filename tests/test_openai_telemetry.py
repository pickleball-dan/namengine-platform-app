import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from namengine.core.ai_generation import AIGenerationError, _call_openai_with_metadata
from namengine.core.openai_telemetry import (
    IMAGE_USAGE_PREFIX,
    TEXT_USAGE_PREFIX,
    TelemetryQueryError,
    aggregate_openai_telemetry,
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

    def test_failed_request_event_logs_only_safe_error_type(self):
        secret = "customer note and sk-secret-value"
        with patch("namengine.core.openai_telemetry.logger") as logger:
            log_text_usage(
                response=None,
                model_requested="gpt-test",
                duration_ms=12,
                status="failed",
                error_type="RuntimeError",
                action="candidate_generator_v1",
                context={
                    "vertical": "baby",
                    "round_number": 1,
                    "customer_intake": secret,
                },
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

    def test_existing_text_event_also_writes_aggregate_safe_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, "telemetry.jsonl")
            with patch.dict(os.environ, {"NAMENGINE_OPENAI_TELEMETRY_PATH": target}):
                with patch("namengine.core.openai_telemetry.logger"):
                    with openai_telemetry_context(session_id="private-session", vertical="baby"):
                        log_text_usage(
                            response=response_with_usage(),
                            model_requested="gpt-test-requested",
                            duration_ms=321,
                            status="success",
                            action="generate_refinement",
                        )

            event = json.loads(open(target, encoding="utf-8").read())
            self.assertEqual(event["request_type"], "responses.create")
            self.assertEqual(event["model"], "gpt-test-returned")
            self.assertEqual(event["total_tokens"], 165)
            self.assertNotIn("session_id", event)
            self.assertNotIn("response_id", event)


class OpenAITelemetryAggregationTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.target = os.path.join(self.tempdir.name, "telemetry.jsonl")
        self.environment = patch.dict(os.environ, {"NAMENGINE_OPENAI_TELEMETRY_PATH": self.target})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.tempdir.cleanup()

    def _event(self, timestamp, **overrides):
        event = {
            "timestamp": timestamp,
            "request_type": "responses.create",
            "model": "gpt-4.1-mini",
            "latency_ms": 100,
            "success": True,
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "context": "generation",
        }
        event.update(overrides)
        return event

    def _write(self, records, trailing="\n"):
        with open(self.target, "w", encoding="utf-8") as handle:
            handle.write("\n".join(json.dumps(item) for item in records) + trailing)

    def test_aggregates_text_images_failures_and_missing_usage(self):
        self._write([
            self._event("2026-07-20T10:00:00Z"),
            self._event(
                "2026-07-20T11:00:00Z",
                success=False,
                latency_ms=300,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
                error_type="TimeoutError",
            ),
            self._event(
                "2026-07-21T12:00:00Z",
                request_type="images.generate",
                model="gpt-image-1-mini",
                context="generate_chosen_keepsake",
                latency_ms=500,
                input_tokens=None,
                output_tokens=None,
                total_tokens=None,
                image_count=1,
            ),
        ])

        report = aggregate_openai_telemetry(
            start="2026-07-20",
            end="2026-07-21",
            now=datetime(2026, 7, 21, 20, tzinfo=UTC),
        )

        self.assertEqual(report["summary"]["request_count"], 3)
        self.assertEqual(report["summary"]["success_count"], 2)
        self.assertEqual(report["summary"]["failure_count"], 1)
        self.assertEqual(report["summary"]["total_tokens"], 15)
        self.assertEqual(report["summary"]["image_generation_count"], 1)
        self.assertEqual(report["summary"]["requests_missing_token_usage"], 2)
        self.assertEqual(report["summary"]["average_latency_ms"], 300.0)
        self.assertEqual(
            report["failures_by_error_type"],
            [{"error_type": "TimeoutError", "failure_count": 1}],
        )

    def test_filters_by_date_request_type_model_and_success(self):
        self._write([
            self._event("2026-07-18T10:00:00Z"),
            self._event("2026-07-20T10:00:00Z", model="other-model"),
            self._event("2026-07-20T11:00:00Z", success=False),
            self._event("2026-07-21T10:00:00Z", request_type="images.generate"),
        ])

        report = aggregate_openai_telemetry(
            start="2026-07-20",
            end="2026-07-20",
            request_type="responses.create",
            model="gpt-4.1-mini",
            success="false",
        )

        self.assertEqual(report["summary"]["request_count"], 1)
        self.assertEqual(report["summary"]["failure_count"], 1)

    def test_malformed_partial_missing_and_empty_files_are_safe(self):
        self._write([self._event("2026-07-20T10:00:00Z")], trailing="\n{not-json\n{\"timestamp\":")
        report = aggregate_openai_telemetry(start="2026-07-20", end="2026-07-20")
        self.assertEqual(report["summary"]["request_count"], 1)

        os.remove(self.target)
        missing = aggregate_openai_telemetry(start="2026-07-20", end="2026-07-20")
        self.assertEqual(missing["summary"]["request_count"], 0)

        open(self.target, "w", encoding="utf-8").close()
        empty = aggregate_openai_telemetry(start="2026-07-20", end="2026-07-20")
        self.assertEqual(empty["requests_by_day"], [])

    def test_scan_below_configured_limit_reports_not_truncated(self):
        self._write([
            self._event("2026-07-20T10:00:00Z"),
            self._event("2026-07-20T11:00:00Z"),
        ])

        with patch.dict(os.environ, {"NAMENGINE_OPENAI_TELEMETRY_MAX_SCAN_RECORDS": "5"}):
            report = aggregate_openai_telemetry(start="2026-07-20", end="2026-07-20")

        self.assertEqual(report["summary"]["request_count"], 2)
        self.assertEqual(report["scan"], {
            "truncated": False,
            "records_scanned": 2,
            "scan_limit": 5,
        })

    def test_scan_exactly_at_configured_limit_reports_not_truncated(self):
        self._write([
            self._event("2026-07-20T10:00:00Z"),
            self._event("2026-07-20T11:00:00Z"),
        ])

        with patch.dict(os.environ, {"NAMENGINE_OPENAI_TELEMETRY_MAX_SCAN_RECORDS": "2"}):
            report = aggregate_openai_telemetry(start="2026-07-20", end="2026-07-20")

        self.assertEqual(report["summary"]["request_count"], 2)
        self.assertEqual(report["scan"], {
            "truncated": False,
            "records_scanned": 2,
            "scan_limit": 2,
        })

    def test_scan_exceeding_configured_limit_reports_truncated(self):
        self._write([
            self._event("2026-07-20T10:00:00Z"),
            self._event("2026-07-20T11:00:00Z"),
            self._event("2026-07-20T12:00:00Z"),
        ])

        with patch.dict(os.environ, {"NAMENGINE_OPENAI_TELEMETRY_MAX_SCAN_RECORDS": "2"}):
            report = aggregate_openai_telemetry(start="2026-07-20", end="2026-07-20")

        self.assertEqual(report["summary"]["request_count"], 2)
        self.assertEqual(report["scan"], {
            "truncated": True,
            "records_scanned": 2,
            "scan_limit": 2,
        })

    def test_invalid_scan_limit_configuration_falls_back_to_default(self):
        self._write([self._event("2026-07-20T10:00:00Z")])

        for configured_value in ("not-a-number", "0", "-10"):
            with self.subTest(configured_value=configured_value):
                with patch.dict(os.environ, {"NAMENGINE_OPENAI_TELEMETRY_MAX_SCAN_RECORDS": configured_value}):
                    report = aggregate_openai_telemetry(start="2026-07-20", end="2026-07-20")

                self.assertEqual(report["summary"]["request_count"], 1)
                self.assertEqual(report["scan"], {
                    "truncated": False,
                    "records_scanned": 1,
                    "scan_limit": 250000,
                })

    def test_unbounded_date_range_is_rejected(self):
        with self.assertRaisesRegex(TelemetryQueryError, "cannot exceed"):
            aggregate_openai_telemetry(start="2026-01-01", end="2026-07-20")


if __name__ == "__main__":
    unittest.main()
