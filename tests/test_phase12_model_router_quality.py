import json
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
import namengine.core.model_router as model_router
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
from namengine.verticals import BABY, BOAT, BUSINESS, PET
from namengine.core.schemas import NameResult, ProviderResult


def _baby_openai_name(
    name: str,
    *,
    index: int,
    candidate_pool: list[str] | None = None,
    rejected: list[str] | None = None,
) -> NameResult:
    metadata = {"source": "openai", "provider": "openai"}
    if candidate_pool is not None:
        metadata["candidate_pool"] = [{"name": item} for item in candidate_pool]
    if rejected is not None:
        metadata["rejected_candidates"] = [{"name": item} for item in rejected]
    return NameResult(
        id=f"baby-{index}",
        name=name,
        slug=name.lower(),
        pronunciation=name,
        tagline=f"{name} feels warm and vivid.",
        origin="Test origin",
        meaning="A test baby name.",
        why_this_name=f"{name} fits the brief with a bolder but wearable sound.",
        fit_note=f"{name} is strongest for a warm, distinctive baby-name direction.",
        risks=["Low practical risk; still test initials and family fit."],
        tags=["warm", "distinctive"],
        scores={"fit": 0.9, "usability": 0.9, "distinctiveness": 0.8},
        metadata=metadata,
    )


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

    def test_round_count_policy_matches_four_round_product_policy(self):
        self.assertEqual(model_router._count_for_round(BABY, 1), 8)
        self.assertEqual(model_router._count_for_round(BABY, 2), 8)
        self.assertEqual(model_router._count_for_round(BABY, 3), 8)
        self.assertEqual(model_router._count_for_round(BABY, 4), 6)

    def test_previous_fill_policy_disables_reuse_for_all_active_verticals(self):
        expected = {
            BABY.slug: {1: False, 2: False, 3: False, 4: False, 5: False},
            PET.slug: {1: False, 2: False, 3: False, 4: False, 5: False},
            BUSINESS.slug: {1: False, 2: False, 3: False, 4: False, 5: False},
            BOAT.slug: {1: False, 2: False, 3: False, 4: False, 5: False},
        }

        for vertical in (BABY, PET, BUSINESS, BOAT):
            for round_number, allow_previous_fill in expected[vertical.slug].items():
                with self.subTest(vertical=vertical.slug, round_number=round_number):
                    self.assertEqual(
                        model_router._allow_previous_fill_for_round(vertical, round_number),
                        allow_previous_fill,
                    )

    def test_generate_with_router_never_reuses_prior_round_names_in_later_rounds(self):
        vertical_inputs = (
            (BABY, {"gender": "Girl", "style": "Warm", "sound": "Soft"}),
            (PET, {"pet_type": "Dog", "style": "Warm", "vibe": "Playful"}),
            (
                BUSINESS,
                {
                    "business_description": "Operations support studio",
                    "audience": "B2B buyers",
                    "style": "Clear and credible",
                },
            ),
            (
                BOAT,
                {
                    "boat_type": "Sailboat",
                    "use": "Weekend adventures",
                    "vibe": "Adventurous",
                    "style": "Traditional nautical",
                },
            ),
        )

        for vertical, inputs in vertical_inputs:
            brief = build_brief(vertical, inputs)
            previous_name = f"Prior {vertical.slug.title()}"
            fresh_name = f"Fresh {vertical.slug.title()}"

            def fallback_provider(*_args, **_kwargs):
                return [
                    NameResult(
                        id=f"{vertical.slug}-prior",
                        name=previous_name,
                        slug=f"prior-{vertical.slug}",
                        scores={"callability": 0.99, "warmth": 0.99, "distinctiveness": 0.99},
                    ),
                    NameResult(
                        id=f"{vertical.slug}-fresh",
                        name=fresh_name,
                        slug=f"fresh-{vertical.slug}",
                        scores={"callability": 0.7, "warmth": 0.7, "distinctiveness": 0.7},
                    ),
                ]

            for round_number in (2, 3, 4):
                with self.subTest(vertical=vertical.slug, round_number=round_number):
                    with patch("namengine.core.model_router._fallback_provider", side_effect=fallback_provider):
                        names = generate_with_router(
                            vertical=vertical,
                            brief=brief,
                            round_number=round_number,
                            previous_names=[previous_name],
                            providers=[ModelProvider.FALLBACK],
                            count=4,
                        )

                    returned_names = [item.name for item in names]
                    self.assertIn(fresh_name, returned_names)
                    self.assertNotIn(previous_name, returned_names)

    def test_provider_routing_keeps_openai_claude_and_fallback_distinct(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        openai_name = NameResult(id="openai-1", name="Aster", slug="aster")
        claude_name = NameResult(id="claude-1", name="Harbor", slug="harbor")

        with patch("namengine.core.model_router._openai_provider", return_value=[openai_name]) as openai, patch(
            "namengine.core.model_router._claude_provider",
            return_value=[claude_name],
        ) as claude:
            provider_results = route_generation(
                vertical=PET,
                brief=brief,
                round_number=1,
                taste_profile=None,
                previous_names=[],
                providers=[ModelProvider.OPENAI, ModelProvider.CLAUDE, ModelProvider.FALLBACK],
            )

        self.assertEqual([result.provider for result in provider_results], [
            ModelProvider.OPENAI,
            ModelProvider.CLAUDE,
            ModelProvider.FALLBACK,
        ])
        self.assertEqual(provider_results[0].names[0].name, "Aster")
        self.assertEqual(provider_results[1].names[0].name, "Harbor")
        self.assertNotEqual(provider_results[2].provider, ModelProvider.CLAUDE)
        openai.assert_called_once()
        claude.assert_called_once()

    def test_baby_round_three_shortfall_uses_openai_top_up_not_fallback(self):
        brief = build_brief(BABY, {"gender": "Girl", "style": "Warm", "sound": "Soft"})
        brief.notes = "bolder"
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
        first_pass = [
            _baby_openai_name("Aveline", index=1, candidate_pool=["Aveline", "Cora"], rejected=["Nova"]),
            _baby_openai_name("Elowen", index=2),
            _baby_openai_name("Seren", index=3),
            _baby_openai_name("Maris", index=4),
        ]
        top_up = [
            _baby_openai_name("Liora", index=5),
            _baby_openai_name("Anouk", index=6),
            _baby_openai_name("Vera", index=7),
            _baby_openai_name("Zara", index=8),
        ]
        calls = []

        def openai_provider(vertical, brief_arg, round_number, taste_profile, previous):
            calls.append(
                {
                    "round_number": round_number,
                    "notes": brief_arg.notes,
                    "previous_names": list(previous),
                }
            )
            return first_pass if len(calls) == 1 else top_up

        with patch("namengine.core.model_router._openai_provider", side_effect=openai_provider), patch(
            "namengine.core.model_router._fallback_provider"
        ) as fallback, patch("namengine.core.model_router._claude_provider") as claude:
            with self.assertLogs("namengine.core.model_router", level="WARNING") as captured:
                names = generate_with_router(
                    vertical=BABY,
                    brief=brief,
                    round_number=3,
                    previous_names=previous_names,
                    providers=[ModelProvider.OPENAI],
                    fallback_on_provider_error=True,
                )

        self.assertEqual(len(names), 8)
        self.assertFalse({item.name.lower() for item in names} & {item.lower() for item in previous_names})
        self.assertTrue(all(item.metadata["provider"] == "openai" for item in names))
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["notes"], "bolder")
        self.assertEqual(calls[1]["notes"], "bolder")
        self.assertIn("Aveline", calls[1]["previous_names"])
        self.assertIn("Cora", calls[1]["previous_names"])
        self.assertIn("Nova", calls[1]["previous_names"])
        fallback.assert_not_called()
        claude.assert_not_called()
        self.assertIn("trying AI top-up", "\n".join(captured.output))

    def test_baby_round_four_shortfall_raises_without_fallback_after_top_up_fails(self):
        brief = build_brief(BABY, {"gender": "Girl", "style": "Warm", "sound": "Soft"})
        first_pass = [_baby_openai_name("Aveline", index=1), _baby_openai_name("Elowen", index=2)]
        top_up = [_baby_openai_name("Seren", index=3)]

        with patch(
            "namengine.core.model_router._openai_provider",
            side_effect=[first_pass, top_up],
        ), patch("namengine.core.model_router._fallback_provider") as fallback, patch(
            "namengine.core.model_router._claude_provider"
        ) as claude:
            with self.assertRaisesRegex(AIGenerationError, "required 6"):
                generate_with_router(
                    vertical=BABY,
                    brief=brief,
                    round_number=4,
                    previous_names=["Maya", "Nora"],
                    providers=[ModelProvider.OPENAI],
                    fallback_on_provider_error=True,
                )

        fallback.assert_not_called()
        claude.assert_not_called()

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
        self.assertGreater(run.average_score, 0.9)
        self.assertEqual(run.avoided_name_hits, 0)
        self.assertEqual(run.duplicate_count, 0)
        self.assertTrue(run.selected)
        for candidate in run.selected:
            with self.subTest(name=candidate.result.name):
                self.assertEqual(candidate.result.metadata["prompt_version"], "namengine-pet-quality-v1")
                self.assertEqual(candidate.result.metadata["quality_score_version"], "pet-quality-score-v1")
                self.assertIn("callability", candidate.result.metadata["quality_scores"])
                self.assertIn("personality_match", candidate.result.metadata["quality_scores"])
                self.assertIn("this pet", candidate.result.why_this_name.lower())
                self.assertIn("everyday", candidate.result.fit_note.lower())
                self.assertNotIn("dog name", candidate.result.why_this_name.lower())

    def test_all_pet_quality_fixtures_keep_adapter_metadata_and_avoid_hits_out(self):
        fixture = Path(__file__).parent / "fixtures" / "pet_quality_briefs.json"
        quality_briefs = load_quality_briefs(fixture)

        runs = [
            run_quality_brief(brief, PET, providers=[ModelProvider.FALLBACK])
            for brief in quality_briefs
        ]

        self.assertEqual({run.brief_id for run in runs}, {"pet-gentle-dog", "pet-quiet-cat"})
        for run in runs:
            with self.subTest(brief=run.brief_id):
                self.assertGreater(run.average_score, 0.9)
                self.assertEqual(run.avoided_name_hits, 0)
                self.assertEqual(run.duplicate_count, 0)
                selected_names = {candidate.result.name.lower() for candidate in run.selected}
                fixture_row = next(item for item in quality_briefs if item.id == run.brief_id)
                self.assertFalse(selected_names & {name.lower() for name in fixture_row.must_avoid})
                for candidate in run.selected:
                    self.assertEqual(candidate.result.metadata["prompt_version"], "namengine-pet-quality-v1")
                    self.assertEqual(candidate.result.metadata["quality_score_version"], "pet-quality-score-v1")

    def test_pet_adapter_ranks_callable_pet_name_above_awkward_fantasy_shape(self):
        brief = build_brief(
            PET,
            {
                "pet_type": "Dog",
                "style": "Warm and easy to call",
                "vibe": "Gentle and loyal",
                "pronunciation_importance": "Very important",
            },
        )
        callable_name = NameResult(
            id="candidate-milo",
            name="Milo",
            slug="milo",
            pronunciation="MY-loh",
            tagline="Warm, clear, and easy to call.",
            meaning="A friendly everyday pet name.",
            why_this_name="Milo fits this pet because it is warm, familiar, and easy to say.",
            fit_note="Best for a pet whose name should feel natural in everyday use.",
            risks=["Low practical risk; still test it out loud."],
            tags=["callable", "warm", "gentle"],
            scores={"callability": 0.95, "warmth": 0.9, "distinctiveness": 0.58},
        )
        awkward_name = NameResult(
            id="candidate-xyqtharion",
            name="Xyqtharion",
            slug="xyqtharion",
            pronunciation="zick-THAIR-ee-on",
            tagline="Invented and dramatic.",
            meaning="A fantasy-shaped invented option.",
            why_this_name="Xyqtharion is unusual but creates friction for a gentle pet.",
            fit_note="Harder to use quickly in everyday moments.",
            risks=["Hard to pronounce and likely to be confusing out loud."],
            tags=["invented", "fantasy"],
            scores={"callability": 0.25, "warmth": 0.35, "distinctiveness": 0.95},
        )
        provider_results = [
            ProviderResult(provider=ModelProvider.FALLBACK, names=[awkward_name, callable_name])
        ]

        candidates = score_provider_results(provider_results, brief=brief, vertical=PET)
        selected = select_best_candidates(candidates, count=2, vertical_slug=PET.slug)

        self.assertEqual([candidate.result.name for candidate in selected], ["Milo", "Xyqtharion"])
        self.assertGreater(callable_name.metadata["quality_score"], awkward_name.metadata["quality_score"])
        self.assertLess(awkward_name.metadata["quality_scores"]["callability"], 0.5)

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
