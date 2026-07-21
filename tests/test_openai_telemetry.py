import json
import time

from namengine.core.openai_telemetry import record_openai_telemetry


def test_success_logs_usage_and_image_fields(tmp_path, monkeypatch):
    target = tmp_path / "telemetry.jsonl"
    monkeypatch.setenv("NAMENGINE_OPENAI_TELEMETRY_PATH", str(target))
    record_openai_telemetry(request_type="images.generate", model="gpt-image-1", started_at=time.perf_counter(), success=True, usage={"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}, image_count=1, image_size="1024x1024")
    event = json.loads(target.read_text())
    assert event["total_tokens"] == 5 and event["image_size"] == "1024x1024"


def test_unavailable_usage_is_safe(tmp_path, monkeypatch):
    target = tmp_path / "telemetry.jsonl"
    monkeypatch.setenv("NAMENGINE_OPENAI_TELEMETRY_PATH", str(target))
    record_openai_telemetry(request_type="responses.create", model="m", started_at=time.perf_counter(), success=True)
    assert json.loads(target.read_text())["input_tokens"] is None


def test_failure_logs_error(tmp_path, monkeypatch):
    target = tmp_path / "telemetry.jsonl"
    monkeypatch.setenv("NAMENGINE_OPENAI_TELEMETRY_PATH", str(target))
    record_openai_telemetry(request_type="responses.create", model="m", started_at=time.perf_counter(), success=False, error_type="TimeoutError")
    event = json.loads(target.read_text())
    assert event["success"] is False and event["error_type"] == "TimeoutError"


def test_write_failure_never_raises(monkeypatch):
    monkeypatch.setenv("NAMENGINE_OPENAI_TELEMETRY_PATH", "Z:\\missing\\telemetry.jsonl")
    record_openai_telemetry(request_type="responses.create", model="m", started_at=time.perf_counter(), success=True)
