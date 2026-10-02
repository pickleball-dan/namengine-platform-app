import os
import tempfile
import unittest

from access_helpers import unlock_beta_access
from app import create_app
from namengine.core import (
    build_brief,
    build_compare_items,
    build_reaction,
    save_chosen_name,
    save_reaction,
    save_session,
)
from namengine.core.schemas import NameResult
from namengine.verticals import BOAT


def _boat_result(result_id: str, name: str) -> NameResult:
    slug = name.lower().replace(" ", "-")
    return NameResult(
        id=result_id,
        name=name,
        slug=slug,
        pronunciation=name,
        tagline="A strong name for a memorable vessel.",
        origin="Nautical",
        meaning=f"{name} carries a clear maritime impression.",
        why_this_name=f"{name} balances dockside presence with radio clarity.",
        fit_note=f"{name} fits a confident Boat brief.",
        risks=["Confirm local marina naming overlap."],
    )


class BoatAcceptanceUiTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_disable_boat_images = os.environ.get("NAMENGINE_DISABLE_BOAT_IMAGES")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        os.environ["NAMENGINE_DISABLE_BOAT_IMAGES"] = "1"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_disable_boat_images is None:
            os.environ.pop("NAMENGINE_DISABLE_BOAT_IMAGES", None)
        else:
            os.environ["NAMENGINE_DISABLE_BOAT_IMAGES"] = self.previous_disable_boat_images
        self.tempdir.cleanup()

    def _seed_boat_chain(self):
        brief = build_brief(
            BOAT,
            {
                "boat_type": "Cruiser",
                "boat_use": "Weekend cruising",
                "style": "Classic",
            },
        )
        r1 = [_boat_result("boat-r1-a", "Harbor Star"), _boat_result("boat-r1-b", "Dock Drift")]
        r2 = [_boat_result("boat-r2-a", "Tide Runner"), _boat_result("boat-r2-b", "Blue Current")]
        r3 = [_boat_result("boat-r3-a", "Golden Wake"), _boat_result("boat-r3-b", "Night Mooring")]
        save_session("boat-accept-r1", "boat", brief, r1, round_number=1)
        save_session("boat-accept-r2", "boat", brief, r2, round_number=2, parent_session_id="boat-accept-r1")
        save_session("boat-accept-r3", "boat", brief, r3, round_number=3, parent_session_id="boat-accept-r2")
        save_reaction(build_reaction("boat-accept-r1", "boat-r1-a", "love"))
        save_reaction(build_reaction("boat-accept-r1", "boat-r1-b", "no"))
        save_reaction(build_reaction("boat-accept-r2", "boat-r2-a", "love"))
        save_reaction(build_reaction("boat-accept-r3", "boat-r3-a", "love"))
        return r1, r2, r3

    def test_boat_detail_compare_link_uses_latest_journey_session(self):
        r1, r2, r3 = self._seed_boat_chain()
        unlock_beta_access(self.client, "boat")

        results_compare = self.client.get("/compare/boat-accept-r3")
        detail = self.client.get("/boat/name/boat-accept-r1/boat-r1-a")
        detail_body = detail.get_data(as_text=True)
        linked_compare = self.client.get("/compare/boat-accept-r3")
        linked_body = linked_compare.get_data(as_text=True)

        self.assertEqual(results_compare.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertIn('href="/compare/boat-accept-r3"', detail_body)
        self.assertNotIn('href="/compare/boat-accept-r1"', detail_body)
        self.assertEqual([item["name"] for item in build_compare_items("boat-accept-r3")], [r1[0].name, r2[0].name, r3[0].name])
        self.assertIn(r1[0].name, linked_body)
        self.assertIn(r2[0].name, linked_body)
        self.assertIn(r3[0].name, linked_body)
        self.assertNotIn(r1[1].name, linked_body)
        self.assertNotIn("NamEngine vs. the field", linked_body)

    def test_boat_chosen_page_renders_transom_preview_shell(self):
        r1, _, _ = self._seed_boat_chain()
        chosen = save_chosen_name("boat-accept-r1", r1[0].id)
        unlock_beta_access(self.client, "boat")

        response = self.client.get(f"/chosen/{chosen.id}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Chosen vessel name", body)
        self.assertIn("boat-transom-frame", body)
        self.assertIn("boat-transom-placeholder", body)
        self.assertIn("Transom preview", body)
        self.assertIn(r1[0].name, body)

    def test_boat_progress_overlay_keeps_boat_sonar_markup(self):
        response = self.client.get("/boat")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("boat-progress-visual", body)
        self.assertIn("boat-hull", body)
        self.assertIn("boat-sonar-out", body)


if __name__ == "__main__":
    unittest.main()
