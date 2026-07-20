import importlib.util
import pathlib
import unittest


class GunicornRuntimeConfigTest(unittest.TestCase):
    def test_gunicorn_config_extends_worker_timeout_for_llm_generation(self):
        config_path = pathlib.Path(__file__).resolve().parents[1] / "gunicorn.conf.py"
        spec = importlib.util.spec_from_file_location("gunicorn_runtime_config", config_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module.timeout, 240)


if __name__ == "__main__":
    unittest.main()
