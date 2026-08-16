import json
import os
import tempfile
import unittest
from pathlib import Path

from access_helpers import csrf_token, unlock_beta_access
from app import _query_string_from_mapping, _sanitize_intake_source, create_app, make_session_id
from namengine.core import build_brief, get_chosen_snapshot, get_session_snapshot
from namengine.verticals import PET


class PhaseEighteenPetLegacyParityTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_ai_verticals = os.environ.get("NAMENGINE_AI_PRIMARY_VERTICALS")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "none"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_ai_verticals is None:
            os.environ.pop("NAMENGINE_AI_PRIMARY_VERTICALS", None)
        else:
            os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = self.previous_ai_verticals
        self.tempdir.cleanup()

    def _session_id_for_query(self, vertical, query: bytes, *, session_vertical: str | None = None) -> str:
        source = dict(pair.split("=", 1) for pair in query.decode("utf-8").split("&"))
        source = {key: value.replace("+", " ") for key, value in source.items()}
        sanitized = _sanitize_intake_source(vertical, source)
        return make_session_id(session_vertical or vertical.slug, _query_string_from_mapping(sanitized).encode("utf-8"))

    def test_pet_uses_approved_active_graphic_assets(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("images/namengine-pets.svg", body)
        self.assertNotIn("images/namengine-pets-icon.svg", body)
        self.assertNotIn("images/pet/namengine-pet-logo-transparent.png", body)
        self.assertIn("images/pet/namengine-pet-share-current.png", body)
        self.assertIn("vertical-page-logo", body)

    def test_pet_intake_collects_portrait_details(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="pet_breed"', body)
        self.assertIn('name="pet_color"', body)
        self.assertIn('name="pet_details"', body)
        self.assertIn("Size, markings, backstory", body)
        self.assertIn('class="pet-choice-list"', body)
        self.assertIn('data-choice-target="pet_type"', body)
        self.assertIn('data-choice-value="Dog"', body)
        self.assertIn('data-choice-target="pet_life_stage"', body)
        self.assertIn('data-choice-value="Young"', body)
        self.assertIn('data-choice-value="Mature"', body)
        self.assertIn('name="pet_life_stage"', body)
        self.assertIn("Young or mature?", body)
        self.assertIn('class="pet-native-control"', body)
        self.assertIn('data-other-select="pet_type_other"', body)
        self.assertIn('name="pet_type_other"', body)
        self.assertNotIn('<select', body)

    def test_pet_intake_question_contract_is_locked_for_underlayment_migration(self):
        contract = [
            {
                "id": question.id,
                "label": question.label,
                "kind": question.kind,
                "required": question.required,
                "choices": question.choices,
                "placeholder": question.placeholder,
                "help_text": question.help_text,
                "section": question.section,
            }
            for question in PET.intake_questions
        ]

        self.assertEqual(
            contract,
            [
                {"id": "pet_type", "label": "Who's joining the family?", "kind": "text", "required": True, "choices": ("Dog", "Cat", "Horse", "Bird", "Rabbit", "Reptile", "Other"), "placeholder": "", "help_text": "", "section": "About your pet"},
                {"id": "pet_color", "label": "Color / markings", "kind": "text", "required": True, "choices": (), "placeholder": "Honey, black and white, brindle, gray tabby...", "help_text": "Required because we use this for the generated pet portrait.", "section": "About your pet"},
                {"id": "pet_life_stage", "label": "Young or mature?", "kind": "text", "required": True, "choices": ("Young", "Mature"), "placeholder": "", "help_text": "", "section": "About your pet"},
                {"id": "pet_gender", "label": "Gender", "kind": "text", "required": False, "choices": ("Male", "Female", "Neutral"), "placeholder": "", "help_text": "", "section": "About your pet"},
                {"id": "pet_breed", "label": "Breed / mix", "kind": "text", "required": False, "choices": (), "placeholder": "Golden retriever, tabby, mixed breed...", "help_text": "", "section": "About your pet"},
                {"id": "pet_details", "label": "Any other details that should shape the name or portrait?", "kind": "textarea", "required": False, "choices": (), "placeholder": "Size, markings, backstory, quirks, anything visually important...", "help_text": "", "section": "About your pet"},
                {"id": "vibe", "label": "What personality should the name capture?", "kind": "text", "required": True, "choices": ("Playful", "Loyal", "Elegant", "Brave", "Curious", "Gentle", "Mischievous", "Regal", "Adventurous", "Quirky", "Sweet", "Tough"), "placeholder": "", "help_text": "", "section": "Fit and feeling"},
                {"id": "style", "label": "What overall style feels closest?", "kind": "text", "required": True, "choices": ("Classic", "Modern", "Soft and romantic", "Strong and tailored", "Uncommon but usable"), "placeholder": "", "help_text": "", "section": "Name style"},
                {"id": "familiarity_preference", "label": "How familiar or surprising should the name feel?", "kind": "text", "required": False, "choices": ("Familiar", "Balanced", "Distinctive", "Very original"), "placeholder": "", "help_text": "This replaces the separate adventurous, timeless, distinctive, and familiarity questions.", "section": "Name style"},
                {"id": "cultural_context", "label": "Name inspiration", "kind": "text", "required": False, "choices": ("Nature", "Mythology", "Human names", "Food & drink", "Literature", "Movies & TV", "Music", "Geography", "Vintage", "Pop culture"), "placeholder": "", "help_text": "", "section": "Fit and feeling"},
                {"id": "pronunciation_importance", "label": "How easy should it be to call?", "kind": "text", "required": False, "choices": ("Very important", "Helpful but not absolute", "Open to slight friction"), "placeholder": "", "help_text": "", "section": "Fit and feeling"},
                {"id": "avoid", "label": "Any names, words, or vibes to avoid?", "kind": "text", "required": False, "choices": (), "placeholder": "Names, sounds, themes, associations, or anything that feels wrong...", "help_text": "", "section": "Fit and feeling"},
            ],
        )

    def test_pet_legacy_species_and_personality_aliases_still_build_current_brief(self):
        brief = build_brief(PET, {"species": "Cat", "personality": "Quiet", "style": "Classic"})

        self.assertEqual(brief.inputs["pet_type"], "Cat")
        self.assertEqual(brief.inputs["species"], "Cat")
        self.assertEqual(brief.inputs["vibe"], "Quiet")
        self.assertEqual(brief.inputs["personality"], "Quiet")

    def test_pet_original_mode_exists_and_generates_original_results(self):
        response = self.client.get("/pet/original")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Original Pet Name Studio", body)
        self.assertIn("Letter to begin the name", body)
        self.assertIn('name="pet_breed"', body)
        self.assertIn('name="pet_color"', body)
        self.assertIn('name="pet_details"', body)
        self.assertIn('class="pet-choice-list"', body)
        self.assertIn('data-choice-target="pet_type"', body)
        self.assertIn('data-choice-target="pet_life_stage"', body)
        self.assertIn('data-choice-value="Young"', body)
        self.assertIn('data-choice-value="Mature"', body)
        self.assertIn('data-other-select="pet_type_other"', body)
        self.assertIn('name="pet_type_other"', body)
        self.assertIn('name="pet_life_stage"', body)
        self.assertIn("Young or mature?", body)
        self.assertNotIn('<select', body)
        self.assertIn("Create original pet names", body)

        results = self.client.get(
            "/pet/original/results?pet_type=Dog&pet_breed=Whippet&pet_color=Blue+gray"
            "&pet_life_stage=Mature&style=Modern&vibe=Playful&starting_letter=L"
        )
        results_body = results.get_data(as_text=True)

        self.assertEqual(results.status_code, 200)
        self.assertIn("Original pet names shaped from your life", results_body)
        self.assertIn("Lumo", results_body)

    def test_other_pet_type_custom_value_is_used_for_results(self):
        response = self.client.get(
            "/pet/results?pet_type=Other&pet_type_other=Goat&style=Classic&vibe=Playful"
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("<dt>Pet</dt>", body)
        self.assertIn("<dd>Goat</dd>", body)
        self.assertNotIn("<dd>Other</dd>", body)

    def test_original_other_pet_type_redirects_with_custom_value(self):
        response = self.client.post(
            "/pet/original/results",
            data={
                "pet_type": "Other",
                "pet_type_other": "Goat",
                "style": "Modern",
                "vibe": "Playful",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("pet_type=Goat", response.headers["Location"])
        self.assertNotIn("pet_type_other", response.headers["Location"])

    def test_results_have_share_route_and_reaction_images(self):
        response = self.client.get("/pet/results?pet_type=Dog&style=Classic&vibe=Playful")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("/share/pet-", body)
        self.assertIn("images/reactions/love.jpg", body)
        self.assertNotIn("images/reactions/maybe.jpg", body)
        self.assertIn("images/reactions/no.jpg", body)
        self.assertIn('data-reaction-value="love"', body)
        self.assertIn('data-reaction-value="no"', body)
        self.assertNotIn('data-reaction-value="maybe"', body)

    def test_pet_results_route_keeps_quality_metadata_internal_and_pet_markup_clean(self):
        query = (
            b"pet_type=Dog&pet_breed=Whippet&pet_color=Blue+gray&pet_life_stage=Mature"
            b"&style=Modern&vibe=Gentle&pronunciation_importance=Very+important"
            b"&familiarity_preference=A+little+less+common"
            b"&timeless_vs_distinctive=Mostly+distinctive"
            b"&partner_alignment=human-name+but+not+too+serious&avoid=Spot"
        )
        session_id = self._session_id_for_query(PET, query)

        response = self.client.get(f"/pet/results?{query.decode('utf-8')}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vertical-pet", body)
        self.assertIn("result-tags", body)
        self.assertNotIn("baby-result-tags", body)
        self.assertNotIn("quality_score_version", body)
        self.assertNotIn("pet-quality-score-v1", body)
        self.assertNotIn("namengine-pet-quality-v1", body)
        self.assertIn("dog", body.lower())
        self.assertIn("call", body.lower())
        self.assertIn("Whippet", body)
        self.assertIn("Blue gray", body)
        self.assertIn("Gentle", body)

        snapshot = get_session_snapshot(session_id)
        self.assertTrue(snapshot)
        first = json.loads(snapshot["results"][0]["result_json"])
        self.assertEqual(first["metadata"]["prompt_version"], "namengine-pet-quality-v1")
        self.assertEqual(first["metadata"]["quality_score_version"], "pet-quality-score-v1")
        self.assertIn("callability", first["metadata"]["quality_scores"])
        self.assertIn("personality_match", first["metadata"]["quality_scores"])
        self.assertIn("this pet", first["why_this_name"].lower())
        self.assertIn("everyday", first["fit_note"].lower())
        self.assertNotIn("dog name", first["why_this_name"].lower())

    def test_pet_detail_share_and_chosen_flow_keep_quality_metadata_internal(self):
        query = (
            b"pet_type=Dog&pet_breed=Whippet&pet_color=Blue+gray&pet_life_stage=Mature"
            b"&style=Modern&vibe=Gentle&pronunciation_importance=Very+important"
            b"&familiarity_preference=A+little+less+common"
            b"&timeless_vs_distinctive=Mostly+distinctive"
            b"&partner_alignment=human-name+but+not+too+serious&avoid=Spot"
        )
        session_id = self._session_id_for_query(PET, query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        snapshot = get_session_snapshot(session_id)
        first = json.loads(snapshot["results"][0]["result_json"])
        result_id = first["id"]
        name = first["name"]
        unlock_beta_access(self.client, "pet")

        detail = self.client.get(f"/pet/name/{session_id}/{result_id}")
        share = self.client.get(f"/share/{session_id}")
        choose = self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": result_id, "csrf_token": csrf_token(self.client)},
            follow_redirects=False,
        )
        chosen_id = get_session_snapshot(session_id)["chosen_names"][0]["id"]
        chosen = self.client.get(f"/chosen/{chosen_id}")

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(share.status_code, 200)
        self.assertEqual(choose.status_code, 302)
        self.assertIn(f"/chosen/{chosen_id}", choose.headers["Location"])
        self.assertEqual(chosen.status_code, 200)

        for response in (detail, share, chosen):
            body = response.get_data(as_text=True)
            with self.subTest(route=response.request.path):
                self.assertIn(name, body)
                if response.request.path != f"/chosen/{chosen_id}":
                    self.assertIn("Whippet", body)
                    self.assertIn("Mature", body)
                self.assertIn("pet", body.lower())
                self.assertIn("Blue gray", body)
                self.assertNotIn("quality_score_version", body)
                self.assertNotIn("pet-quality-score-v1", body)
                self.assertNotIn("namengine-pet-quality-v1", body)
                self.assertNotIn("baby-result-tags", body)
                self.assertNotIn("baby-decision-section", body)
                self.assertNotIn("Baby blanket", body)

        chosen_snapshot = get_chosen_snapshot(chosen_id)
        self.assertEqual(chosen_snapshot["chosen"]["name"], name)
        self.assertEqual(chosen_snapshot["chosen"]["vertical"], "pet")
        self.assertEqual(
            chosen_snapshot["chosen"]["metadata"]["pet_portrait"]["details"],
            {"breed": "Whippet", "color": "Blue gray", "details": "Mature"},
        )
        persisted_result = json.loads(get_session_snapshot(session_id)["results"][0]["result_json"])
        self.assertEqual(persisted_result["metadata"]["prompt_version"], "namengine-pet-quality-v1")
        self.assertEqual(persisted_result["metadata"]["quality_score_version"], "pet-quality-score-v1")

    def test_pet_compare_and_refine_loop_keeps_quality_metadata_internal(self):
        query = (
            b"pet_type=Dog&pet_breed=Whippet&pet_color=Blue+gray&pet_life_stage=Mature"
            b"&style=Modern&vibe=Gentle&pronunciation_importance=Very+important"
            b"&familiarity_preference=A+little+less+common"
            b"&timeless_vs_distinctive=Mostly+distinctive"
            b"&partner_alignment=human-name+but+not+too+serious&avoid=Spot"
        )
        session_id = self._session_id_for_query(PET, query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        parent_snapshot = get_session_snapshot(session_id)
        parent_results = [json.loads(row["result_json"]) for row in parent_snapshot["results"]]
        unlock_beta_access(self.client, "pet")

        for result, value in zip(parent_results[:3], ("love", "love", "no")):
            response = self.client.post(
                "/api/react",
                json={"session_id": session_id, "result_id": result["id"], "value": value, "csrf_token": csrf_token(self.client)},
            )
            self.assertEqual(response.status_code, 201)

        compare = self.client.get(f"/compare/{session_id}")
        compare_body = compare.get_data(as_text=True)

        self.assertEqual(compare.status_code, 200)
        self.assertIn("Compare Favorites", compare_body)
        self.assertIn("Taste profile", compare_body)
        self.assertIn("Callability", compare_body)
        self.assertIn("Warmth", compare_body)
        self.assertIn(parent_results[0]["name"], compare_body)
        self.assertIn(parent_results[1]["name"], compare_body)
        self.assertNotIn("quality_score_version", compare_body)
        self.assertNotIn("pet-quality-score-v1", compare_body)
        self.assertNotIn("namengine-pet-quality-v1", compare_body)
        self.assertNotIn("baby-result-tags", compare_body)
        self.assertNotIn("baby-decision-section", compare_body)
        self.assertNotIn("Baby blanket", compare_body)

        refined = self.client.post(
            "/refine",
            data={"session_id": session_id, "instruction": "warmer but still easy to call", "csrf_token": csrf_token(self.client)},
        )
        refined_body = refined.get_data(as_text=True)
        child_session_id = f"{session_id}-r2"
        child_snapshot = get_session_snapshot(child_session_id)
        child_results = [json.loads(row["result_json"]) for row in child_snapshot["results"]]

        self.assertEqual(refined.status_code, 200)
        self.assertEqual(child_snapshot["session"]["round_number"], 2)
        self.assertEqual(child_snapshot["session"]["parent_session_id"], session_id)
        self.assertIn("Round 2", refined_body)
        self.assertIn("pet", refined_body.lower())
        self.assertIn("Sound test", refined_body)
        self.assertIn("Whippet", refined_body)
        self.assertIn("Blue gray", refined_body)
        self.assertNotIn("quality_score_version", refined_body)
        self.assertNotIn("pet-quality-score-v1", refined_body)
        self.assertNotIn("namengine-pet-quality-v1", refined_body)
        self.assertNotIn("baby-result-tags", refined_body)
        self.assertNotIn("baby-decision-section", refined_body)
        self.assertNotIn("Baby blanket", refined_body)
        self.assertFalse({item["name"] for item in parent_results} & {item["name"] for item in child_results})
        for result in child_results:
            with self.subTest(name=result["name"]):
                self.assertEqual(result["metadata"]["prompt_version"], "namengine-pet-quality-v1")
                self.assertEqual(result["metadata"]["quality_score_version"], "pet-quality-score-v1")
                self.assertIn("callability", result["metadata"]["quality_scores"])
                self.assertIn("personality_match", result["metadata"]["quality_scores"])
                self.assertIn("this pet", result["why_this_name"].lower())
                self.assertIn("everyday", result["fit_note"].lower())
                self.assertNotIn("dog name", result["why_this_name"].lower())

    def test_shared_shortlist_route_renders_saved_session(self):
        query = b"pet_type=Dog&style=Classic&vibe=Playful"
        session_id = self._session_id_for_query(PET, query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        unlock_beta_access(self.client, "pet")

        response = self.client.get(f"/share/{session_id}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Shared NamEngine Pet list", body)
        self.assertIn("Start your own list", body)
        self.assertIn("Open detail", body)

    def test_original_shared_shortlist_route_renders_saved_session(self):
        query = (
            b"pet_type=Dog&pet_breed=Whippet&pet_color=Blue+gray"
            b"&pet_life_stage=Mature&style=Modern&vibe=Playful&starting_letter=L"
        )
        session_id = self._session_id_for_query(PET, query, session_vertical="pet-original")
        self.client.get(f"/pet/original/results?{query.decode('utf-8')}")
        unlock_beta_access(self.client, "pet")

        response = self.client.get(f"/share/{session_id}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Shared NamEngine Pet list", body)
        self.assertIn("Lumo", body)

    def test_missing_shared_shortlist_route_has_recovery_page(self):
        response = self.client.get("/share/pet-original-missing")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 410)
        self.assertIn("This saved list is no longer available.", body)
        self.assertIn("Start a new pet list", body)
        self.assertNotIn("Not Found", body)

    def test_feedback_route_renders_and_accepts_submission(self):
        response = self.client.get("/feedback")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Feedback", response.get_data(as_text=True))

        submitted = self.client.post("/feedback", data={"overall_rating": "Promising"})
        self.assertEqual(submitted.status_code, 200)
        self.assertIn("Feedback received", submitted.get_data(as_text=True))
        feedback_path = Path(self.db_path).parent / "feedback.jsonl"
        self.assertTrue(feedback_path.is_file())
        self.assertIn("Promising", feedback_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
