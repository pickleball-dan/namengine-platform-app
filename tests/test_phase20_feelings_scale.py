import unittest

from app import create_app
from namengine.core.briefs import build_brief
from namengine.core.generation import generate_names
from namengine.verticals import get_vertical


class PhaseTwentyFeelingsScaleTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_feelings_scale_routes_render_for_sectioned_verticals(self):
        cases = {
            "baby": "baby",
            "pet": "dog",
            "business": "building",
            "product": "product",
        }
        for slug, noun in cases.items():
            with self.subTest(slug=slug):
                response = self.client.get(f"/{slug}/feelings?pet_type=Dog&style=Classic&sound=Warm")
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                self.assertIn("Feelings Scale", body)
                self.assertIn("What do I feel strong about?", body)
                self.assertIn("Generate", body)
                self.assertIn("taste_strength_", body)
                self.assertIn(noun, body.lower())
                self.assertNotIn("Best first look", body)

    def test_character_without_sections_bypasses_feelings_scale(self):
        response = self.client.get("/character/feelings?genre=Fantasy")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/character/results", response.headers["Location"])

    def test_feelings_scale_restores_saved_priority_values(self):
        response = self.client.get(
            "/baby/feelings?gender=Girl&style=Classic&sound=Warm"
            "&taste_strength_about_your_baby=8"
            "&taste_strength_name_style=82"
            "&taste_strength_fit_and_feeling=10"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('name="taste_strength_about_your_baby" value="8"', body)
        self.assertIn('name="taste_strength_name_style" value="82"', body)
        self.assertIn('name="taste_strength_fit_and_feeling" value="10"', body)
        self.assertIn('data-progress-form', body)
        self.assertIn('method="post"', body)

    def test_feelings_scale_submits_hidden_strengths_to_results(self):
        query = (
            "gender=Girl&style=Classic&sound=Warm"
            "&taste_strength_about_your_baby=12"
            "&taste_strength_name_style=76"
            "&taste_strength_fit_and_feeling=12"
        )
        response = self.client.get(f"/baby/results?{query}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Baby names shaped from your taste", body)
        self.assertNotIn("taste_strength_name_style", body)

    def test_public_feelings_submit_redirects_to_clean_session_url(self):
        response = self.client.post(
            "/baby/results",
            data={
                "gender": "Boy",
                "family_context": "african american",
                "notes": "strong historical relevance",
                "discovery_style": "Unexpected finds",
                "style": "Classic",
                "timeless_vs_distinctive": "Strongly distinctive",
                "familiarity_preference": "Recognizable but not overused",
                "sound": "Strong",
                "cultural_context": "Family heritage",
                "taste_strength_about_your_baby": "34",
                "taste_strength_name_style": "33",
                "taste_strength_fit_and_feeling": "33",
            },
        )

        self.assertEqual(response.status_code, 302)
        location = response.headers["Location"]
        self.assertIn("/results/session/", location)
        self.assertNotIn("gender=", location)
        self.assertNotIn("taste_strength_", location)

        result_response = self.client.get(location)
        self.assertEqual(result_response.status_code, 200)
        body = result_response.get_data(as_text=True)
        self.assertIn("Baby names shaped from your taste", body)
        self.assertNotIn("taste_strength_name_style", body)

    def test_baby_fallback_changes_for_major_taste_changes(self):
        baby = get_vertical("baby")
        classic = build_brief(
            baby,
            {
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
                "family_context": "sister Clara",
                "notes": "warm gentle familiar",
            },
        )
        classic.inputs.update(
            {
                "taste_strength_about_your_baby": 15,
                "taste_strength_name_style": 75,
                "taste_strength_fit_and_feeling": 10,
            }
        )
        rare = build_brief(
            baby,
            {
                "gender": "Girl",
                "style": "Strong and tailored",
                "timeless_vs_distinctive": "Strongly distinctive",
                "sound": "Strong",
                "notes": "bold rare distinctive strong",
            },
        )
        rare.inputs.update(
            {
                "taste_strength_about_your_baby": 10,
                "taste_strength_name_style": 75,
                "taste_strength_fit_and_feeling": 15,
            }
        )

        classic_names = [result.name for result in generate_names(baby, classic, use_ai=False)[:8]]
        rare_names = [result.name for result in generate_names(baby, rare, use_ai=False)[:8]]

        self.assertNotEqual(classic_names[:3], rare_names[:3])
        self.assertGreaterEqual(len(set(classic_names) ^ set(rare_names)), 6)

    def test_pet_fallback_changes_by_pet_type(self):
        pet = get_vertical("pet")
        dog = build_brief(
            pet,
            {
                "pet_type": "Dog",
                "style": "Classic",
                "vibe": "Playful",
                "notes": "callable loyal friendly dog",
            },
        )
        dog.inputs.update(
            {
                "taste_strength_about_your_pet": 70,
                "taste_strength_name_style": 15,
                "taste_strength_fit_and_feeling": 15,
            }
        )
        cat = build_brief(
            pet,
            {
                "pet_type": "Cat",
                "style": "Uncommon but usable",
                "vibe": "Elegant",
                "notes": "elegant stylish cat",
            },
        )
        cat.inputs.update(
            {
                "taste_strength_about_your_pet": 70,
                "taste_strength_name_style": 15,
                "taste_strength_fit_and_feeling": 15,
            }
        )

        dog_names = [result.name for result in generate_names(pet, dog, use_ai=False)[:8]]
        cat_names = [result.name for result in generate_names(pet, cat, use_ai=False)[:8]]

        self.assertNotEqual(dog_names[:3], cat_names[:3])
        self.assertGreaterEqual(len(set(dog_names) ^ set(cat_names)), 6)


if __name__ == "__main__":
    unittest.main()
