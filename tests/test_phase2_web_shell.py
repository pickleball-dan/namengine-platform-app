import unittest
from html.parser import HTMLParser

from app import create_app
from namengine.verticals import VERTICALS


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            self._current = {
                "href": attrs_dict.get("href", ""),
                "class": attrs_dict.get("class", ""),
                "text": "",
            }

    def handle_data(self, data):
        if self._current is not None:
            self._current["text"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self._current is not None:
            self._current["text"] = " ".join(self._current["text"].split())
            self.anchors.append(self._current)
            self._current = None


class PhaseTwoWebShellTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_home_lists_vertical_routes(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Finding the right name should start with what matters", body)
        self.assertIn("NamEngine learns your taste through a short conversation", body)
        self.assertIn("Name a baby", body)
        self.assertIn("What are you naming?", body)
        self.assertIn("Love", body)
        self.assertIn("No", body)
        self.assertIn("Unlock the list when the name matters.", body)
        self.assertNotIn("Free first round", body)
        self.assertNotIn("$0", body)
        self.assertNotIn("Love / No learning loop", body)
        self.assertNotIn("Maybe", body)
        self.assertNotIn("Like", body)
        self.assertNotIn("Find the name that feels right.", body)
        self.assertNotIn("The TASTE ENGINE", body)
        self.assertIn('href="/pet"', body)
        self.assertIn('href="/baby"', body)
        self.assertIn('href="/business"', body)
        self.assertNotIn('href="/character"', body)
        self.assertNotIn('href="/product"', body)

    def test_home_vertical_start_links_use_canonical_intake_routes(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        parser = AnchorParser()
        parser.feed(response.get_data(as_text=True))
        anchors_by_text = {}
        anchors_by_class = {}
        for anchor in parser.anchors:
            anchors_by_text.setdefault(anchor["text"], set()).add(anchor["href"])
            if anchor["class"]:
                anchors_by_class.setdefault(anchor["class"], set()).add(anchor["href"])

        self.assertEqual(anchors_by_text["Baby"], {"/baby"})
        self.assertEqual(anchors_by_text["Pet"], {"/pet"})
        self.assertEqual(anchors_by_text["Business"], {"/business"})
        self.assertEqual(anchors_by_class["landing-vertical-card baby"], {"/baby"})
        self.assertEqual(anchors_by_class["landing-vertical-card pet"], {"/pet"})
        self.assertEqual(anchors_by_class["landing-vertical-card business"], {"/business"})
        self.assertNotIn("Unlock Full Access", anchors_by_text)
        self.assertNotIn("Unlock Full Access", anchors_by_text)
        self.assertNotIn("Unlock Full Access", anchors_by_text)

    def test_pet_intake_renders_from_vertical_config(self):
        response = self.client.get("/pet")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("NamEngine Pet", body)
        self.assertIn("How familiar or surprising should the name feel?", body)
        self.assertIn("Name style", body)
        self.assertIn("Who&#39;s joining the family?", body)
        self.assertIn("About your pet", body)
        self.assertIn("What overall style feels closest?", body)
        self.assertIn("How easy should it be to call?", body)
        self.assertIn("What personality should the name capture?", body)
        self.assertIn("Fit and feeling", body)
        self.assertIn("Name inspiration", body)
        self.assertIn("Tell us about their personality", body)
        self.assertIn("Required", body)
        self.assertIn('data-choice-value="Dog"', body)
        self.assertIn('data-choice-value="Cat"', body)
        self.assertIn('data-choice-value="Balanced"', body)
        self.assertIn('data-choice-value="Very important"', body)
        self.assertIn('action="/pet/review"', body)
        self.assertIn('method="post"', body)
        self.assertIn('data-progress-form data-no-progress novalidate', body)
        self.assertIn("Review Direction", body)

    def test_review_lifecycle_modes_are_configured_for_active_verticals(self):
        self.assertEqual(VERTICALS["baby"].review_mode, "direct_generation")
        self.assertEqual(VERTICALS["pet"].review_mode, "direction_review")
        self.assertEqual(VERTICALS["business"].review_mode, "direction_review")
        self.assertEqual(VERTICALS["boat"].review_mode, "direct_generation")

    def test_intake_form_action_follows_configured_review_mode(self):
        expected_actions = {
            "baby": "/baby/results",
            "pet": "/pet/review",
            "business": "/business/review",
            "boat": "/boat/results",
        }

        for slug, expected_action in expected_actions.items():
            with self.subTest(slug=slug):
                response = self.client.get(f"/{slug}")

                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                self.assertIn(f'action="{expected_action}"', body)
                self.assertIn(f'data-intake-submit-url="{expected_action}"', body)
                if VERTICALS[slug].review_mode == "direction_review":
                    self.assertIn("Review Direction", body)
                    self.assertIn("data-no-progress", body)
                else:
                    self.assertNotIn(f'action="/{slug}/review"', body)

    def test_server_review_route_follows_configured_review_mode(self):
        for slug in ("baby", "boat"):
            with self.subTest(slug=slug):
                response = self.client.post(f"/{slug}/review", data={})

                self.assertEqual(response.status_code, 404)

        review_payloads = {
            "pet": {
                "pet_type": "Dog",
                "pet_color": "gold",
                "pet_life_stage": "Young",
                "vibe": "Gentle,Adventurous",
                "style": "Classic",
            },
            "business": {
                "business_description": "A strategy studio for founders",
                "industry": "Consulting",
                "style": "Premium and refined",
                "audience": "Businesses / organizations",
            },
        }
        for slug, payload in review_payloads.items():
            with self.subTest(slug=slug):
                response = self.client.post(f"/{slug}/review", data=payload)

                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                self.assertIn(f'action="/{slug}/results"', body)
                self.assertNotIn(f'action="/{slug}/results?', body)
                for key, value in payload.items():
                    escaped_value = value.replace("&", "&amp;")
                    self.assertIn(f'name="{key}" value="{escaped_value}"', body)
                    self.assertIn(f'edit={key}', body)

    def test_intake_lifecycle_preserves_control_contracts(self):
        baby_body = self.client.get("/baby").get_data(as_text=True)
        pet_body = self.client.get("/pet").get_data(as_text=True)
        boat_body = self.client.get("/boat").get_data(as_text=True)

        self.assertIn('id="gender" name="gender" required', baby_body)
        self.assertIn('id="notes" name="notes"', baby_body)
        self.assertNotIn('id="notes" name="notes" required', baby_body)

        self.assertIn('data-choice-target="vibe" data-max-select="3"', pet_body)
        self.assertIn('id="vibe" name="vibe" value="" required', pet_body)
        self.assertIn('data-choice-target="cultural_context" data-max-select="2"', pet_body)

        self.assertIn('data-question-id="use"', boat_body)
        self.assertIn('data-max-select="3"', boat_body)
        self.assertIn('id="use" name="use" value="" required', boat_body)

    def test_baby_intake_renders_baby_specific_structure(self):
        response = self.client.get("/baby")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("NamEngine Baby", body)
        self.assertIn("Let’s discover your child’s name together.", body)
        self.assertIn("A child’s name is one of the few gifts that lasts a lifetime.", body)
        self.assertIn("Thoughtful AI guidance", body)
        self.assertIn("About your baby", body)
        self.assertIn("Name style", body)
        self.assertIn("Fit and feeling", body)
        self.assertIn("Sibling, surname, or family context", body)
        self.assertIn("How familiar should the name feel?", body)
        self.assertIn("What sound should the name have?", body)
        self.assertIn("Fit and feeling", body)
        self.assertIn("Taste history", body)
        self.assertIn('id="baby-intake-form"', body)
        self.assertIn('action="/baby/results"', body)
        self.assertNotIn('data-progress-form novalidate', body)
        self.assertIn("images/baby/namengine-baby-share.png", body)
        self.assertIn('data-taste-vertical="baby"', body)
        self.assertIn("data-taste-history-clear", body)
        self.assertIn('data-required="true"', body)
        self.assertIn('id="gender" name="gender" required', body)
        self.assertIn('id="style" name="style" required', body)
        self.assertIn('id="sound" name="sound" required', body)
        self.assertIn("Optional", body)
        self.assertIn(">Next</button>", body)
        self.assertNotIn("Skip for now", body)

    def test_about_page_shows_release_version(self):
        response = self.client.get("/about")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Current release", body)
        self.assertIn("NamEngine v0.9.0-beta", body)

    def test_unknown_vertical_404s(self):
        response = self.client.get("/spaceship")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
