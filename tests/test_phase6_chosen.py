import os
import tempfile
import unittest

from app import create_app, make_session_id
from namengine.core import (
    build_brief,
    build_pet_portrait_prompt,
    generate_names,
    get_chosen_snapshot,
    get_session_snapshot,
    portrait_details_from_brief,
    save_chosen_name,
    save_session,
)
from namengine.verticals import PET


class PhaseSixChosenNameTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_disable_pet_images = os.environ.get("NAMENGINE_DISABLE_PET_IMAGES")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        os.environ["NAMENGINE_DISABLE_PET_IMAGES"] = "1"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_disable_pet_images is None:
            os.environ.pop("NAMENGINE_DISABLE_PET_IMAGES", None)
        else:
            os.environ["NAMENGINE_DISABLE_PET_IMAGES"] = self.previous_disable_pet_images
        self.tempdir.cleanup()

    def test_save_chosen_name_persists_choice(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)
        save_session("pet-session", "pet", brief, results)

        chosen = save_chosen_name("pet-session", "pet-1")
        snapshot = get_chosen_snapshot(chosen.id)

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["chosen"]["name"], "Milo")
        self.assertEqual(snapshot["chosen"]["vertical"], "pet")
        self.assertEqual(snapshot["result"]["name"], "Milo")

    def test_choose_route_redirects_to_chosen_page(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": "pet-1"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/chosen/chosen-", response.headers["Location"])

    def test_chosen_page_renders_single_name(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        response = self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": "pet-1"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Milo", body)
        self.assertIn("Why this name?", body)
        self.assertIn("share-preview", body)
        self.assertIn("Final pick", body)
        self.assertIn("Meet Milo", body)
        self.assertNotIn("chosen-hero", body)
        self.assertNotIn("share-preview-logo", body)
        self.assertNotIn("share-preview-brand", body)
        self.assertIn("images/pet/namengine-pet-logo-transparent.png", body)
        self.assertIn("Copy link", body)
        self.assertIn("Start another", body)

    def test_chosen_page_uses_pet_portrait_details_when_present(self):
        query = (
            b"pet_type=Dog&pet_breed=Golden+Retriever&pet_color=Honey"
            b"&pet_life_stage=Puppy&style=Classic&vibe=Gentle"
        )
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        response = self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": "pet-1"},
            follow_redirects=True,
        )
        chosen_id = get_session_snapshot(session_id)["chosen_names"][0]["id"]

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("pet-portrait-frame", body)
        self.assertIn("Breed", body)
        self.assertIn("Golden Retriever", body)
        self.assertIn("Color", body)
        self.assertIn("Honey", body)
        self.assertIn("Age", body)
        self.assertIn("Puppy", body)
        self.assertIn("Milo", body)

        snapshot = get_chosen_snapshot(chosen_id)
        self.assertEqual(snapshot["chosen"]["metadata"]["pet_portrait"]["status"], "not_configured")

    def test_chosen_portrait_status_reports_runtime_without_secret(self):
        query = (
            b"pet_type=Dog&pet_breed=Golden+Retriever&pet_color=Honey"
            b"&pet_life_stage=Puppy&style=Classic&vibe=Gentle"
        )
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": "pet-1"},
            follow_redirects=True,
        )
        chosen_id = get_session_snapshot(session_id)["chosen_names"][0]["id"]

        response = self.client.get(f"/api/chosen/{chosen_id}/portrait")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(payload["runtime"]["configured"])
        self.assertTrue(payload["runtime"]["disabled"])
        self.assertNotIn("api_key", payload)
        self.assertEqual(payload["portrait"]["status"], "not_configured")
        self.assertEqual(payload["portrait"]["model"], "gpt-image-1")

    def test_pet_portrait_prompt_is_timeless_and_avoids_generated_text(self):
        brief = {
            "inputs": {
                "pet_type": "Dog",
                "pet_breed": "Whippet",
                "pet_color": "Blue gray",
                "pet_life_stage": "Adult",
                "vibe": "Elegant",
                "style": "Classic",
            }
        }
        details = portrait_details_from_brief(brief)
        prompt = build_pet_portrait_prompt(
            {"name": "Clover"},
            {"name": "Clover"},
            brief,
            details,
        )

        self.assertEqual(details["breed"], "Whippet")
        self.assertIn("timeless framed studio portrait", prompt)
        self.assertIn("Blue gray adult Whippet dog named Clover", prompt)
        self.assertIn("Do not include words", prompt)

    def test_session_stores_round_metadata(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)
        save_session(
            "pet-round-2",
            "pet",
            brief,
            results,
            round_number=2,
            parent_session_id="pet-round-1",
            refinement_prompt="More like Milo",
        )

        snapshot = get_session_snapshot("pet-round-2")

        self.assertEqual(snapshot["session"]["round_number"], 2)
        self.assertEqual(snapshot["session"]["parent_session_id"], "pet-round-1")
        self.assertEqual(snapshot["session"]["refinement_prompt"], "More like Milo")


if __name__ == "__main__":
    unittest.main()
