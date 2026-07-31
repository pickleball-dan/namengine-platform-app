import unittest
from html.parser import HTMLParser

from app import create_app


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
        self.assertIn("Finding the right name should begin with understanding", body)
        self.assertIn("Start naming", body)
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
        self.assertEqual(anchors_by_text["Unlock Baby Access"], {"/baby/access"})
        self.assertEqual(anchors_by_text["Unlock Pet Access"], {"/pet/access"})
        self.assertEqual(anchors_by_text["Unlock Business Access"], {"/business/access"})

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
        self.assertIn("Tell us who they are.", body)
        self.assertIn("Required", body)
        self.assertIn('data-choice-value="Dog"', body)
        self.assertIn('data-choice-value="Cat"', body)
        self.assertIn('data-choice-value="Balanced"', body)
        self.assertIn('data-choice-value="Very important"', body)
        self.assertIn('action="/pet/results"', body)
        self.assertIn('method="post"', body)
        self.assertIn('data-progress-form novalidate', body)
        self.assertIn("Generate Pet Names", body)

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
        self.assertIn('action="/baby/feelings"', body)
        self.assertNotIn('data-progress-form novalidate', body)
        self.assertIn("images/baby/namengine-baby-share.png", body)
        self.assertIn('data-taste-vertical="baby"', body)
        self.assertIn("data-taste-history-clear", body)
        self.assertIn('data-required="true"', body)
        self.assertIn('id="gender" name="gender" required', body)
        self.assertIn('id="style" name="style" required', body)
        self.assertIn('id="sound" name="sound" required', body)
        self.assertIn("Optional", body)
        self.assertIn(">Skip</button>", body)
        self.assertNotIn("Skip for now", body)

    def test_unknown_vertical_404s(self):
        response = self.client.get("/spaceship")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
