import re
import unittest
from pathlib import Path

from app import create_app


class BabyConversationalIntakeV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.testing = True
        cls.client = cls.app.test_client()
        cls.root = Path(cls.app.root_path)

    def question_markup(self, body, question_id):
        match = re.search(
            rf'<section class="baby-question(?: [^"]*)?"[^>]*data-question-id="{re.escape(question_id)}".*?</section>',
            body,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, f"Missing Baby question markup for {question_id}")
        return match.group(0)

    def test_baby_intake_keeps_original_route_and_field_contract(self):
        body = self.client.get("/baby").get_data(as_text=True)

        self.assertIn('action="/baby/feelings"', body)
        for field in (
            "gender", "family_context", "cultural_heritage", "notes",
            "discovery_style", "style", "timeless_vs_distinctive",
            "familiarity_preference", "sound", "cultural_context",
            "partner_alignment", "avoid",
        ):
            self.assertIn(f'name="{field}"', body)

    def test_intake_renders_one_question_shell_progress_and_edit_history(self):
        body = self.client.get("/baby").get_data(as_text=True)

        self.assertIn("data-baby-question-stage", body)
        self.assertEqual(body.count("data-baby-question data-question-id="), 12)
        self.assertIn("data-baby-answer-history", body)
        self.assertIn("data-baby-progressbar", body)
        heritage = self.question_markup(body, "cultural_heritage")
        self.assertNotIn('data-condition-field="cultural_context"', heritage)
        self.assertIn("Cultural / heritage feel", heritage)
        self.assertIn('data-choice-value="Italian"', heritage)
        self.assertNotIn('class="baby-native-submit" type="submit">', body)

    def test_final_priority_question_preserves_strength_inputs_and_auto_handoff(self):
        body = self.client.get(
            "/baby/feelings?gender=Girl&style=Classic&sound=Soft"
        ).get_data(as_text=True)

        self.assertIn('action="/baby/results"', body)
        self.assertIn('name="taste_strength_about_your_baby" value="34"', body)
        self.assertIn('name="taste_strength_name_style" value="33"', body)
        self.assertIn('name="taste_strength_fit_and_feeling" value="33"', body)
        self.assertIn("Wonderful.", body)
        self.assertIn("We’re creating names that feel uniquely yours...", body)
        self.assertNotIn("Find names that feel right</button>", body)

    def test_optional_multiple_choice_questions_show_skip(self):
        body = self.client.get("/baby").get_data(as_text=True)

        for question_id in (
            "cultural_heritage",
            "discovery_style",
            "timeless_vs_distinctive",
            "familiarity_preference",
            "cultural_context",
        ):
            with self.subTest(question_id=question_id):
                question = self.question_markup(body, question_id)
                self.assertIn('class="baby-skip" data-baby-skip>Skip for now</button>', question)

    def test_required_multiple_choice_questions_do_not_show_skip(self):
        body = self.client.get("/baby").get_data(as_text=True)

        for question_id in ("gender", "style", "sound"):
            with self.subTest(question_id=question_id):
                question = self.question_markup(body, question_id)
                self.assertNotIn("data-baby-skip", question)

    def test_optional_questions_use_helpful_personalization_copy(self):
        body = self.client.get("/baby").get_data(as_text=True)

        optional_ids = (
            "family_context",
            "cultural_heritage",
            "notes",
            "discovery_style",
            "timeless_vs_distinctive",
            "familiarity_preference",
            "cultural_context",
            "partner_alignment",
            "avoid",
        )
        for question_id in optional_ids:
            with self.subTest(question_id=question_id):
                question = self.question_markup(body, question_id)
                self.assertIn(
                    '<p class="baby-optional-note">Optional · Personalizes results</p>',
                    question,
                )

        for question_id in ("gender", "style", "sound"):
            with self.subTest(question_id=question_id):
                self.assertNotIn("baby-optional-note", self.question_markup(body, question_id))

    def test_skip_clears_selection_and_answering_removes_skipped_state(self):
        intake_js = (self.root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")
        clear_question = intake_js.split("function clearQuestion(question)", 1)[1].split(
            "function clearDependentConditionOverrides", 1
        )[0]
        skip_question = intake_js.split("function skipQuestion(question)", 1)[1].split(
            "function syncInitialSelections", 1
        )[0]
        select_choice = intake_js.split("function selectChoice(question, button)", 1)[1].split(
            "function continueText", 1
        )[0]

        self.assertIn('control.value = ""', clear_question)
        self.assertIn('button.classList.remove("is-selected")', clear_question)
        self.assertIn('button.setAttribute("aria-checked", "false")', clear_question)
        self.assertIn("clearQuestion(question)", skip_question)
        self.assertIn("skipped.add(question.dataset.questionId)", skip_question)
        self.assertIn('confirmAndAdvance(question, "Skipped for now")', skip_question)
        self.assertIn("skipped.delete(question.dataset.questionId)", select_choice)

    def test_heritage_question_is_visible_independent_of_inspiration_choice(self):
        body = self.client.get("/baby").get_data(as_text=True)
        intake_js = (self.root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")
        heritage = self.question_markup(body, "cultural_heritage")
        skip_question = intake_js.split("function skipQuestion(question)", 1)[1].split(
            "function syncInitialSelections", 1
        )[0]

        self.assertNotIn('data-condition-field="cultural_context"', heritage)
        self.assertIn('name="cultural_heritage"', heritage)
        self.assertIn('data-choice-value="Irish"', heritage)
        self.assertIn("clearDependentConditionOverrides(question)", skip_question)
        self.assertIn("syncConditions()", intake_js)

    def test_frontend_contracts_cover_auto_advance_keyboard_and_reduced_motion(self):
        intake_js = (self.root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")
        feelings_js = (self.root / "static" / "js" / "feelings-scale.js").read_text(encoding="utf-8")
        css = (self.root / "static" / "css" / "platform.css").read_text(encoding="utf-8")

        self.assertIn("confirmAndAdvance", intake_js)
        self.assertIn("ArrowDown", intake_js)
        self.assertIn("data-edit-answer", intake_js)
        self.assertIn("applicableQuestions", intake_js)
        self.assertIn("prefers-reduced-motion: reduce", intake_js)
        self.assertIn("babyFinalForm.requestSubmit()", feelings_js)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("overflow-x: hidden", css)

    def test_gender_benchmark_preserves_values_descriptions_and_semantics(self):
        body = self.client.get("/baby").get_data(as_text=True)
        question = self.question_markup(body, "gender")
        values_and_descriptions = {
            "Girl": "We’re expecting a baby girl.",
            "Boy": "We’re expecting a baby boy.",
            "Gender-neutral": "We love names that work for any baby.",
            "Surprise me": "We’d love a mix of ideas for every possibility.",
        }

        self.assertIn('id="gender" name="gender" required', question)
        self.assertEqual(question.count('class="baby-choice baby-choice-illustrated'), 4)
        for value, description in values_and_descriptions.items():
            with self.subTest(value=value):
                self.assertIn(f'data-choice-value="{value}"', question)
                self.assertIn(f'<option value="{value}"', question)
                self.assertIn(description, question)
        self.assertEqual(question.count('role="radio"'), 4)
        self.assertEqual(question.count('aria-checked='), 4)
        self.assertNotIn("data-baby-skip", question)

    def test_gender_benchmark_keeps_auto_advance_and_live_journey_state(self):
        body = self.client.get("/baby").get_data(as_text=True)
        intake_js = (self.root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")
        select_choice = intake_js.split("function selectChoice(question, button)", 1)[1].split(
            "function continueText", 1
        )[0]

        self.assertIn('data-question-section="About your baby"', self.question_markup(body, "gender"))
        self.assertEqual(body.count("data-baby-journey-stage"), 3)
        self.assertIn("updateJourney(question)", intake_js)
        self.assertIn("question.dataset.questionSection", intake_js)
        self.assertIn('item.setAttribute("aria-current", "step")', intake_js)
        self.assertIn("confirmAndAdvance(question, value)", select_choice)

    def test_contextual_progress_titles_preserve_numeric_progress(self):
        body = self.client.get("/baby").get_data(as_text=True)
        intake_js = (self.root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")

        self.assertIn("data-baby-progress-title", body)
        self.assertIn("data-baby-progress-copy", body)
        self.assertIn("data-journey-vertical=\"baby\"", body)
        self.assertIn("Let’s get to know your family.", body)
        self.assertIn("journeyCopyConfigurations", intake_js)
        self.assertIn("progressTitle.textContent = journeyCopy.questions[question.dataset.questionId]", intake_js)
        self.assertIn("progressCopy.textContent = `Question ${number} of ${total}`", intake_js)
        self.assertIn('progressBar.setAttribute("aria-valuenow", String(number))', intake_js)
        self.assertIn('progressBar.setAttribute("aria-valuemax", String(total))', intake_js)

    def test_every_question_has_the_approved_journey_message(self):
        intake_js = (self.root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")
        expected = {
            "gender": "Let’s get to know your family.",
            "style": "We’re discovering the kinds of names you’ll love.",
            "familiarity_preference": "We’re discovering the kinds of names you’ll love.",
            "discovery_style": "We’re discovering the kinds of names you’ll love.",
            "timeless_vs_distinctive": "We’re narrowing in on the right fit.",
            "sound": "We’re narrowing in on the right fit.",
            "cultural_context": "We’re narrowing in on the right fit.",
            "cultural_heritage": "We’re narrowing in on the right fit.",
            "family_context": "We’re refining your perfect shortlist.",
            "partner_alignment": "We’re refining your perfect shortlist.",
            "avoid": "We’re refining your perfect shortlist.",
            "notes": "Almost there.",
        }

        for question_id, message in expected.items():
            with self.subTest(question_id=question_id):
                self.assertIn(f'{question_id}: "{message}"', intake_js)
        self.assertIn('completion: "Almost there."', intake_js)

    def test_feelings_scale_uses_warm_journey_introduction(self):
        body = self.client.get("/baby/feelings?gender=Girl&style=Classic&sound=Soft").get_data(as_text=True)

        self.assertIn("Now tell us what matters most.", body)
        self.assertIn('<span class="baby-progress-count">Final step</span>', body)

    def test_forward_back_and_skip_paths_all_refresh_journey_copy(self):
        intake_js = (self.root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")
        show_question = intake_js.split("function showQuestion(question, options)", 1)[1].split(
            "function nextQuestion", 1
        )[0]
        confirmation = intake_js.split("function confirmAndAdvance(question, label)", 1)[1].split(
            "function finishInterview", 1
        )[0]
        skip_question = intake_js.split("function skipQuestion(question)", 1)[1].split(
            "function syncInitialSelections", 1
        )[0]
        click_handler = intake_js.split('form.addEventListener("click"', 1)[1]

        self.assertIn("updateProgress(question)", show_question)
        self.assertIn("if (next) showQuestion(next)", confirmation)
        self.assertIn('confirmAndAdvance(question, "Skipped for now")', skip_question)
        self.assertIn("if (question) showQuestion(question)", click_handler)

    def test_nursery_art_is_local_decorative_and_does_not_replace_labels(self):
        body = self.client.get("/baby").get_data(as_text=True)
        asset = self.root / "static" / "images" / "baby" / "intake" / "nursery-sprite-v1.png"

        self.assertIn('<div class="baby-nursery-scene" aria-hidden="true">', body)
        self.assertIn('<span class="baby-choice-art baby-sprite-bow" aria-hidden="true"></span>', body)
        self.assertIn('<strong>Girl</strong>', body)
        self.assertIn('aria-label="NamEngine home"', body)
        self.assertTrue(asset.is_file())
        self.assertLess(asset.stat().st_size, 1_000_000)

    def test_benchmark_css_covers_supported_mobile_widths_without_overflow(self):
        css = (self.root / "static" / "css" / "platform.css").read_text(encoding="utf-8")

        for breakpoint in (1080, 820, 600, 350):
            self.assertIn(f"@media (max-width: {breakpoint}px)", css)
        mobile = css.split("@media (max-width: 600px)", 1)[1].split("@media (max-width: 350px)", 1)[0]
        self.assertIn("grid-template-columns: minmax(0, 1fr)", mobile)
        self.assertIn("min-width: 0", css)
        self.assertIn("overflow-x: hidden", css)

    def test_polish_removes_legacy_stage_copy_and_refines_shared_cards(self):
        body = self.client.get("/baby").get_data(as_text=True)
        css = (self.root / "static" / "css" / "platform.css").read_text(encoding="utf-8")

        self.assertNotIn("About your baby. Step 1 of 3", body)
        self.assertIn(".baby-choice:not(.baby-choice-illustrated)", css)
        self.assertIn(".baby-choice:not(.baby-choice-illustrated).is-selected", css)
        self.assertIn("width: 164px", css)
        self.assertIn("background: transparent", css)
        self.assertIn("border: 0", css)

    def test_answer_summary_is_compact_and_wraps_on_mobile(self):
        css = (self.root / "static" / "css" / "platform.css").read_text(encoding="utf-8")
        history_styles = css.split(".vertical-baby .baby-answer-history {", 1)[1].split("}", 1)[0]
        chip_styles = css.split(".vertical-baby .baby-answer-chip {", 1)[1].split("}", 1)[0]
        mobile_styles = css.split("@media (max-width: 680px)", 1)[1]

        self.assertIn("max-height: 116px", history_styles)
        self.assertIn("padding-bottom: 12px", history_styles)
        self.assertIn("min-height: 40px", chip_styles)
        self.assertIn("flex-wrap: wrap", mobile_styles)
        self.assertIn("overflow-x: visible", mobile_styles)


if __name__ == "__main__":
    unittest.main()
