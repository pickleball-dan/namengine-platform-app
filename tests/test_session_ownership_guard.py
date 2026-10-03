import os
import tempfile
import unittest
from unittest.mock import patch

from access_helpers import csrf_token, unlock_beta_access
from app import create_app
from namengine.core import (
    build_brief,
    build_reaction,
    generate_names,
    get_session_snapshot,
    save_chosen_name,
    save_reaction,
    save_session,
)
from namengine.core.storage import get_magic_links_by_email
from namengine.magic_links import create_magic_link
from namengine.verticals import PET


class SessionOwnershipGuardTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_openai_key = os.environ.get("OPENAI_API_KEY")
        self.previous_disable_pet_images = os.environ.get("NAMENGINE_DISABLE_PET_IMAGES")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "ownership.sqlite3")
        os.environ["OPENAI_API_KEY"] = ""
        os.environ["NAMENGINE_DISABLE_PET_IMAGES"] = "1"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_openai_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.previous_openai_key
        if self.previous_disable_pet_images is None:
            os.environ.pop("NAMENGINE_DISABLE_PET_IMAGES", None)
        else:
            os.environ["NAMENGINE_DISABLE_PET_IMAGES"] = self.previous_disable_pet_images
        self.tempdir.cleanup()

    def _seed_pet_session(self, session_id: str):
        brief = build_brief(PET, {"species": "Dog", "personality": "Gentle", "style": "Warm"})
        results = generate_names(PET, brief)
        save_session(session_id, "pet", brief, results)
        return results

    def _unlock_for_session(self, session_id: str):
        self.client.get("/")
        unlock_beta_access(self.client, "pet", return_session=session_id)

    def test_bound_paid_session_can_react_compare_choose_and_view_chosen(self):
        results = self._seed_pet_session("pet-owned")
        self._unlock_for_session("pet-owned")

        reaction = self.client.post(
            "/api/react",
            json={
                "session_id": "pet-owned",
                "result_id": results[0].id,
                "value": "love",
                "csrf_token": csrf_token(self.client),
            },
        )
        compare = self.client.get("/compare/pet-owned")
        chosen_response = self.client.post(
            "/choose",
            data={
                "session_id": "pet-owned",
                "result_id": results[0].id,
                "csrf_token": csrf_token(self.client),
            },
            follow_redirects=False,
        )
        chosen_id = get_session_snapshot("pet-owned")["chosen_names"][0]["id"]
        chosen_page = self.client.get(f"/chosen/{chosen_id}")

        self.assertEqual(reaction.status_code, 201)
        self.assertEqual(compare.status_code, 200)
        self.assertEqual(chosen_response.status_code, 302)
        self.assertEqual(chosen_page.status_code, 200)

    def test_same_vertical_paid_cookie_cannot_access_unrelated_session(self):
        self._seed_pet_session("pet-owned")
        unrelated = self._seed_pet_session("pet-unrelated")
        chosen = save_chosen_name("pet-unrelated", unrelated[0].id)
        self._unlock_for_session("pet-owned")

        reaction = self.client.post(
            "/api/react",
            json={
                "session_id": "pet-unrelated",
                "result_id": unrelated[0].id,
                "value": "love",
                "csrf_token": csrf_token(self.client),
            },
        )
        compare = self.client.get("/compare/pet-unrelated", follow_redirects=False)
        choose = self.client.post(
            "/choose",
            data={
                "session_id": "pet-unrelated",
                "result_id": unrelated[0].id,
                "csrf_token": csrf_token(self.client),
            },
            follow_redirects=False,
        )
        chosen_page = self.client.get(f"/chosen/{chosen.id}", follow_redirects=False)

        self.assertEqual(reaction.status_code, 402)
        self.assertEqual(reaction.get_json()["error"], "access_required")
        self.assertEqual(compare.status_code, 302)
        self.assertIn("/pet/access?return_session=pet-unrelated", compare.headers["Location"])
        self.assertEqual(choose.status_code, 302)
        self.assertIn("/pet/access?return_session=pet-unrelated", choose.headers["Location"])
        self.assertEqual(chosen_page.status_code, 302)
        self.assertIn("/pet/access?return_session=pet-unrelated", chosen_page.headers["Location"])

    def test_magic_link_recovery_restores_only_the_linked_session(self):
        self._seed_pet_session("pet-linked")
        self._seed_pet_session("pet-other")
        token = create_magic_link(
            email="tester@example.com",
            vertical="pet",
            session_id="pet-linked",
            session_state={"session_id": "pet-linked", "vertical": "pet"},
        )
        fresh = self.app.test_client()

        resumed = fresh.get(f"/continue/{token}", follow_redirects=False)
        linked = fresh.get("/results/session/pet-linked", follow_redirects=False)
        other = fresh.get("/results/session/pet-other", follow_redirects=False)

        self.assertEqual(resumed.status_code, 302)
        self.assertEqual(resumed.headers["Location"], "/results/session/pet-linked")
        self.assertEqual(linked.status_code, 200)
        self.assertEqual(other.status_code, 302)
        self.assertIn("/pet/access?return_session=pet-other", other.headers["Location"])

    def test_chosen_share_token_is_read_only_and_does_not_grant_session_ownership(self):
        results = self._seed_pet_session("pet-shared")
        save_reaction(build_reaction("pet-shared", results[0].id, "love"))
        chosen = save_chosen_name("pet-shared", results[0].id)
        self._unlock_for_session("pet-shared")

        with patch("app.send_chosen_share_link") as send:
            share = self.client.post(
                f"/api/chosen/{chosen.id}/share",
                json={"email": "recipient@example.com", "csrf_token": csrf_token(self.client)},
            )
        token = send.call_args.kwargs["magic_url"].rsplit("/", 1)[-1]
        fresh = self.app.test_client()
        shared_page = fresh.get(f"/chosen/shared/{token}")
        compare = fresh.get("/compare/pet-shared", follow_redirects=False)
        reaction = fresh.post(
            "/api/react",
            json={
                "session_id": "pet-shared",
                "result_id": results[1].id,
                "value": "love",
                "csrf_token": csrf_token(fresh),
            },
        )

        self.assertEqual(share.status_code, 200)
        self.assertEqual(shared_page.status_code, 200)
        self.assertIsNone(fresh.get_cookie("namengine_pet_beta_access"))
        self.assertEqual(compare.status_code, 302)
        self.assertIn("/pet/access?return_session=pet-shared", compare.headers["Location"])
        self.assertEqual(reaction.status_code, 402)
        self.assertEqual(reaction.get_json()["error"], "access_required")
        records = get_magic_links_by_email("recipient@example.com", "pet")
        self.assertIn('"purpose": "chosen_share"', records[0]["session_state_json"])


if __name__ == "__main__":
    unittest.main()
