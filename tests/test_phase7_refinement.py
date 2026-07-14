import os
import tempfile
import unittest

from app import create_app, make_session_id
from namengine.core import (
    build_reaction,
    build_reaction_effect_summary,
    get_session_snapshot,
    refine_session,
    save_reaction,
)
from namengine.verticals import BABY, PET


class PhaseSevenRefinementTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def _seed_round_one(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        save_reaction(build_reaction(session_id, "pet-2", "no"))
        save_reaction(build_reaction(session_id, "pet-3", "maybe"))
        return session_id

    def _seed_baby_round_one(self):
        query = b"gender=Girl&style=Classic&sound=Soft"
        session_id = make_session_id("baby", query)
        self.client.get(f"/baby/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "baby-1", "love"))
        save_reaction(build_reaction(session_id, "baby-2", "maybe"))
        save_reaction(build_reaction(session_id, "baby-3", "no"))
        return session_id

    def test_reaction_effect_summary_is_short_and_directional(self):
        session_id = self._seed_round_one()
        snapshot = get_session_snapshot(session_id)

        summary = build_reaction_effect_summary(snapshot)

        self.assertIn("We leaned toward Rosie.", summary)
        self.assertIn("We moved away from Juniper.", summary)

    def test_refine_session_creates_round_two_child(self):
        session_id = self._seed_round_one()

        child_session_id, brief, results = refine_session(
            session_id,
            PET,
            instruction="shorter and warmer",
        )
        child = get_session_snapshot(child_session_id)

        self.assertEqual(child["session"]["round_number"], 2)
        self.assertEqual(child["session"]["parent_session_id"], session_id)
        self.assertEqual(child["session"]["refinement_prompt"], "shorter and warmer")
        self.assertEqual(len(results), 8)
        self.assertIn("Rosie", brief.liked_examples)
        self.assertIn("Juniper", brief.rejected_examples)

    def test_refine_route_renders_round_two(self):
        session_id = self._seed_round_one()
        response = self.client.post(
            "/refine",
            data={"session_id": session_id, "instruction": "shorter"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Round 2", body)
        self.assertNotIn("Get finalists", body)
        self.assertIn("Ready for a fresh list?", body)
        self.assertIn("Generate New List", body)
        self.assertIn("Hazel", body)

    def test_progress_refine_redirects_to_saved_results_page(self):
        session_id = self._seed_round_one()
        response = self.client.post(
            "/refine",
            data={"session_id": session_id, "instruction": "shorter"},
            headers={"X-NamEngine-Progress": "1"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/results/session/", response.headers["Location"])
        follow = self.client.get(response.headers["Location"])
        body = follow.get_data(as_text=True)
        self.assertEqual(follow.status_code, 200)
        self.assertIn("Round 2", body)
        self.assertIn("Generate New List", body)

    def test_results_page_has_bottom_generate_new_list_action(self):
        session_id = self._seed_round_one()
        response = self.client.get("/pet/results?species=Dog&personality=Gentle&style=Warm")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="bottom-next-panel"', body)
        self.assertIn("Ready for a fresh list?", body)
        self.assertIn("Generate New List", body)
        self.assertIn(f'name="session_id" value="{session_id}"', body)
        self.assertIn('action="/refine"', body)
        self.assertIn('data-min-reactions="3"', body)
        self.assertIn("Ready to generate the next list.", body)
        self.assertNotIn("data-refine-submit disabled", body)

    def test_results_page_disables_generate_new_list_until_three_reactions(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        response = self.client.get(f"/pet/results?{query.decode('utf-8')}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-min-reactions="3"', body)
        self.assertIn('data-reaction-total="0"', body)
        self.assertIn("data-refine-submit disabled", body)
        self.assertIn("React to 3 more names before generating the next list.", body)

    def test_refine_route_requires_three_reactions(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        save_reaction(build_reaction(session_id, "pet-2", "no"))

        response = self.client.post(
            "/refine",
            data={"session_id": session_id, "instruction": "shorter"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("React to 1 more name before generating the next list.", body)
        self.assertIn("Generate New List", body)
        self.assertNotIn("Round 2", body)

    def test_round_three_returns_finalists(self):
        session_id = self._seed_round_one()
        round_two_id, _, _ = refine_session(session_id, PET, instruction="shorter")
        save_reaction(build_reaction(round_two_id, "pet-1", "love"))

        round_three_id, _, results = refine_session(round_two_id, PET, instruction="finalists")
        round_three = get_session_snapshot(round_three_id)

        self.assertEqual(round_three["session"]["round_number"], 3)
        self.assertEqual(round_three["session"]["parent_session_id"], round_two_id)
        self.assertEqual(len(results), 6)

    def test_one_more_round_after_finalists_returns_new_names(self):
        session_id = self._seed_round_one()
        round_two_id, _, _ = refine_session(session_id, PET, instruction="shorter")
        round_three_id, _, finalists = refine_session(round_two_id, PET, instruction="finalists")
        for index, _ in enumerate(finalists, start=1):
            save_reaction(build_reaction(round_three_id, f"pet-{index}", "no"))

        round_four_id, _, extra_results = refine_session(round_three_id, PET, instruction="")
        round_four = get_session_snapshot(round_four_id)

        finalist_names = {result.name for result in finalists}
        extra_names = {result.name for result in extra_results}
        self.assertEqual(round_four["session"]["round_number"], 4)
        self.assertNotEqual(round_four_id, f"{round_three_id}-r4")
        self.assertEqual(len(extra_results), 6)
        self.assertFalse(finalist_names & extra_names)

    def test_baby_refinement_does_not_repeat_any_prior_round_names(self):
        session_id = self._seed_baby_round_one()
        round_one = get_session_snapshot(session_id)
        round_one_names = {row["name"] for row in round_one["results"]}

        round_two_id, _, round_two_results = refine_session(
            session_id,
            BABY,
            instruction="fresh but still classic",
        )
        for index, _ in enumerate(round_two_results, start=1):
            save_reaction(build_reaction(round_two_id, f"baby-{index}", "maybe"))

        round_three_id, _, round_three_results = refine_session(
            round_two_id,
            BABY,
            instruction="expand the horizon",
        )
        round_two_names = {result.name for result in round_two_results}
        round_three_names = {result.name for result in round_three_results}
        round_three = get_session_snapshot(round_three_id)

        self.assertEqual(round_three["session"]["round_number"], 3)
        self.assertEqual(len(round_three_results), 6)
        self.assertFalse(round_three_names & round_one_names)
        self.assertFalse(round_three_names & round_two_names)

    def test_baby_girl_refinement_excludes_masculine_fallback_names(self):
        session_id = self._seed_baby_round_one()
        round_two_id, _, round_two_results = refine_session(
            session_id,
            BABY,
            instruction="fresh but still classic",
        )
        for index, _ in enumerate(round_two_results, start=1):
            save_reaction(build_reaction(round_two_id, f"baby-{index}", "maybe"))

        _, _, round_three_results = refine_session(
            round_two_id,
            BABY,
            instruction="expand the horizon",
        )
        result_names = {result.name for result in round_two_results + round_three_results}

        self.assertNotIn("Arthur", result_names)
        self.assertFalse(
            result_names
            & {"Arthur", "Felix", "Graham", "Hugo", "Miles", "Jonah", "Silas", "Theo"}
        )

    def test_refine_route_rejects_missing_session(self):
        response = self.client.post("/refine", data={"session_id": "missing"})

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
