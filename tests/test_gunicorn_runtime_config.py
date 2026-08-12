import importlib.util
import pathlib
import unittest


EXPECTED_GENERATION_TIMEOUT_SECONDS = 420


class GunicornRuntimeConfigTest(unittest.TestCase):
    def test_gunicorn_config_extends_worker_timeout_for_llm_generation(self):
        config_path = pathlib.Path(__file__).resolve().parents[1] / "gunicorn.conf.py"
        spec = importlib.util.spec_from_file_location("gunicorn_runtime_config", config_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module.timeout, EXPECTED_GENERATION_TIMEOUT_SECONDS)

    def test_runtime_start_commands_match_llm_generation_timeout(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        expected_flag = f"--timeout {EXPECTED_GENERATION_TIMEOUT_SECONDS}"

        self.assertIn(expected_flag, (root / "Procfile").read_text())
        self.assertIn(expected_flag, (root / "render.yaml").read_text())


if __name__ == "__main__":
    unittest.main()
