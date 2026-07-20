import json
import os
import tempfile
import unittest
from dataclasses import asdict

from app import create_app
from namengine.core import (
    build_reaction,
    build_taste_profile,
    get_session_snapshot,
    save_reaction,
    save_session,
)
from namengine.core.ai_generation import (
    name_generation_response_format,
    parse_ai_generation_response,
)
from namengine.core.schemas import NameResult, NamingBrief


def rich_result(result_id: str, name: str, tags: list[str]) -> NameResult:
    return NameResult(
        id=result_id,
        name=name,
        slug=name.lower(),
        pronunciation=f"{name}-pronunciation",
        tagline=f"A concise impression of {name}",
        origin="Documented origin",
        meaning="Documented meaning",
        why_this_name="Legacy compatibility explanation.",
        fit_note="Legacy compatibility fit note.",
        recommendation_reason=(
            f"You selected Classic and asked for a name that works with the family surname. "
            f"{name} earned a place because its established form and stored sound evidence address both choices."
        ),
        matched_preferences=[
            {
                "preference": "Classic style",
                "evidence": "You selected Classic as the primary style direction.",
                "fit": f"{name} has an established form rather than a newly invented one.",
            }
        ],
        strongest_fit=f"{name} most directly answers the request for an established full name.",
        real_life_impression={
            "childhood": f"{name} can be spoken in full at home without shortening it.",
            "adulthood": f"The full form {name} remains available in adult introductions.",
            "overall": "The same full form works across both settings.",
        },
        tradeoffs=["The formal full form may invite nicknames chosen by other people."],
        comparison_position={
            "softer_than": ["Beatrice"],
            "stronger_than": [],
            "more_familiar_than": [],
            "more_distinctive_than": [],
        },
        nickname_considerations={
            "likely": [f"{name[:3]}"],
            "optional": [],
            "note": "The family can choose whether to introduce a short form.",
        },
        family_fit={
            "surname_or_context": "The supplied surname was considered in the recommendation.",
            "sound_note": "The first name ends before the surname begins, keeping the boundary audible.",
            "initials_note": "No initials claim is made without a complete middle-name choice.",
        },
        confidence_note="Style fit is supported by the intake; the emotional response remains personal.",
        risks=["Legacy risk should not replace the structured tradeoff."],
        tags=tags,
        scores={"callability": 0.75, "warmth": 0.7, "distinctiveness": 0.55},
    )


class BabyDecisionSupportTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_environment = {
            key: os.environ.get(key)
            for key in ("NAMENGINE_DB_PATH", "NAMENGINE_AI_PRIMARY_VERTICALS", "OPENAI_API_KEY")
        }
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "none"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        for key, value in self.previous_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tempdir.cleanup()

    def save_baby(self, session_id: str, results: list[NameResult], **inputs):
        brief = NamingBrief(vertical="baby", inputs=inputs or {"gender": "Girl", "style": "Classic"})
        save_session(session_id, "baby", brief, results)

    def test_baby_schema_is_compact_but_parser_preserves_structured_decision_fields(self):
        schema = name_generation_response_format("baby")["schema"]["properties"]["names"]["items"]
        for field in (
            "recommendation_reason", "matched_preferences", "strongest_fit",
            "real_life_impression", "tradeoffs", "comparison_position",
            "nickname_considerations", "family_fit", "confidence_note",
        ):
            self.assertNotIn(field, schema["required"])
            self.assertNotIn(field, schema["properties"])

        source = rich_result("baby-1", "Eleanor", ["Classic", "Substantial"])
        payload = {
            "names": [{key: value for key, value in asdict(source).items() if key not in {"id", "slug", "validation", "metadata"}}]
        }
        parsed = parse_ai_generation_response(json.dumps(payload), "baby")[0]
        self.assertEqual(parsed.recommendation_reason, source.recommendation_reason)
        self.assertEqual(parsed.matched_preferences, source.matched_preferences)
        self.assertEqual(parsed.family_fit, source.family_fit)
        self.assertEqual(parsed.comparison_position["softer_than"], ["Beatrice"])

        self.save_baby("baby-rich-storage", [parsed], gender="Girl", style="Classic")
        stored = json.loads(get_session_snapshot("baby-rich-storage")["results"][0]["result_json"])
        self.assertEqual(stored["real_life_impression"], source.real_life_impression)
        self.assertEqual(stored["nickname_considerations"], source.nickname_considerations)

    def test_first_round_without_reactions_hides_learning_and_comparisons(self):
        self.save_baby("baby-first-round", [rich_result("baby-1", "Eleanor", ["Classic"])], gender="Girl", style="Classic")
        body = self.client.get("/baby/name/baby-first-round/baby-1").get_data(as_text=True)
        self.assertIn("Why this made your list", body)
        self.assertNotIn("Compared with names you liked", body)
        self.assertNotIn("What NamEngine is learning", body)

    def test_rich_detail_uses_reactions_taste_and_grounded_comparisons(self):
        results = [
            rich_result("baby-1", "Eleanor", ["Classic", "Substantial"]),
            rich_result("baby-2", "Lillian", ["Classic", "Soft"]),
            rich_result("baby-3", "Beatrice", ["Classic", "Formal"]),
            rich_result("baby-4", "Nova", ["Modern", "Bright"]),
        ]
        self.save_baby(
            "baby-reacted",
            results,
            gender="Girl",
            style="Classic",
            family_context="A supplied family surname",
        )
        save_reaction(build_reaction("baby-reacted", "baby-2", "love"))
        save_reaction(build_reaction("baby-reacted", "baby-3", "love"))
        save_reaction(build_reaction("baby-reacted", "baby-4", "no"))
        build_taste_profile("baby-reacted")

        body = self.client.get("/baby/name/baby-reacted/baby-1").get_data(as_text=True)
        for text in (
            "Why this made your list",
            "How it may feel in real life",
            "Compared with names you liked",
            "Softer than Beatrice.",
            "Tradeoffs to consider",
            "What NamEngine is learning",
            "Classic recur most clearly",
            "Next decision",
        ):
            self.assertIn(text, body)
        self.assertNotIn("quality_score", body)
        self.assertNotIn("gpt-", body)

    def test_sparse_legacy_result_hides_generic_and_unsupported_sections(self):
        sparse = NameResult(
            id="baby-1",
            name="Legacy",
            slug="legacy",
            pronunciation="LEG-uh-see",
            tagline="A warm and elegant name",
            origin="",
            meaning="",
            why_this_name="This is a warm, timeless name that aligns with parental hopes.",
            fit_note="Matches the supplied brief.",
            risks=["Popularity may be increasing in some regions."],
            tags=["Classic"],
        )
        self.save_baby("baby-sparse", [sparse], gender="Girl", style="Modern")
        body = self.client.get("/baby/name/baby-sparse/baby-1").get_data(as_text=True)
        self.assertEqual(self.client.get("/baby/name/baby-sparse/baby-1").status_code, 200)
        self.assertNotIn("Why this made your list", body)
        self.assertNotIn("How it may feel in real life", body)
        self.assertNotIn("Tradeoffs to consider", body)
        self.assertNotIn("Popularity may be increasing", body)
        self.assertNotIn("Popularity snapshot", body)
        self.assertNotIn("placeholder", body.casefold())
        self.assertIn("Next decision", body)

    def test_family_context_and_accessible_actions_render_without_exposing_internals(self):
        self.save_baby(
            "baby-family-fit",
            [rich_result("baby-1", "Eleanor", ["Classic"])],
            gender="Girl",
            style="Classic",
            family_context="Supplied surname context",
        )
        body = self.client.get("/baby/name/baby-family-fit/baby-1").get_data(as_text=True)
        self.assertIn("Family fit", body)
        self.assertIn('aria-label="How does Eleanor feel?"', body)
        self.assertIn('aria-live="polite"', body)
        self.assertIn("Love this name", body)
        self.assertIn("Keep as a maybe", body)
        self.assertIn("Not for us", body)
        self.assertIn("<details", body)
        self.assertNotIn("engine_pipeline", body)
        self.assertNotIn("generation_id", body)

    def test_baby_maybe_reaction_works_while_pet_contract_is_unchanged(self):
        self.save_baby("baby-maybe", [rich_result("baby-1", "Eleanor", ["Classic"])])
        response = self.client.post(
            "/api/react",
            json={"session_id": "baby-maybe", "result_id": "baby-1", "value": "maybe"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["reaction"]["value"], "maybe")
        body = self.client.get("/baby/name/baby-maybe/baby-1").get_data(as_text=True)
        self.assertIn('class="is-selected" data-reaction-value="maybe"', body)

        pet = NameResult(id="pet-1", name="Milo", slug="milo")
        save_session("pet-no-maybe", "pet", NamingBrief(vertical="pet", inputs={"species": "Dog"}), [pet])
        rejected = self.client.post(
            "/api/react",
            json={"session_id": "pet-no-maybe", "result_id": "pet-1", "value": "maybe"},
        )
        self.assertEqual(rejected.status_code, 400)


if __name__ == "__main__":
    unittest.main()
