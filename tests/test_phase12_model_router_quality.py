import json
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from namengine.core import (
    AIGenerationError,
    ModelProvider,
    build_brief,
    generate_names,
    generate_with_router,
    load_quality_briefs,
    route_generation,
    run_quality_brief,
    score_name_result,
    score_provider_results,
    select_best_candidates,
    get_session_snapshot,
    save_session,
    summarize_quality_runs,
)
from namengine.verticals import BABY, PET
from namengine.core.schemas import NameResult


class PhaseTwelveModelRouterQualityTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        self.app = create_app()
        self.app.testing = True

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def test_route_generation_reports_openai_error_and_fallback_success(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})

        with patch.dict(os.environ, {}, clear=True):
            provider_results = route_generation(
                vertical=PET,
                brief=brief,
                round_number=1,
                taste_profile=None,
                previous_names=[],
                providers=[ModelProvider.OPENAI, ModelProvider.FALLBACK],
            )

        self.assertEqual(provider_results[0].provider, ModelProvider.OPENAI)
        self.assertEqual(provider_results[0].status, "error")
        self.assertEqual(provider_results[1].provider, ModelProvider.FALLBACK)
        self.assertEqual(provider_results[1].status, "ok")
        self.assertEqual(provider_results[1].names[0].metadata["source"], "phase3_fallback")
        self.assertEqual(len(provider_results[1].names), 8)

    def test_route_generation_logs_original_provider_exception_before_returning_error(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})

        def fail_with_chained_parse_error(*_args, **_kwargs):
            try:
                json.loads("not-json")
            except json.JSONDecodeError as exc:
                raise AIGenerationError("AI response was not valid JSON") from exc

        with patch(
            "namengine.core.model_router._provider_callable",
            return_value=fail_with_chained_parse_error,
        ), self.assertLogs("namengine.core.model_router", level="ERROR") as captured:
            provider_results = route_generation(
                vertical=PET,
                brief=brief,
                round_number=1,
                taste_profile=None,
                previous_names=[],
                providers=[ModelProvider.OPENAI],
            )

        self.assertEqual(provider_results[0].status, "error")
        self.assertEqual(provider_results[0].error, "AI response was not valid JSON")
        logs = "\n".join(captured.output)
        self.assertIn("provider=openai vertical=pet round=1", logs)
        self.assertIn("JSONDecodeError", logs)
        self.assertIn("AI response was not valid JSON", logs)

    def test_score_and_select_candidates_dedupe_previous_names(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        provider_results = route_generation(
            vertical=PET,
            brief=brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            providers=[ModelProvider.FALLBACK],
        )

        candidates = score_provider_results(provider_results)
        score, reasons = score_name_result(candidates[0].result, ModelProvider.FALLBACK)
        selected = select_best_candidates(candidates, count=3, previous_names=["Milo"])

        self.assertGreater(score, 0.6)
        self.assertIn("high callability", reasons)
        self.assertNotIn("Milo", [item.result.name for item in selected])
        self.assertEqual(len(selected), 3)

    def test_generate_with_router_returns_best_names(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})

        names = generate_with_router(
            vertical=PET,
            brief=brief,
            round_number=1,
            providers=[ModelProvider.FALLBACK],
            count=4,
        )

        self.assertEqual(len(names), 4)
        self.assertTrue(all(item.metadata["provider"] == "fallback" for item in names))

    def test_baby_round_three_falls_back_when_openai_selection_is_all_previous_names(self):
        brief = build_brief(BABY, {"gender": "Girl", "style": "Warm", "sound": "Soft"})
        previous_names = [
            "Maya",
            "Nora",
            "Amina",
            "Asha",
            "Ayana",
            "Hana",
            "Haru",
            "Imani",
            "Celia",
            "Eshe",
            "Rami",
            "Yuna",
            "Giovanni",
            "Lena",
            "Iris",
            "Ada",
        ]
        duplicate_openai = [
            NameResult(
                id="openai-duplicate-maya",
                name="Maya",
                slug="maya",
                why_this_name="Duplicate from an earlier round.",
                fit_note="Already seen.",
                scores={"fit": 0.9, "usability": 0.9, "distinctiveness": 0.7},
                metadata={"source": "openai"},
            ),
            NameResult(
                id="openai-duplicate-nora",
                name="Nora",
                slug="nora",
                why_this_name="Duplicate from an earlier round.",
                fit_note="Already seen.",
                scores={"fit": 0.9, "usability": 0.9, "distinctiveness": 0.7},
                metadata={"source": "openai"},
            ),
        ]

        with patch("namengine.core.model_router._openai_provider", return_value=duplicate_openai):
            with self.assertLogs("namengine.core.model_router", level="WARNING") as captured:
                names = generate_with_router(
                    vertical=BABY,
                    brief=brief,
                    round_number=3,
                    previous_names=previous_names,
                    providers=[ModelProvider.OPENAI],
                    fallback_on_provider_error=True,
                )

        self.assertEqual(len(names), 6)
        self.assertFalse({item.name.lower() for item in names} & {item.lower() for item in previous_names})
        self.assertTrue(all(item.metadata["provider"] == "fallback" for item in names))
        self.assertIn("Model selection shortfall", "\n".join(captured.output))

    def test_public_generate_names_uses_router(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})

        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            names = generate_names(PET, brief, use_ai=True)

        self.assertEqual(len(names), 8)
        self.assertTrue(all(item.metadata["provider"] == "fallback" for item in names))

    def test_mixed_provider_metadata_survives_final_selection_and_session_storage(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        openai_name = NameResult(
            id="mixed-openai",
            name="Aster",
            slug="aster",
            scores={"callability": 0.9, "warmth": 0.9, "distinctiveness": 0.8},
        )
        fallback_name = NameResult(
            id="mixed-fallback",
            name="Bramble",
            slug="bramble",
            scores={"callability": 0.9, "warmth": 0.9, "distinctiveness": 0.8},
        )

        with patch("namengine.core.model_router._openai_provider", return_value=[openai_name]), patch(
            "namengine.core.model_router._fallback_provider",
            return_value=[fallback_name],
        ):
            names = generate_with_router(
                vertical=PET,
                brief=brief,
                providers=[ModelProvider.OPENAI, ModelProvider.FALLBACK],
                count=2,
            )

        provider_by_name = {item.name: item.metadata["provider"] for item in names}
        self.assertEqual({"Aster": "openai", "Bramble": "fallback"}, provider_by_name)

        save_session("mixed-provider-session", PET.slug, brief, names)
        snapshot = get_session_snapshot("mixed-provider-session")
        stored_provider_by_name = {
            row["name"]: json.loads(row["result_json"])["metadata"]["provider"]
            for row in snapshot["results"]
        }
        self.assertEqual(provider_by_name, stored_provider_by_name)

    def test_quality_fixture_loads_and_runs(self):
        fixture = Path(__file__).parent / "fixtures" / "pet_quality_briefs.json"
        quality_briefs = load_quality_briefs(fixture)

        run = run_quality_brief(
            quality_briefs[0],
            PET,
            providers=[ModelProvider.FALLBACK],
        )

        self.assertEqual(run.brief_id, "pet-gentle-dog")
        self.assertGreater(run.average_score, 0.6)
        self.assertEqual(run.avoided_name_hits, 0)

    def test_quality_summary_reports_provider_status(self):
        fixture = Path(__file__).parent / "fixtures" / "pet_quality_briefs.json"
        quality_briefs = load_quality_briefs(fixture)
        runs = [
            run_quality_brief(brief, PET, providers=[ModelProvider.FALLBACK])
            for brief in quality_briefs
        ]

        summary = summarize_quality_runs(runs)

        self.assertEqual(summary["brief_count"], 2)
        self.assertEqual(summary["provider_status"]["fallback"]["ok"], 2)
        self.assertGreater(summary["average_score"], 0.6)


if __name__ == "__main__":
    unittest.main()
