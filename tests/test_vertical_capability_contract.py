from dataclasses import replace
import unittest

from namengine.core.generation_prompt_config import generation_prompt_config_for
from namengine.core.pet_portrait import artifact_definition
from namengine.core.quality_framework import quality_adapter_for
from namengine.core.validation import validate_result
from namengine.core.vertical_capabilities import (
    ACTIVE_VERTICAL_SLUGS,
    CapabilityContractError,
    active_vertical_capability_contracts,
    assert_active_vertical_capability_contracts_complete,
    vertical_capability_contract,
)
from namengine.core.schemas import NameResult, NamingBrief
from namengine.verticals import BABY, BOAT, BUSINESS, PET


class VerticalCapabilityContractTest(unittest.TestCase):
    def test_active_verticals_have_complete_contracts(self):
        contracts = active_vertical_capability_contracts()

        self.assertEqual(
            tuple(contract.vertical_slug for contract in contracts),
            ACTIVE_VERTICAL_SLUGS,
        )
        expected = {
            "baby": {
                "review_mode": "direct_generation",
                "max_rounds": 4,
                "terminal_reaction_mode": "love_only",
                "terminal_edit_locked": True,
                "prompt_version": "namengine-baby-quality-v1",
                "quality": "baby-quality-score-v1",
                "validation": ("baby_pronunciation", "baby_initials", "baby_popularity"),
                "artifact": "baby_blanket",
                "render": "baby_keepsake",
                "special": ("baby_taxonomy", "baby_final_decision"),
            },
            "pet": {
                "review_mode": "direction_review",
                "max_rounds": 4,
                "terminal_reaction_mode": "normal",
                "terminal_edit_locked": False,
                "prompt_version": "namengine-pet-quality-v1",
                "quality": "pet-quality-score-v1",
                "validation": ("pet_callability", "pet_sound_clarity"),
                "artifact": "pet_portrait",
                "render": "pet_portrait",
                "special": ("pet_legacy_brief_aliases",),
            },
            "business": {
                "review_mode": "direction_review",
                "max_rounds": 4,
                "terminal_reaction_mode": "normal",
                "terminal_edit_locked": False,
                "prompt_version": "namengine-business-quality-v1",
                "quality": "business-quality-score-v1",
                "validation": (
                    "business_domain",
                    "business_category_fit",
                    "business_similarity",
                ),
                "artifact": "business_brand_concept",
                "render": "business_brand_concept",
                "special": ("business_recovery_finalizer", "business_domain_enrichment"),
            },
            "boat": {
                "review_mode": "direct_generation",
                "max_rounds": 4,
                "terminal_reaction_mode": "normal",
                "terminal_edit_locked": False,
                "prompt_version": "namengine-taste-engine-v1",
                "quality": "boat-quality-score-v1",
                "validation": (
                    "boat_radio_clarity",
                    "boat_tradition_fit",
                    "boat_length",
                ),
                "artifact": "boat_portrait",
                "render": "boat_transom",
                "special": ("boat_transom_artifact",),
            },
        }

        for contract in contracts:
            with self.subTest(vertical=contract.vertical_slug):
                row = expected[contract.vertical_slug]
                self.assertEqual(contract.review_mode, row["review_mode"])
                self.assertEqual(contract.max_rounds, row["max_rounds"])
                self.assertEqual(contract.terminal_reaction_mode, row["terminal_reaction_mode"])
                self.assertEqual(contract.terminal_edit_locked, row["terminal_edit_locked"])
                self.assertEqual(contract.generation_prompt_config.prompt_version, row["prompt_version"])
                self.assertEqual(contract.quality_adapter.score_version, row["quality"])
                self.assertEqual(contract.validation_modules, row["validation"])
                self.assertEqual(contract.artifact_kind, row["artifact"])
                self.assertEqual(contract.artifact_render_variant, row["render"])
                self.assertEqual(contract.special_capabilities, row["special"])

    def test_contract_resolves_existing_subsystem_implementations(self):
        for vertical in (BABY, PET, BUSINESS, BOAT):
            with self.subTest(vertical=vertical.slug):
                contract = vertical_capability_contract(vertical)
                self.assertIs(
                    contract.generation_prompt_config,
                    generation_prompt_config_for(vertical.slug),
                )
                self.assertIs(contract.quality_adapter, quality_adapter_for(vertical.slug))
                self.assertIs(contract.artifact_definition, artifact_definition(vertical.slug))

    def test_active_verticals_do_not_use_silent_validation_fallback(self):
        for vertical in (BABY, PET, BUSINESS, BOAT):
            with self.subTest(vertical=vertical.slug):
                brief = NamingBrief(vertical=vertical.slug, inputs={})
                result = NameResult(id=f"{vertical.slug}-probe", name="Contract", slug="contract")
                modules = {item.module for item in validate_result(vertical, brief, result)}
                self.assertNotIn("validation_not_configured", modules)
                contract = vertical_capability_contract(vertical)
                self.assertEqual(set(contract.validation_executor_modules), modules)

    def test_missing_active_registration_fails_explicitly(self):
        candidate = replace(PET, slug="newactive")

        with self.assertRaisesRegex(
            CapabilityContractError,
            "Generation prompt config is not registered for active vertical: newactive",
        ):
            vertical_capability_contract(candidate)

        with self.assertRaisesRegex(
            CapabilityContractError,
            "Generation prompt config is not registered for active vertical: newactive",
        ):
            assert_active_vertical_capability_contracts_complete((candidate,))

    def test_contract_fails_if_quality_or_artifact_registration_is_missing(self):
        with self.assertRaisesRegex(
            CapabilityContractError,
            "Quality adapter is not registered for active vertical: pet",
        ):
            vertical_capability_contract(PET, quality_lookup=lambda _slug: None)

        with self.assertRaisesRegex(
            CapabilityContractError,
            "Graphical artifact is not registered for active vertical: pet",
        ):
            vertical_capability_contract(PET, artifact_lookup=lambda _slug: None)


if __name__ == "__main__":
    unittest.main()
