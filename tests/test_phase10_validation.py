import os
import tempfile
import unittest
from dataclasses import replace

from app import create_app, make_session_id
from namengine.core import (
    build_brief,
    generate_names,
    get_session_snapshot,
    get_validation_results,
    save_session,
    validate_result,
)
from namengine.core.validation import (
    ValidationModuleError,
    filter_results_for_brief,
    registered_validation_modules,
    validation_modules_for,
)
from namengine.core.schemas import NameResult, ValidationStatus
from namengine.core.generation import slugify
from namengine.verticals import BABY, BOAT, BUSINESS, PET


class PhaseTenValidationTest(unittest.TestCase):
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

    def test_pet_validation_returns_decision_checks(self):
        brief = build_brief(PET, {"species": "Dog", "avoid": "Milo"})
        result = NameResult(id="pet-1", name="Milo", slug=slugify("Milo"))

        validation = validate_result(PET, brief, result)

        self.assertEqual(
            {item.module for item in validation},
            {"pet_callability", "pet_sound_clarity", "avoid_match"},
        )
        avoid = next(item for item in validation if item.module == "avoid_match")
        self.assertEqual(avoid.status, ValidationStatus.FAIL)

    def test_declared_validation_modules_dispatch_in_order(self):
        cases = (
            (
                PET,
                {"pet_type": "Dog", "style": "Warm", "vibe": "Playful"},
                "Milo",
                ("pet_callability", "pet_sound_clarity"),
            ),
            (
                BABY,
                {"gender": "Girl", "style": "Classic", "sound": "Soft"},
                "Clara",
                (
                    "baby_gender_direction",
                    "baby_pronunciation",
                    "baby_initials",
                    "baby_popularity",
                ),
            ),
            (
                BUSINESS,
                {"business_description": "AI ops platform", "audience": "B2B", "style": "Clear"},
                "Gridline",
                (
                    "business_domain",
                    "business_category_fit",
                    "business_similarity",
                ),
            ),
            (
                BOAT,
                {
                    "boat_type": "Sailboat",
                    "use": "Weekend adventures",
                    "vibe": "Adventurous",
                    "style": "Traditional nautical",
                },
                "Harbor Star",
                ("boat_radio_clarity", "boat_tradition_fit", "boat_length"),
            ),
        )

        for vertical, inputs, name, expected_modules in cases:
            with self.subTest(vertical=vertical.slug):
                brief = build_brief(vertical, inputs)
                result = NameResult(id=f"{vertical.slug}-1", name=name, slug=slugify(name))

                validation = validate_result(vertical, brief, result)

                self.assertEqual(tuple(item.module for item in validation), expected_modules)

    def test_active_validation_modules_are_registered(self):
        registered = registered_validation_modules()

        for vertical in (BABY, PET, BUSINESS, BOAT):
            with self.subTest(vertical=vertical.slug):
                self.assertEqual(
                    tuple(module for module in validation_modules_for(vertical) if module not in registered),
                    (),
                )

    def test_baby_gender_direction_runtime_validator_always_runs_first(self):
        brief = build_brief(BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        result = NameResult(id="baby-1", name="Clara", slug=slugify("Clara"))

        validation = validate_result(BABY, brief, result)

        self.assertEqual(validation[0].module, "baby_gender_direction")
        self.assertEqual(validation[0].status, ValidationStatus.PASS)

    def test_avoid_match_remains_conditional_common_validation(self):
        cases = (
            (PET, {"pet_type": "Dog", "avoid": "Milo"}, "Milo"),
            (BABY, {"gender": "Girl", "avoid": "Clara"}, "Clara"),
            (BUSINESS, {"business_description": "AI ops", "avoid": "Gridline"}, "Gridline"),
            (BOAT, {"boat_type": "Sailboat", "avoid": "Harbor Star"}, "Harbor Star"),
        )

        for vertical, inputs, name in cases:
            with self.subTest(vertical=vertical.slug):
                brief = build_brief(vertical, inputs)
                result = NameResult(id=f"{vertical.slug}-avoid", name=name, slug=slugify(name))

                validation = validate_result(vertical, brief, result)

                avoid = next(item for item in validation if item.module == "avoid_match")
                self.assertEqual(avoid.status, ValidationStatus.FAIL)

        brief = build_brief(PET, {"pet_type": "Dog"})
        result = NameResult(id="pet-no-avoid", name="Milo", slug=slugify("Milo"))
        self.assertNotIn(
            "avoid_match",
            {item.module for item in validate_result(PET, brief, result)},
        )

    def test_unknown_validation_module_fails_explicitly(self):
        candidate = replace(PET, validation_modules=("pet_callability", "missing_validator"))
        brief = build_brief(candidate, {"pet_type": "Dog"})
        result = NameResult(id="pet-unknown", name="Milo", slug=slugify("Milo"))

        with self.assertRaisesRegex(
            ValidationModuleError,
            "Validation module is not registered: missing_validator",
        ):
            validate_result(candidate, brief, result)

    def test_generation_applies_validation_pipeline(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)

        self.assertEqual(len(results[0].validation), 2)
        self.assertIn("pet_callability", results[0].scores)
        self.assertNotIn("avoid_match", results[0].scores)

    def test_save_session_persists_validation_results(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)

        save_session("pet-session", "pet", brief, results)
        validation_rows = get_validation_results("pet-session", "pet-1")
        snapshot = get_session_snapshot("pet-session")

        self.assertEqual(len(validation_rows), 2)
        self.assertEqual(validation_rows[0]["session_id"], "pet-session")
        self.assertEqual(len(snapshot["validation_results"]), 16)

    def test_results_page_renders_validation(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        response = self.client.get(f"/pet/results?{query.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Validation", body)
        self.assertIn("Callability", body)
        self.assertNotIn("Avoid list", body)

    def test_results_page_renders_avoid_validation_only_when_user_supplies_avoid_terms(self):
        response = self.client.get("/pet/results?species=Dog&personality=Gentle&style=Warm&avoid=Milo")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Avoid list", body)
        self.assertIn("Does not match the avoid list.", body)
        self.assertNotIn(
            "This name matches something the user asked to avoid.",
            body,
        )

    def test_validation_table_survives_refined_session_ids(self):
        query = b"pet_type=Dog&vibe=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        rows = get_validation_results(session_id)

        self.assertEqual(len(rows), 16)

    def test_baby_girl_validation_filters_masculine_name(self):
        brief = build_brief(BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        results = [
            NameResult(id="baby-1", name="Arthur", slug=slugify("Arthur")),
            NameResult(id="baby-2", name="Eloise", slug=slugify("Eloise")),
        ]

        filtered = filter_results_for_brief(BABY, brief, results)

        self.assertEqual([result.name for result in filtered], ["Eloise"])


if __name__ == "__main__":
    unittest.main()
