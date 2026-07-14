import unittest

from app import create_app


class PhaseTwoWebShellTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_home_lists_vertical_routes(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("The TASTE ENGINE", body)
        self.assertIn('href="/pet"', body)
        self.assertIn('href="/baby"', body)
        self.assertIn('href="/business"', body)
        self.assertIn('href="/character"', body)

    def test_pet_intake_renders_from_vertical_config(self):
        response = self.client.get("/pet")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("NamEngine Pet", body)
        self.assertIn("How adventurous should we be?", body)
        self.assertIn("Name style", body)
        self.assertIn("Who&#39;s joining the family?", body)
        self.assertIn("About your pet", body)
        self.assertIn("What overall style feels closest?", body)
        self.assertIn("How easy should it be to call?", body)
        self.assertIn("What personality should the name capture?", body)
        self.assertIn("Fit and feeling", body)
        self.assertIn("Name inspiration", body)
        self.assertIn("Tell us about your pet", body)
        self.assertIn("Required", body)
        self.assertIn('<option value="Dog">Dog</option>', body)
        self.assertIn('<option value="Cat">Cat</option>', body)
        self.assertIn('<option value="Balanced mix">Balanced mix</option>', body)
        self.assertIn('<option value="Very important">Very important</option>', body)
        self.assertIn('action="/pet/feelings"', body)
        self.assertNotIn('data-progress-form novalidate', body)
        self.assertIn("novalidate", body)

    def test_baby_intake_renders_baby_specific_structure(self):
        response = self.client.get("/baby")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("NamEngine Baby", body)
        self.assertIn("Let’s shape the right baby name.", body)
        self.assertIn("About your baby", body)
        self.assertIn("Name style", body)
        self.assertIn("Fit and feeling", body)
        self.assertIn("Sibling, surname, or family context", body)
        self.assertIn("How familiar should the name feel?", body)
        self.assertIn("What sound should the name have?", body)
        self.assertIn("Family fit", body)
        self.assertIn("Taste history", body)
        self.assertIn('id="baby-intake-form"', body)
        self.assertIn('action="/baby/feelings"', body)
        self.assertNotIn('data-progress-form novalidate', body)
        self.assertIn("images/baby/namengine-baby-logo.png", body)
        self.assertIn('data-taste-vertical="baby"', body)
        self.assertIn("data-taste-history-clear", body)
        self.assertIn("Required", body)
        self.assertIn('id="gender" name="gender" required', body)
        self.assertIn('id="style" name="style" required', body)
        self.assertIn('id="sound" name="sound" required', body)
        self.assertIn("Optional", body)

    def test_unknown_vertical_404s(self):
        response = self.client.get("/spaceship")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
