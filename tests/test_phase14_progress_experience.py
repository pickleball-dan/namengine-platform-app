import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from namengine.core import build_brief, build_trust_cue, generate_names
from namengine.verticals import PET


class PhaseFourteenProgressExperienceTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def _unlock_access(self, vertical_slug):
        env_key = f"NAMENGINE_{vertical_slug.upper()}_BETA_PAYMENT_LINK"
        previous = os.environ.get(env_key)
        os.environ[env_key] = "https://buy.stripe.com/test_example"
        try:
            self.client.get(f"/{vertical_slug}/access/checkout")
            with patch("app._stripe_checkout_session_paid", return_value=True):
                self.client.get(f"/{vertical_slug}/access?checkout_session_id=cs_test_paid")
        finally:
            if previous is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = previous

    def test_intake_page_has_progress_experience(self):
        response = self.client.get("/pet")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('action="/pet/results"', body)
        self.assertIn('method="post"', body)
        self.assertIn('data-progress-form', body)
        self.assertIn("Generate Pet Names", body)
        self.assertIn("Finding names for this identity", body)
        self.assertIn("A few quick checks before the list appears.", body)
        self.assertIn("Finding names for this identity", body)
        self.assertIn("Checking everyday fit", body)
        self.assertNotIn("Checking sound and use", body)
        self.assertIn("data-progress-visual", body)
        self.assertIn("pet-progress-visual", body)
        self.assertIn("pet-progress-companion", body)
        self.assertIn("pet-progress-pad", body)
        self.assertIn("pet-progress-wave", body)
        self.assertNotIn("Sound check", body)
        self.assertNotIn("Bark check", body)
        self.assertIn('class="progress-steps pet-progress-steps" hidden', body)
        self.assertNotIn("progress-node-center", body)
        self.assertNotIn("Identity fit", body)
        self.assertNotIn("baby-thinking-arm", body)
        self.assertIn("data-progress-headline", body)
        self.assertIn("js/progress.js", body)
        self.assertIn("novalidate", body)

    def test_results_page_has_trust_cue_and_refine_progress(self):
        self._unlock_access("pet")
        response = self.client.get("/pet/results?species=Dog&personality=Gentle&style=Warm")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Name Style DNA", body)
        self.assertIn("Warm names with gentle energy for this pet", body)
        self.assertNotIn("Sound checked", body)
        self.assertIn("Personality matched", body)
        self.assertIn("Everyday-ready", body)
        self.assertIn("Fit reviewed", body)
        self.assertNotIn("for a dog", body)
        self.assertIn("Love or No reactions", body)
        self.assertIn("data-progress-form", body)
        self.assertIn("Picking the strongest names", body)

    def test_trust_cue_summarizes_validation_work(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        names = generate_names(PET, brief)

        cue = build_trust_cue(names)

        self.assertEqual(cue["candidate_count"], 8)
        self.assertGreater(cue["validation_count"], 0)
        self.assertIn("callability", cue["traits"])
        self.assertIn("Selected from 8 candidates", cue["summary"])

    def test_progress_copy_hides_provider_plumbing(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True).lower()

        self.assertNotIn("openai", body)
        self.assertNotIn("claude", body)
        self.assertNotIn("gemini", body)
        self.assertNotIn("groq", body)

    def test_progress_script_guides_missing_required_fields(self):
        script_path = os.path.join(self.app.static_folder, "js", "progress.js")
        with open(script_path, encoding="utf-8") as script_file:
            script = script_file.read()

        self.assertIn("form.checkValidity()", script)
        self.assertIn("focusFirstInvalid", script)
        self.assertIn("is-required-missing", script)
        self.assertIn("Required before we can generate names.", script)
        self.assertIn("scrollIntoView", script)

    def test_progress_script_holds_overlay_for_minimum_marketing_moment(self):
        script_path = os.path.join(self.app.static_folder, "js", "progress.js")
        with open(script_path, encoding="utf-8") as script_file:
            script = script_file.read()

        self.assertIn("minimumProgressMs = 18000", script)
        self.assertIn("event.preventDefault()", script)
        self.assertIn("setTimeout", script)
        self.assertIn("requestForForm(form, event.submitter)", script)
        self.assertIn("fetch(url", script)
        self.assertIn("Promise.all([request, minimumWait])", script)
        self.assertIn("window.location.assign(response.url || navigateUrl)", script)
        self.assertIn('"X-NamEngine-Progress": "1"', script)
        self.assertIn("syncOtherSelect", script)
        self.assertIn("select[data-other-select]", script)
        self.assertIn("input.required = isOther && select.required", script)
        self.assertIn("namengine:progress-step", script)
        self.assertIn("is-pulsing", script)
        self.assertIn("personalizeProgress(form)", script)
        self.assertIn("pageVertical", script)
        self.assertIn("overlay.dataset.progressVertical", script)
        self.assertIn("[data-taste-vertical]", script)
        self.assertIn("Finding names for ${subject}", script)
        self.assertIn("HTMLFormElement.prototype.submit.call(form)", script)
        self.assertIn('visual.dataset.progressPhase = String(index + 1)', script)

    def _run_progress_duplicate_submit_harness(self, action):
        script_path = Path(self.app.static_folder) / "js" / "progress.js"
        harness = textwrap.dedent(
            f"""
            const fs = require("fs");
            const vm = require("vm");
            const progressScript = fs.readFileSync({str(script_path)!r}, "utf8");

            function classList() {{
              return {{
                add() {{}},
                remove() {{}},
                toggle() {{}},
                contains() {{ return false; }}
              }};
            }}

            function element() {{
              return {{
                hidden: false,
                dataset: {{}},
                textContent: "",
                classList: classList(),
                querySelector() {{ return null; }},
                querySelectorAll() {{ return []; }},
                removeAttribute() {{}},
                setAttribute() {{}},
                appendChild() {{}},
                closest() {{ return null; }},
                checkValidity() {{ return true; }},
                focus() {{}},
                scrollIntoView() {{}},
                offsetWidth: 1,
              }};
            }}

            const overlay = element();
            const current = element();
            const visual = element();
            const steps = [element(), element(), element()];
            steps.forEach((step, index) => {{
              step.dataset.progressHeadline = `Step ${{index + 1}}`;
              step.textContent = `Step ${{index + 1}}`;
            }});

            const listeners = {{}};
            const form = element();
            form.method = "post";
            form.action = {action!r};
            form.elements = {{ namedItem() {{ return null; }} }};
            form.matches = (selector) => selector === "[data-progress-form]";
            form.addEventListener = (name, handler) => {{ listeners[name] = handler; }};

            let fetchCount = 0;
            const context = {{
              console,
              Promise,
              Error,
              Number,
              Math,
              String,
              Boolean,
              Array,
              URL,
              URLSearchParams,
              FormData: class {{
                constructor() {{}}
                append() {{}}
              }},
              HTMLFormElement: {{ prototype: {{ submit() {{ throw new Error("fallback submit should not run"); }} }} }},
              fetch() {{
                fetchCount += 1;
                return new Promise(() => {{}});
              }},
              document: {{
                body: {{ classList: classList() }},
                createElement: element,
                getElementById() {{ return null; }},
                querySelector(selector) {{
                  if (selector === "[data-progress-overlay]") return overlay;
                  if (selector === "[data-progress-current]") return current;
                  if (selector === "[data-progress-eyebrow]") return element();
                  if (selector === "[data-progress-visual]") return visual;
                  if (selector === ".progress-visual-label") return element();
                  if (selector === "[data-progress-note]") return element();
                  return null;
                }},
                querySelectorAll(selector) {{
                  if (selector === "[data-progress-step]") return steps;
                  if (selector === "form") return [form];
                  return [];
                }},
              }},
              window: {{
                location: {{ href: "https://example.test/current", assign() {{}} }},
                addEventListener() {{}},
                setInterval() {{ return 1; }},
                clearInterval() {{}},
                setTimeout() {{ return 1; }},
              }},
            }};
            context.window.window = context.window;
            vm.createContext(context);
            vm.runInContext(progressScript, context);

            const firstEvent = {{ prevented: false, preventDefault() {{ this.prevented = true; }} }};
            const secondEvent = {{ prevented: false, preventDefault() {{ this.prevented = true; }} }};
            listeners.submit(firstEvent);
            listeners.submit(secondEvent);
            console.log(JSON.stringify({{ fetchCount, firstPrevented: firstEvent.prevented, secondPrevented: secondEvent.prevented }}));
            """
        )
        result = subprocess.run(
            ["node", "-e", harness],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_intake_progress_suppresses_duplicate_in_flight_submit(self):
        result = self._run_progress_duplicate_submit_harness("https://example.test/baby/results")

        self.assertEqual(
            result,
            '{"fetchCount":1,"firstPrevented":true,"secondPrevented":true}',
        )

    def test_refine_progress_suppresses_duplicate_in_flight_submit(self):
        result = self._run_progress_duplicate_submit_harness("https://example.test/refine")

        self.assertEqual(
            result,
            '{"fetchCount":1,"firstPrevented":true,"secondPrevented":true}',
        )

    def test_progress_overlay_has_synced_node_animation_styles(self):
        css_path = os.path.join(self.app.static_folder, "css", "platform.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn(".progress-visual", css)
        self.assertIn(".progress-node-center", css)
        self.assertIn(".progress-visual-label", css)
        self.assertIn(".pet-progress-visual", css)
        self.assertIn(".pet-progress-companion", css)
        self.assertIn(".pet-progress-pad", css)
        self.assertIn(".pet-progress-wave", css)
        self.assertIn("@keyframes progress-node-pulse", css)
        self.assertIn("@keyframes pet-progress-companion-pulse", css)
        self.assertIn("@keyframes pet-progress-wave-pop", css)
        self.assertIn(".progress-visual.is-pulsing .progress-node-center", css)
        self.assertIn(".pet-progress-visual.is-pulsing .pet-progress-companion", css)
        self.assertIn("grid-template-columns: minmax(220px, 0.54fr) minmax(0, 1fr)", css)
        self.assertIn("width: min(218px, 68vw)", css)
        self.assertIn("max-height: calc(100vh - 28px)", css)
        self.assertIn("text-align: center", css)
        self.assertIn("background: #fff8ef", css)

    def test_progress_stepper_only_displays_active_line(self):
        css_path = os.path.join(self.app.static_folder, "css", "platform.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn(".progress-steps li {", css)
        self.assertIn("display: none;", css)
        self.assertIn(".progress-steps li.is-active {", css)
        self.assertIn("display: block;", css)

    def test_baby_progress_bear_keeps_motion_without_fake_hands(self):
        response = self.client.get("/baby")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("baby-thinking-panel", body)
        self.assertIn('data-progress-vertical="baby"', body)
        self.assertNotIn("baby-thinking-arm", body)

        css_path = os.path.join(self.app.static_folder, "css", "platform.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn("baby-thinking-bear-breathe", css)
        self.assertIn("baby-thinking-bear-hop", css)
        self.assertIn("baby-thinking-bubble", css)
        self.assertIn(".progress-visual > * { display: none; }", css)
        self.assertIn('data-progress-phase="4"', css)
        self.assertIn("rgba(255, 107, 87, 0.34)", css)
        self.assertIn(".baby-thinking-panel .progress-steps {", css)
        self.assertIn("clip: rect(0 0 0 0);", css)
        self.assertNotIn("baby-thinking-left-arm-wave", css)
        self.assertNotIn("baby-thinking-right-arm-wave", css)

    def test_business_progress_hides_redundant_step_line(self):
        response = self.client.get("/business")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('class="progress-steps" hidden', body)

    def test_hidden_progress_steps_do_not_display(self):
        css_path = os.path.join(self.app.static_folder, "css", "platform.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn(".progress-steps[hidden]", css)
        self.assertIn("display: none;", css)

    def test_baby_refinement_progress_keeps_baby_identity(self):
        self._unlock_access("baby")
        response = self.client.get("/baby/results?gender=Girl&style=Classic&sound=Soft")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('data-taste-vertical="baby"', body)
        self.assertIn('data-progress-vertical="baby"', body)
        self.assertIn("baby-thinking-panel", body)
        self.assertIn('action="/refine"', body)


if __name__ == "__main__":
    unittest.main()
