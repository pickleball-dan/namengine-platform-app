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

    def test_baby_fallback_respects_african_american_historical_heritage_signal(self):
        baby = get_vertical("baby")
        brief = build_brief(
            baby,
            {
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

        names = [result.name for result in generate_names(baby, brief, use_ai=False)[:8]]

        self.assertIn(names[0], {"Malcolm", "Langston", "Booker"})
        self.assertGreaterEqual(
            len({"Malcolm", "Langston", "Booker", "Thurgood", "Frederick", "Bayard"} & set(names[:6])),
            4,
        )
        self.assertNotIn("Arthur", names[:6])

    def test_baby_fallback_respects_italian_heritage_without_cross_contamination(self):
        baby = get_vertical("baby")
        brief = build_brief(
            baby,
            {
                "gender": "Boy",
                "family_context": "Italian heritage",
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

        names = [result.name for result in generate_names(baby, brief, use_ai=False)[:8]]

        self.assertIn(names[0], {"Dante", "Giovanni", "Leonardo", "Lorenzo", "Vittorio"})
        self.assertGreaterEqual(
            len({"Giovanni", "Leonardo", "Lorenzo", "Dante", "Marco", "Enzo", "Rocco", "Vittorio"} & set(names[:8])),
            6,
        )
        self.assertFalse({"Malcolm", "Langston", "Booker", "Thurgood", "Bayard"} & set(names[:6]))
        self.assertNotIn("Arthur", names[:6])

    def test_baby_fallback_respects_common_named_heritages(self):
        baby = get_vertical("baby")
        cases = {
            "Irish heritage": {"Cillian", "Ronan", "Declan", "Eamon", "Cormac", "Seamus", "Finnian"},
            "Scottish heritage": {"Duncan", "Lachlan", "Alistair", "Hamish", "Callum", "Ewan"},
            "Russian heritage": {"Lev", "Dmitri", "Mikhail", "Viktor", "Nikolai", "Ivan"},
            "Chinese heritage": {"Liang", "Jian", "Kai", "Jun", "Ming", "Wei"},
        }
        wrong_lane_names = {"Malcolm", "Langston", "Booker", "Thurgood", "Dante", "Vittorio", "Giovanni"}

        for family_context, expected_names in cases.items():
            with self.subTest(family_context=family_context):
                brief = build_brief(
                    baby,
                    {
                        "gender": "Boy",
                        "family_context": family_context,
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

                names = [result.name for result in generate_names(baby, brief, use_ai=False)[:8]]

                self.assertIn(names[0], expected_names)
                self.assertGreaterEqual(len(expected_names & set(names[:6])), 5)
                self.assertFalse((wrong_lane_names - expected_names) & set(names[:6]))
                self.assertNotIn("Arthur", names[:6])

    def test_baby_fallback_has_coverage_for_broad_heritage_requests(self):
        baby = get_vertical("baby")
        cases = {
            "African American heritage": {"Malcolm", "Langston", "Booker", "Thurgood", "Frederick", "Bayard"},
            "African heritage": {"Kwame", "Kofi", "Omari", "Idris", "Zuberi", "Amari"},
            "Arab Middle Eastern heritage": {"Idris", "Omar", "Samir", "Zayn", "Rami", "Tariq"},
            "Armenian heritage": {"Aram", "Levon", "Tigran", "Suren", "Hayk", "Ashot"},
            "Australian heritage": {"Banjo", "Darcy", "Jett", "Clancy", "Ned", "Lachie"},
            "Brazilian heritage": {"Rafael", "Thiago", "Mateus", "Caio", "Joao", "Lucas"},
            "Chinese heritage": {"Liang", "Jian", "Kai", "Jun", "Ming", "Wei"},
            "Danish heritage": {"Lars", "Anders", "Mikkel", "Niels", "Magnus", "Nils"},
            "Dutch heritage": {"Bram", "Sander", "Pieter", "Floris", "Daan", "Thijs"},
            "English heritage": {"Alfred", "Edmund", "Hugh", "Percy", "Rupert", "Winston"},
            "Filipino heritage": {"Andres", "Ramon", "Lito", "Bayan", "Jose", "Miguel"},
            "French heritage": {"Etienne", "Lucien", "Bastien", "Remy", "Marcel", "Pascal"},
            "German heritage": {"Otto", "Fritz", "Klaus", "Anselm", "Luther", "Heinrich"},
            "Greek heritage": {"Theo", "Nikos", "Dimitri", "Andreas", "Leander", "Stelios"},
            "Indian heritage": {"Aarav", "Rohan", "Arjun", "Dev", "Kiran", "Nikhil"},
            "Irish heritage": {"Cillian", "Ronan", "Declan", "Eamon", "Cormac", "Seamus"},
            "Italian heritage": {"Dante", "Vittorio", "Giovanni", "Leonardo", "Lorenzo", "Marco"},
            "Japanese heritage": {"Akio", "Hiro", "Kenji", "Ren", "Sora", "Haru"},
            "Jewish Ashkenazi Sephardic heritage": {"Ezra", "Ari", "Eitan", "Noam", "Asher", "Rafi"},
            "Korean heritage": {"Minjun", "Jiho", "Joon", "Dohyun", "Hyun", "Seojoon"},
            "Mexican heritage": {"Jose", "Mateo", "Santiago", "Emiliano", "Diego", "Alejandro"},
            "Native American Indigenous heritage": {"Dakota", "Yuma", "Takoda", "Mika", "Nodin", "Tahoma"},
            "Norwegian heritage": {"Lars", "Anders", "Magnus", "Sven", "Einar", "Nils"},
            "Persian Iranian heritage": {"Cyrus", "Darius", "Kian", "Arman", "Rostam", "Navid"},
            "Polish heritage": {"Marek", "Kazimir", "Tadeusz", "Lukasz", "Janek", "Piotr"},
            "Portuguese heritage": {"Rafael", "Thiago", "Mateus", "Caio", "Joao", "Lucas"},
            "Russian heritage": {"Lev", "Dmitri", "Mikhail", "Viktor", "Nikolai", "Ivan"},
            "Scottish heritage": {"Duncan", "Lachlan", "Alistair", "Hamish", "Callum", "Ewan"},
            "Spanish heritage": {"Rafael", "Andres", "Ramon", "Jose", "Miguel", "Mateo"},
            "Swedish heritage": {"Stellan", "Lars", "Anders", "Magnus", "Sven", "Nils"},
            "Turkish heritage": {"Emir", "Kerem", "Levent", "Arda", "Ozan", "Deniz"},
            "Ukrainian heritage": {"Taras", "Bohdan", "Mykola", "Ostap", "Danylo", "Levko"},
            "Vietnamese heritage": {"Minh", "An", "Bao", "Quang", "Duc", "Khoa"},
            "Welsh heritage": {"Idris", "Emrys", "Owain", "Cai", "Dylan", "Bryn"},
        }

        for family_context, expected_names in cases.items():
            with self.subTest(family_context=family_context):
                brief = build_brief(
                    baby,
                    {
                        "gender": "Boy",
                        "family_context": family_context,
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

                names = [result.name for result in generate_names(baby, brief, use_ai=False)[:6]]

                self.assertEqual(len(names), len(set(names)))
                self.assertGreaterEqual(len(expected_names & set(names)), 5)
                self.assertNotIn("Arthur", names)

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
