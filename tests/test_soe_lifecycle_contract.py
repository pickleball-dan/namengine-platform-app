import os
import shutil
import tempfile
import unittest

from access_helpers import csrf_token, unlock_beta_access
from app import _signed_beta_access_token, beta_unlock_cookie_name, create_app
from namengine.core import build_reaction, get_session_snapshot, save_reaction
from namengine.magic_links import create_magic_link
from namengine.verticals import BABY


def _session_id_from_body(body: str) -> str:
    marker = 'data-session-id="'
    start = body.index(marker) + len(marker)
    end = body.index('"', start)
    return body[start:end]


class SOELifecycleContractTest(unittest.TestCase):
    def setUp(self):
        self._previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self._previous_openai_key = os.environ.get("OPENAI_API_KEY")
        self._tmp = tempfile.mkdtemp()
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self._tmp, "lifecycle.sqlite3")
        os.environ["OPENAI_API_KEY"] = ""
        self.client = create_app().test_client()

    def tearDown(self):
        self.client = None
        if self._previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self._previous_db_path
        if self._previous_openai_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self._previous_openai_key
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _seed_baby_round_one(self) -> str:
        response = self.client.get("/baby/results?gender=Girl&style=Classic&sound=Soft")
        self.assertEqual(response.status_code, 200)
        return _session_id_from_body(response.get_data(as_text=True))

    def _react_for_refinement(self, session_id: str) -> None:
        snapshot = get_session_snapshot(session_id)
        self.assertIsNotNone(snapshot)
        for index, row in enumerate(snapshot["results"][:3]):
            value = ("love", "maybe", "no")[index]
            save_reaction(build_reaction(session_id, row["id"], value))

    def _post_refine(self, session_id: str, instruction: str):
        self._react_for_refinement(session_id)
        return self.client.post(
            "/refine",
            data={
                "session_id": session_id,
                "instruction": instruction,
                "csrf_token": csrf_token(self.client),
            },
        )

    def _create_paid_baby_round_four(self) -> tuple[str, str, str, str]:
        round_one_id = self._seed_baby_round_one()
        unlock_beta_access(self.client, "baby")

        round_two_response = self._post_refine(round_one_id, "warmer")
        self.assertEqual(round_two_response.status_code, 200)
        round_two_id = _session_id_from_body(round_two_response.get_data(as_text=True))

        round_three_response = self._post_refine(round_two_id, "bolder")
        self.assertEqual(round_three_response.status_code, 200)
        round_three_id = _session_id_from_body(round_three_response.get_data(as_text=True))

        round_four_response = self._post_refine(round_three_id, "final stretch")
        self.assertEqual(round_four_response.status_code, 200)
        round_four_body = round_four_response.get_data(as_text=True)
        round_four_id = _session_id_from_body(round_four_body)
        self.assertIn("Curated finish", round_four_body)
        self.assertIn("Round 4", round_four_body)
        return round_one_id, round_two_id, round_three_id, round_four_id

    def test_baby_rounds_one_through_three_allow_refinement_and_round_four_is_terminal(self):
        round_one_id, round_two_id, round_three_id, round_four_id = self._create_paid_baby_round_four()

        self.assertEqual(get_session_snapshot(round_one_id)["session"]["round_number"], 1)
        self.assertEqual(get_session_snapshot(round_two_id)["session"]["round_number"], 2)
        self.assertEqual(get_session_snapshot(round_three_id)["session"]["round_number"], 3)
        self.assertEqual(get_session_snapshot(round_four_id)["session"]["round_number"], 4)

        response = self._post_refine(round_four_id, "one more")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Curated finish", body)
        self.assertIn("naming journey is complete", body)
        self.assertNotIn("Round 5", body)

    def test_baby_terminal_round_allows_love_only_and_keeps_choose_compare_share_available(self):
        _round_one_id, _round_two_id, _round_three_id, round_four_id = self._create_paid_baby_round_four()
        snapshot = get_session_snapshot(round_four_id)
        first_result = snapshot["results"][0]
        second_result = snapshot["results"][1]

        page = self.client.get(f"/results/session/{round_four_id}")
        body = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn('data-reaction-value="love"', body)
        self.assertNotIn('data-reaction-value="no"', body)
        self.assertNotIn('action="/refine"', body)
        self.assertIn(f"/compare/{round_four_id}", body)
        self.assertIn('action="/choose"', body)
        self.assertIn('data-save-progress-form', body)

        love = self.client.post(
            "/api/react",
            json={
                "csrf_token": csrf_token(self.client),
                "session_id": round_four_id,
                "result_id": first_result["id"],
                "value": "love",
            },
        )
        no = self.client.post(
            "/api/react",
            json={
                "csrf_token": csrf_token(self.client),
                "session_id": round_four_id,
                "result_id": second_result["id"],
                "value": "no",
            },
        )

        self.assertEqual(love.status_code, 201)
        self.assertEqual(no.status_code, 400)
        self.assertEqual(no.get_json()["error"], "final_decision_reactions_closed")

        compare = self.client.get(f"/compare/{round_four_id}")
        self.assertEqual(compare.status_code, 200)
        self.assertIn("Compare All Your Loved Names", compare.get_data(as_text=True))

        chosen = self.client.post(
            "/choose",
            data={
                "session_id": round_four_id,
                "result_id": first_result["id"],
                "csrf_token": csrf_token(self.client),
            },
            follow_redirects=False,
        )
        self.assertEqual(chosen.status_code, 302)
        self.assertIn("/chosen/", chosen.headers["Location"])

    def test_baby_terminal_state_blocks_edit_review_intake_and_paid_session_reuse_generation(self):
        round_one_id, _round_two_id, _round_three_id, round_four_id = self._create_paid_baby_round_four()
        # Pin the paid entitlement to the original journey, as checkout does.
        self.client.set_cookie(beta_unlock_cookie_name(BABY), _signed_beta_access_token(BABY, round_one_id))

        edit = self.client.get("/baby?gender=Girl&style=Classic&sound=Soft&edit=style", follow_redirects=False)
        feelings = self.client.get("/baby/feelings?gender=Girl&style=Classic&sound=Soft", follow_redirects=False)
        new_results = self.client.get("/baby/results?gender=Boy&style=Bold&sound=Crisp", follow_redirects=False)
        review_get = self.client.get("/baby/review", follow_redirects=False)
        review_post = self.client.post(
            "/baby/review",
            data={"gender": "Boy", "style": "Modern", "sound": "Bold"},
            follow_redirects=False,
        )

        expected_location = f"/results/session/{round_four_id}"
        self.assertEqual(edit.status_code, 302)
        self.assertEqual(edit.headers["Location"], expected_location)
        self.assertEqual(feelings.status_code, 302)
        self.assertEqual(feelings.headers["Location"], expected_location)
        self.assertEqual(new_results.status_code, 302)
        self.assertEqual(new_results.headers["Location"], expected_location)
        self.assertEqual(review_get.status_code, 404)
        self.assertEqual(review_post.status_code, 404)
        self.assertIsNone(get_session_snapshot("baby-new-terminal-escape"))

    def test_magic_link_resume_does_not_bypass_terminal_generation_rules(self):
        _round_one_id, _round_two_id, _round_three_id, round_four_id = self._create_paid_baby_round_four()
        token = create_magic_link(
            email="test@example.com",
            vertical="baby",
            session_id=round_four_id,
            session_state={"session_id": round_four_id, "vertical": "baby"},
        )

        fresh = create_app().test_client()
        resumed = fresh.get(f"/continue/{token}", follow_redirects=False)
        self.assertEqual(resumed.status_code, 302)
        self.assertEqual(resumed.headers["Location"], f"/results/session/{round_four_id}")

        terminal = fresh.get(f"/results/session/{round_four_id}", follow_redirects=False)
        self.assertEqual(terminal.status_code, 200)
        csrf_page = fresh.get("/baby")
        self.assertEqual(csrf_page.status_code, 200)
        blocked_refine = fresh.post(
            "/refine",
            data={
                "session_id": round_four_id,
                "instruction": "again",
                "csrf_token": csrf_token(fresh),
            },
        )
        new_generation = fresh.get("/baby/results?gender=Boy&style=Bold&sound=Crisp", follow_redirects=False)

        self.assertEqual(blocked_refine.status_code, 400)
        self.assertIn("naming journey is complete", blocked_refine.get_data(as_text=True))
        self.assertEqual(new_generation.status_code, 302)
        self.assertIn("/baby/access?return_session=", new_generation.headers["Location"])


if __name__ == "__main__":
    unittest.main()
