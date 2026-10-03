import os
import tempfile
import unittest
from dataclasses import replace

from app import _query_string_from_mapping, _sanitize_intake_source, create_app, make_session_id
from access_helpers import unlock_beta_access
from namengine.core import (
    build_brief,
    build_compare_items,
    build_reaction,
    generate_names,
    get_session_snapshot,
    refine_session,
    save_reaction,
    save_session,
)
from namengine.verticals import BABY, PET


class PhaseEightCompareTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def _pet_session_id_for_query(self, query: bytes) -> str:
        source = dict(pair.split("=", 1) for pair in query.decode("utf-8").split("&"))
        source = {key: value.replace("+", " ") for key, value in source.items()}
        sanitized = _sanitize_intake_source(PET, source)
        return make_session_id("pet", _query_string_from_mapping(sanitized).encode("utf-8"))

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def _seed_chain(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = self._pet_session_id_for_query(query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        save_reaction(build_reaction(session_id, "pet-2", "no"))
        round_two_id, _, _ = refine_session(session_id, PET, instruction="shorter")
        save_reaction(build_reaction(round_two_id, "pet-1", "love"))
        save_reaction(build_reaction(round_two_id, "pet-2", "maybe"))
        return session_id, round_two_id

    def test_compare_items_include_loved_names_across_chain(self):
        _, round_two_id = self._seed_chain()

        items = build_compare_items(round_two_id)
        names = [item["name"] for item in items]

        self.assertIn("Rosie", names)
        self.assertIn("love", {item["reaction"] for item in items})
        self.assertLessEqual(len(items), 6)

    def test_baby_compare_items_are_loved_names_across_rounds_only(self):
        brief = build_brief(BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        r1 = generate_names(BABY, brief, round_number=1)
        r2 = generate_names(BABY, brief, round_number=2)
        r3 = generate_names(BABY, brief, round_number=3)
        save_session("baby-r1", "baby", brief, r1, round_number=1)
        save_session("baby-r2", "baby", brief, r2, round_number=2, parent_session_id="baby-r1")
        save_session("baby-r3", "baby", brief, r3, round_number=3, parent_session_id="baby-r2")
        save_reaction(build_reaction("baby-r1", r1[0].id, "love"))
        save_reaction(build_reaction("baby-r1", r1[1].id, "no"))
        save_reaction(build_reaction("baby-r2", r2[0].id, "love"))
        save_reaction(build_reaction("baby-r3", r3[0].id, "love"))

        items = build_compare_items("baby-r3")
        names = [item["name"] for item in items]

        self.assertEqual(len(items), 3)
        self.assertIn(r1[0].name, names)
        self.assertIn(r2[0].name, names)
        self.assertIn(r3[0].name, names)
        self.assertNotIn(r1[1].name, names)
        self.assertEqual({item["reaction"] for item in items}, {"love"})

    def test_baby_compare_route_renders_cards_for_loved_names_across_all_four_rounds(self):
        brief = build_brief(BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        r1 = generate_names(BABY, brief, round_number=1)
        r2 = generate_names(BABY, brief, round_number=2)
        r3 = generate_names(BABY, brief, round_number=3)
        r4 = generate_names(BABY, brief, round_number=4)
        other = generate_names(BABY, brief, round_number=1)
        r3[0] = replace(r3[0], id="baby-99", name="NoOnly", slug="noonly")
        other[0] = replace(other[0], id="baby-99", name="OtherSessionOnly", slug="other-session-only")
        save_session("baby-compare-r1", "baby", brief, r1, round_number=1)
        save_session("baby-compare-r2", "baby", brief, r2, round_number=2, parent_session_id="baby-compare-r1")
        save_session("baby-compare-r3", "baby", brief, r3, round_number=3, parent_session_id="baby-compare-r2")
        save_session("baby-compare-r4", "baby", brief, r4, round_number=4, parent_session_id="baby-compare-r3")
        save_session("baby-other", "baby", brief, other, round_number=1)
        save_reaction(build_reaction("baby-compare-r1", r1[0].id, "love"))
        save_reaction(build_reaction("baby-compare-r2", r2[0].id, "love"))
        save_reaction(build_reaction("baby-compare-r3", r3[0].id, "no"))
        save_reaction(build_reaction("baby-compare-r4", r4[0].id, "love"))
        save_reaction(build_reaction("baby-other", other[0].id, "love"))
        unlock_beta_access(self.client, "baby", return_session="baby-compare-r1")

        response = self.client.get("/compare/baby-compare-r4")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Compare All Your Loved Names", body)
        self.assertIn('data-compare-favorite-card', body)
        self.assertIn("Loved in Round 1", body)
        self.assertIn("Loved in Round 2", body)
        self.assertIn("Loved in Round 4", body)
        self.assertIn(r1[0].name, body)
        self.assertIn(r2[0].name, body)
        self.assertIn(r4[0].name, body)
        self.assertNotIn(r3[0].name, body)
        self.assertNotIn(other[0].name, body)
        self.assertNotIn("NamEngine vs. the field", body)
        self.assertNotIn("<table", body)
        self.assertIn('action="/choose"', body)

    def test_compare_does_not_expose_historical_maybe_as_backup(self):
        query = b"species=Cat&personality=Quiet&style=Soft"
        session_id = self._pet_session_id_for_query(query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "pet-3", "maybe"))
        save_reaction(build_reaction(session_id, "pet-4", "maybe"))

        items = build_compare_items(session_id)

        self.assertEqual(items, [])

    def test_compare_route_renders_decision_page(self):
        _, round_two_id = self._seed_chain()
        unlock_beta_access(self.client, "pet")
        response = self.client.get(f"/compare/{round_two_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Compare All Your Loved Names", body)
        self.assertIn("compare-favorites-grid", body)
        self.assertIn('data-compare-favorite-card', body)
        self.assertIn("result-card compare-favorite-card", body)
        self.assertNotIn("<table", body)
        self.assertNotIn("engine-audit-table", body)
        self.assertIn("Best if", body)
        self.assertIn("Worth noting", body)
        self.assertIn("Why it stayed with you", body)
        self.assertNotIn("NamEngine vs. the field", body)
        self.assertNotIn("Watch-out", body)
        self.assertIn("Open detail", body)
        self.assertIn('action="/choose"', body)
        self.assertIn("Choose Rosie", body)
        self.assertIn(f"/pet/name/{round_two_id}/pet-1", body)
        self.assertIn("Rosie", body)
        self.assertIn("Loved in Round 2", body)

    def test_compare_empty_state_when_no_loved_names(self):
        session_id, round_two_id = self._seed_chain()
        round_three_id, _, _ = refine_session(round_two_id, PET, instruction="finalists")
        for snapshot_id in (session_id, round_two_id):
            snapshot = get_session_snapshot(snapshot_id)
            for row in snapshot["reactions"]:
                save_reaction(build_reaction(snapshot_id, row["result_id"], "no"))
        unlock_beta_access(self.client, "pet")

        response = self.client.get(f"/compare/{round_three_id}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("No loved names yet.", body)
        self.assertNotIn("NamEngine vs. the field", body)

    def test_results_page_links_to_compare_and_share_sheet(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = self._pet_session_id_for_query(query)
        response = self.client.get(f"/pet/results?{query.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn(f"/pet/access?return_session={session_id}", body)
        self.assertIn(f'data-taste-share-url="/share/{session_id}"', body)
        self.assertIn("js/share-list.js", body)

    def test_free_compare_route_requires_paid_access(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = self._pet_session_id_for_query(query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.get(f"/compare/{session_id}")

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/pet/access?return_session={session_id}", response.headers["Location"])

    def test_compare_route_rejects_missing_session(self):
        response = self.client.get("/compare/missing")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
