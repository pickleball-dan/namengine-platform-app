import base64
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app as app_module
from app import create_app
from namengine.core import (
    build_brief,
    cleanup_generated_images,
    ensure_keepsake_for_chosen,
    generated_image_directory,
    get_chosen_snapshot,
    save_chosen_name,
    save_session,
    keepsake_runtime_config,
    update_chosen_metadata,
)
from namengine.core.schemas import NameResult
from namengine.verticals import BABY, BUSINESS, PET


class MultiVerticalImageGenerationTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "NAMENGINE_DB_PATH": str(Path(self.tempdir.name) / "test.sqlite3"),
                "NAMENGINE_GENERATED_IMAGE_DIR": self.tempdir.name,
                "OPENAI_API_KEY": "test-key",
                "NAMENGINE_IMAGE_MODEL": "gpt-image-1-mini",
                "NAMENGINE_DISABLE_BABY_IMAGES": "0",
                "NAMENGINE_DISABLE_PET_IMAGES": "0",
                "NAMENGINE_DISABLE_BUSINESS_IMAGES": "0",
            },
        )
        self.env.start()
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.env.stop()
        self.tempdir.cleanup()

    def _chosen(self, vertical, inputs, name):
        brief = build_brief(vertical, inputs)
        result = NameResult(
            id=f"{vertical.slug}-1",
            name=name,
            slug=name.lower(),
            tagline="A confident fit",
            why_this_name="It fits the brief.",
            fit_note="Strong match.",
        )
        session_id = f"{vertical.slug}-image-session"
        save_session(session_id, vertical.slug, brief, [result])
        chosen = save_chosen_name(session_id, result.id)
        return get_chosen_snapshot(chosen.id)

    def test_image_request_uses_selected_name_vertical_context_and_supported_model(self):
        cases = (
            (BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft"}, "Eloise", "baby blanket"),
            (PET, {"pet_type": "Dog", "pet_breed": "Whippet", "pet_color": "Blue gray", "pet_life_stage": "Mature", "style": "Classic", "vibe": "Playful"}, "Clover", "Whippet"),
            (BUSINESS, {"business_description": "Premium recovery studio", "industry": "Wellness", "audience": "Premium clients", "style": "Clear and credible"}, "Northwell", "Premium recovery studio"),
        )
        png = base64.b64encode(b"valid-png-bytes").decode("ascii")

        for vertical, inputs, name, context in cases:
            with self.subTest(vertical=vertical.slug):
                snapshot = self._chosen(vertical, inputs, name)
                generate = Mock(return_value=SimpleNamespace(data=[SimpleNamespace(b64_json=png, url=None)]))
                with patch("namengine.core.pet_portrait.OpenAI") as client:
                    client.return_value.images.generate = generate
                    image = ensure_keepsake_for_chosen(
                        snapshot["chosen"],
                        {"name": name, "tagline": "A confident fit"},
                        snapshot["session"],
                    )

                request = generate.call_args.kwargs
                self.assertEqual(request["model"], "gpt-image-1-mini")
                self.assertEqual(request["size"], "1024x1024")
                self.assertEqual(request["n"], 1)
                self.assertIn(name, request["prompt"])
                self.assertIn(context, request["prompt"])
                self.assertEqual(image["status"], "ready")
                self.assertNotIn(snapshot["chosen"]["id"], image["filename"])
                self.assertGreaterEqual(len(Path(image["filename"]).stem), 24)
                dirname = {
                    "baby": "generated_baby_keepsakes",
                    "pet": "generated_pet_portraits",
                    "business": "generated_business_images",
                }[vertical.slug]
                self.assertTrue((Path(self.tempdir.name) / dirname / image["filename"]).exists())

    def test_business_image_renders_on_chosen_page_and_generated_route(self):
        snapshot = self._chosen(
            BUSINESS,
            {
                "business_description": "Premium recovery studio",
                "industry": "Wellness",
                "audience": "Premium clients",
                "style": "Clear and credible",
            },
            "Northwell",
        )
        png = base64.b64encode(b"brand-image").decode("ascii")
        with patch("namengine.core.pet_portrait.OpenAI") as client:
            client.return_value.images.generate.return_value = {
                "data": [{"b64_json": png}]
            }
            image = ensure_keepsake_for_chosen(
                snapshot["chosen"],
                {"name": "Northwell", "tagline": "A confident fit"},
                snapshot["session"],
            )

        page = self.client.get(f"/chosen/{snapshot['chosen']['id']}")
        asset = self.client.get(image["url"])
        body = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Brand direction board for Northwell", body)
        self.assertIn(image["url"], body)
        self.assertEqual(asset.status_code, 200)
        self.assertEqual(asset.data, b"brand-image")
        asset.close()

    def test_failure_is_sanitized_preserves_choice_and_exposes_retry(self):
        snapshot = self._chosen(
            PET,
            {"pet_type": "Dog", "pet_breed": "Whippet", "style": "Classic", "vibe": "Playful"},
            "Clover",
        )
        secret_error = RuntimeError("provider rejected sk-super-secret")
        with patch("namengine.core.pet_portrait.OpenAI") as client:
            client.return_value.images.generate.side_effect = secret_error
            with self.assertRaises(RuntimeError):
                ensure_keepsake_for_chosen(
                    snapshot["chosen"], {"name": "Clover"}, snapshot["session"]
                )

        after = get_chosen_snapshot(snapshot["chosen"]["id"])
        metadata = after["chosen"]["metadata"]["pet_portrait"]
        self.assertEqual(after["chosen"]["name"], "Clover")
        self.assertEqual(after["result"]["name"], "Clover")
        self.assertEqual(metadata["status"], "failed")
        self.assertNotIn("sk-super-secret", metadata["error_message"])

        page = self.client.get(f"/chosen/{after['chosen']['id']}")
        body = page.get_data(as_text=True)
        self.assertIn("Clover", body)
        self.assertIn("Try again", body)
        self.assertIn(f"/api/chosen/{after['chosen']['id']}/portrait/retry", body)

    def test_retry_changes_failed_image_to_pending_without_losing_selection(self):
        snapshot = self._chosen(
            BABY,
            {"gender": "Boy", "style": "Classic", "sound": "Strong"},
            "Miles",
        )
        update_chosen_metadata(
            snapshot["chosen"]["id"],
            {"baby_keepsake": {"status": "failed", "error_message": "Image creation failed. Please try again."}},
        )

        with patch("app.Thread") as thread:
            response = self.client.post(
                f"/api/chosen/{snapshot['chosen']['id']}/portrait/retry"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["portrait"]["status"], "pending")
        self.assertEqual(get_chosen_snapshot(snapshot["chosen"]["id"])["chosen"]["name"], "Miles")
        thread.assert_called_once()

    def test_runtime_supports_default_development_and_explicit_production_storage(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NAMENGINE_GENERATED_IMAGE_DIR", None)
            self.assertEqual(
                generated_image_directory("pet"),
                Path(os.environ["NAMENGINE_DB_PATH"]).parent / "generated_pet_portraits",
            )

        with patch.dict(os.environ, {"NAMENGINE_GENERATED_IMAGE_DIR": self.tempdir.name}):
            self.assertEqual(
                generated_image_directory("business"),
                Path(self.tempdir.name) / "generated_business_images",
            )
            runtime = keepsake_runtime_config("business")
            self.assertTrue(runtime["configured"])
            self.assertTrue(runtime["storage_configured"])
            self.assertNotIn("api_key", runtime)

    def test_invalid_provider_response_becomes_retryable_failure(self):
        snapshot = self._chosen(
            BUSINESS,
            {"business_description": "Design studio", "audience": "Premium clients", "style": "Premium and refined"},
            "Formwell",
        )
        with patch("namengine.core.pet_portrait.OpenAI") as client:
            client.return_value.images.generate.return_value = {"data": [{}]}
            with self.assertRaises(RuntimeError):
                ensure_keepsake_for_chosen(
                    snapshot["chosen"], {"name": "Formwell"}, snapshot["session"]
                )

        after = get_chosen_snapshot(snapshot["chosen"]["id"])
        self.assertEqual(after["chosen"]["metadata"]["business_image"]["status"], "failed")
        self.assertEqual(after["chosen"]["name"], "Formwell")

    def test_retention_cleanup_removes_only_expired_png_files(self):
        directory = generated_image_directory("pet")
        directory.mkdir(parents=True, exist_ok=True)
        expired = directory / "expired.png"
        current = directory / "current.png"
        unrelated = directory / "notes.txt"
        expired.write_bytes(b"old")
        current.write_bytes(b"new")
        unrelated.write_text("keep", encoding="utf-8")
        now = time.time()
        os.utime(expired, (now - 31 * 86400, now - 31 * 86400))

        with patch.dict(os.environ, {"NAMENGINE_IMAGE_RETENTION_DAYS": "30"}):
            removed = cleanup_generated_images("pet", now=now)

        self.assertEqual(removed, 1)
        self.assertFalse(expired.exists())
        self.assertTrue(current.exists())
        self.assertTrue(unrelated.exists())

    def test_forced_failure_refresh_return_and_repeated_retry_preserve_state(self):
        snapshot = self._chosen(
            PET,
            {"pet_type": "Dog", "pet_breed": "Whippet", "style": "Classic", "vibe": "Playful"},
            "Clover",
        )
        chosen_id = snapshot["chosen"]["id"]
        session_id = snapshot["chosen"]["session_id"]
        result_id = snapshot["chosen"]["result_id"]
        reaction = self.client.post(
            "/api/react",
            json={"session_id": session_id, "result_id": result_id, "value": "love"},
        )
        self.assertEqual(reaction.status_code, 201)
        update_chosen_metadata(
            chosen_id,
            {"pet_portrait": {"status": "failed", "error_message": "Image creation failed. Please try again."}},
        )

        for _ in range(2):
            page = self.client.get(f"/chosen/{chosen_id}")
            body = page.get_data(as_text=True)
            self.assertIn("Meet Clover", body)
            self.assertIn("Try again", body)

        results = self.client.get(f"/results/session/{session_id}").get_data(as_text=True)
        self.assertIn("Clover", results)
        self.assertIn("Saved 1 name", results)

        try:
            with patch("app.Thread") as thread:
                first = self.client.post(f"/api/chosen/{chosen_id}/portrait/retry")
                second = self.client.post(f"/api/chosen/{chosen_id}/portrait/retry")
            self.assertEqual(first.get_json()["portrait"]["status"], "pending")
            self.assertEqual(second.get_json()["portrait"]["status"], "pending")
            thread.assert_called_once()
            self.assertEqual(get_chosen_snapshot(chosen_id)["chosen"]["name"], "Clover")
        finally:
            app_module._portrait_jobs.discard(chosen_id)


if __name__ == "__main__":
    unittest.main()
