import json
import os
import tempfile
import unittest
from urllib.parse import urlencode

from app import create_app, make_session_id
from namengine.core import (
    build_brief,
    build_reaction,
    get_session_snapshot,
    save_reaction,
    save_session,
    validate_result,
)
from namengine.core.generation import generate_names, slugify
from namengine.core.schemas import NameResult, ValidationStatus
from namengine.core.validation import (
    BABY_BOY_INCOMPATIBLE_NAMES,
    BABY_GIRL_INCOMPATIBLE_NAMES,
    filter_results_for_brief,
)
from namengine.verticals import BABY


class PhaseNineteenBabySmokeValidationTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_openai_key = os.environ.get("OPENAI_API_KEY")
        self.previous_disable_baby_images = os.environ.get("NAMENGINE_DISABLE_BABY_IMAGES")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        os.environ["NAMENGINE_DISABLE_BABY_IMAGES"] = "1"
        os.environ.pop("OPENAI_API_KEY", None)
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
        if self.previous_disable_baby_images is None:
            os.environ.pop("NAMENGINE_DISABLE_BABY_IMAGES", None)
        else:
            os.environ["NAMENGINE_DISABLE_BABY_IMAGES"] = self.previous_disable_baby_images
        self.tempdir.cleanup()

    def test_baby_girl_route_smoke_refines_without_repeats_or_invalid_names(self):
        query = urlencode(
            {
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
                "avoid": "Eloise, Maya",
                "family_context": "Surname Parker",
            }
        )
        session_id = make_session_id("baby", query.encode("utf-8"))

        response = self.client.get(f"/baby/results?{query}")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Baby names shaped from your taste", body)
        self.assertIn("Gender direction", body)
        self.assertIn("Compare favorites", body)

        round_one_names = self._assert_clean_baby_snapshot(
            session_id,
            gender="girl",
            expected_count=8,
            forbidden={"eloise", "maya"},
        )

        self._react_to_first_three(session_id)
        round_two_response = self.client.post(
            "/refine",
            data={
                "session_id": session_id,
                "instruction": "broaden the horizon but keep it soft",
            },
        )
        self.assertEqual(round_two_response.status_code, 200)
        self.assertIn("Round 2", round_two_response.get_data(as_text=True))
        round_two_id = f"{session_id}-r2"
        round_two_names = self._assert_clean_baby_snapshot(
            round_two_id,
            gender="girl",
            expected_count=8,
            forbidden={"eloise", "maya"} | round_one_names,
        )

        self._react_to_first_three(round_two_id)
        round_three_response = self.client.post(
            "/refine",
            data={
                "session_id": round_two_id,
                "instruction": "finalists with no repeats",
            },
        )
        self.assertEqual(round_three_response.status_code, 200)
        self.assertIn("Round 3", round_three_response.get_data(as_text=True))
        round_three_id = f"{round_two_id}-r3"
        round_three_names = self._assert_clean_baby_snapshot(
            round_three_id,
            gender="girl",
            expected_count=6,
            forbidden={"eloise", "maya"} | round_one_names | round_two_names,
        )

        compare = self.client.get(f"/compare/{round_three_id}")
        self.assertEqual(compare.status_code, 200)
        self.assertIn("Compare", compare.get_data(as_text=True))

        chosen = self.client.post(
            "/choose",
            data={"session_id": round_three_id, "result_id": "baby-1"},
            follow_redirects=True,
        )
        self.assertEqual(chosen.status_code, 200)
        chosen_body = chosen.get_data(as_text=True)
        self.assertIn("Baby blanket keepsake embroidered with", chosen_body)
        self.assertTrue(any(name.title() in chosen_body for name in round_three_names))

    def test_baby_gender_direction_validation_fails_wrong_lane_names(self):
        girl_brief = build_brief(BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        boy_brief = build_brief(BABY, {"gender": "Boy", "style": "Classic", "sound": "Strong"})
        neutral_brief = build_brief(BABY, {"gender": "Gender-neutral", "style": "Modern"})

        arthur_validation = validate_result(
            BABY,
            girl_brief,
            NameResult(id="baby-1", name="Arthur", slug=slugify("Arthur")),
        )
        ada_validation = validate_result(
            BABY,
            boy_brief,
            NameResult(id="baby-2", name="Ada", slug=slugify("Ada")),
        )
        neutral_validation = validate_result(
            BABY,
            neutral_brief,
            NameResult(id="baby-3", name="Arthur", slug=slugify("Arthur")),
        )

        self.assertEqual(
            self._validation_status(arthur_validation, "baby_gender_direction"),
            ValidationStatus.FAIL,
        )
        self.assertEqual(
            self._validation_status(ada_validation, "baby_gender_direction"),
            ValidationStatus.FAIL,
        )
        self.assertEqual(
            self._validation_status(neutral_validation, "baby_gender_direction"),
            ValidationStatus.PASS,
        )

    def test_baby_filter_removes_wrong_gender_and_exact_avoid_names(self):
        brief = build_brief(
            BABY,
            {
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
                "avoid": "Eloise",
            },
        )
        results = [
            NameResult(id="baby-1", name="Arthur", slug=slugify("Arthur")),
            NameResult(id="baby-2", name="Eloise", slug=slugify("Eloise")),
            NameResult(id="baby-3", name="Clara", slug=slugify("Clara")),
        ]

        filtered = filter_results_for_brief(BABY, brief, results)

        self.assertEqual([result.name for result in filtered], ["Clara"])

    def test_baby_results_route_regenerates_stale_cached_names(self):
        query = urlencode(
            {
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
                "avoid": "Eloise, Maya",
            }
        )
        session_id = make_session_id("baby", query.encode("utf-8"))
        brief = build_brief(
            BABY,
            {
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
                "avoid": "Eloise, Maya",
            },
        )
        stale_results = [
            NameResult(id="baby-1", name="Eloise", slug=slugify("Eloise")),
            NameResult(id="baby-2", name="Arthur", slug=slugify("Arthur")),
            NameResult(id="baby-3", name="Maya", slug=slugify("Maya")),
        ]
        save_session(session_id, "baby", brief, stale_results)

        response = self.client.get(f"/baby/results?{query}")

        self.assertEqual(response.status_code, 200)
        refreshed = get_session_snapshot(session_id)
        refreshed_names = {self._clean(row["name"]) for row in refreshed["results"]}
        self.assertNotIn("eloise", refreshed_names)
        self.assertNotIn("maya", refreshed_names)
        self.assertNotIn("arthur", refreshed_names)
        self.assertEqual(len(refreshed_names), 8)
        self.assertEqual(
            sum(
                1
                for row in refreshed["validation_results"]
                if row["module"] == "baby_gender_direction"
            ),
            8,
        )

    def test_baby_fallback_pool_validates_girl_and_boy_across_rounds(self):
        scenarios = (
            ("Girl", "Soft", BABY_GIRL_INCOMPATIBLE_NAMES),
            ("Boy", "Strong", BABY_BOY_INCOMPATIBLE_NAMES),
        )
        for gender, sound, incompatible in scenarios:
            brief = build_brief(
                BABY,
                {
                    "gender": gender,
                    "style": "Classic",
                    "sound": sound,
                    "avoid": "Eloise, Arthur",
                },
            )
            previous_names: list[str] = []
            for round_number in range(1, 5):
                with self.subTest(gender=gender, round_number=round_number):
                    results = generate_names(
                        BABY,
                        brief,
                        round_number=round_number,
                        previous_names=previous_names,
                        use_ai=False,
                    )
                    names = [result.name for result in results]
                    clean_names = {self._clean(name) for name in names}
                    self.assertEqual(len(names), 6 if round_number >= 3 else 8)
                    self.assertEqual(len(clean_names), len(names))
                    self.assertFalse(clean_names & incompatible)
                    self.assertNotIn("eloise", clean_names)
                    self.assertNotIn("arthur", clean_names)
                    self.assertFalse(clean_names & {self._clean(name) for name in previous_names})
                    previous_names.extend(names)

    def _assert_clean_baby_snapshot(
        self,
        session_id: str,
        *,
        gender: str,
        expected_count: int,
        forbidden: set[str],
    ) -> set[str]:
        snapshot = get_session_snapshot(session_id)
        self.assertIsNotNone(snapshot)
        rows = snapshot["results"]
        names = {self._clean(row["name"]) for row in rows}
        incompatible = (
            BABY_GIRL_INCOMPATIBLE_NAMES
            if gender == "girl"
            else BABY_BOY_INCOMPATIBLE_NAMES
        )

        self.assertEqual(len(rows), expected_count)
        self.assertEqual(len(names), expected_count)
        self.assertFalse(names & incompatible)
        self.assertFalse(names & forbidden)

        validation_by_result = {}
        for row in snapshot["validation_results"]:
            validation_by_result.setdefault(row["result_id"], set()).add(row["module"])
            payload = json.loads(row["validation_json"])
            if row["module"] == "baby_gender_direction":
                self.assertEqual(payload["status"], "pass")
        for row in rows:
            self.assertIn("baby_gender_direction", validation_by_result.get(row["id"], set()))

        return names

    def _react_to_first_three(self, session_id: str) -> None:
        snapshot = get_session_snapshot(session_id)
        self.assertIsNotNone(snapshot)
        for row, value in zip(snapshot["results"][:3], ("love", "maybe", "no")):
            save_reaction(build_reaction(session_id, row["id"], value))

    def _validation_status(self, validation, module: str) -> ValidationStatus:
        return next(item.status for item in validation if item.module == module)

    def _clean(self, name: str) -> str:
        return "".join(character for character in name.lower() if character.isalpha())


if __name__ == "__main__":
    unittest.main()
