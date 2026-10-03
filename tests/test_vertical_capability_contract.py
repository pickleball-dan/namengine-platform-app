from dataclasses import replace
import unittest
from unittest.mock import patch

from app import _record_provider_failures_from_fallback, _required_baby_refinement_count
from namengine.core.generation_prompt_config import generation_prompt_config_for
from namengine.core.pet_portrait import artifact_definition
from namengine.core.schemas import NameResult, NamingBrief
from namengine.core.quality_framework import quality_adapter_for
from namengine.core.validation import validate_result
from namengine.core.vertical_capabilities import (
    ACTIVE_VERTICAL_SLUGS,
    CapabilityContractError,
    active_vertical_capability_contracts,
    assert_active_vertical_capability_contracts_complete,
    registered_route_generation_policies,
    route_generation_policy_for,
    vertical_capability_contract,
)
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
                "runtime_validation": ("baby_gender_direction",),
                "artifact": "baby_blanket",
                "render": "baby_keepsake",
                "special": ("baby_taxonomy", "baby_final_decision"),
                "route_policy": {
                    "ai_primary_default": True,
                    "allow_provider_fallback": True,
                    "fallback_audit_enabled": True,
                    "cache": (
                        "ai_primary_source_consistency",
                        "customer_environment_requires_all_ai",
                        "baby_gender_filter",
                        "baby_gender_direction_validation",
                    ),
                    "required_count": "round_2_3_default_round_4_min_6",
                    "previous_fill": "never",
                    "result_filter": "baby_gender_and_avoid",
                    "generation_special": ("baby_taxonomy", "baby_generation_guidance"),
                },
            },
            "pet": {
                "review_mode": "direction_review",
                "max_rounds": 4,
                "terminal_reaction_mode": "normal",
                "terminal_edit_locked": False,
                "prompt_version": "namengine-pet-quality-v1",
                "quality": "pet-quality-score-v1",
                "validation": ("pet_callability", "pet_sound_clarity"),
                "runtime_validation": (),
                "artifact": "pet_portrait",
                "render": "pet_portrait",
                "special": ("pet_legacy_brief_aliases",),
                "route_policy": {
                    "ai_primary_default": True,
                    "allow_provider_fallback": True,
                    "fallback_audit_enabled": True,
                    "cache": (
                        "ai_primary_source_consistency",
                        "customer_environment_requires_all_ai",
                    ),
                    "required_count": "none",
                    "previous_fill": "rounds_before_four",
                    "result_filter": "none",
                    "generation_special": (),
                },
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
                "runtime_validation": (),
                "artifact": "business_brand_concept",
                "render": "business_brand_concept",
                "special": ("business_recovery_finalizer", "business_domain_enrichment"),
                "route_policy": {
                    "ai_primary_default": True,
                    "allow_provider_fallback": False,
                    "fallback_audit_enabled": False,
                    "cache": (
                        "ai_primary_source_consistency",
                        "always_requires_all_ai",
                        "business_domain_validation",
                        "business_domain_info",
                    ),
                    "required_count": "none",
                    "previous_fill": "rounds_before_four",
                    "result_filter": "none",
                    "generation_special": (
                        "business_recovery_finalizer",
                        "business_quality_gate",
                        "business_domain_enrichment",
                    ),
                },
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
                "runtime_validation": (),
                "artifact": "boat_portrait",
                "render": "boat_transom",
                "special": ("boat_transom_artifact",),
                "route_policy": {
                    "ai_primary_default": False,
                    "allow_provider_fallback": True,
                    "fallback_audit_enabled": False,
                    "cache": (
                        "ai_primary_source_consistency",
                        "customer_environment_requires_all_ai",
                    ),
                    "required_count": "none",
                    "previous_fill": "rounds_before_four",
                    "result_filter": "none",
                    "generation_special": (),
                },
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
                self.assertEqual(contract.validation_runtime_modules, row["runtime_validation"])
                self.assertEqual(
                    contract.validation_executor_modules,
                    row["runtime_validation"] + row["validation"],
                )
                self.assertEqual(contract.artifact_kind, row["artifact"])
                self.assertEqual(contract.artifact_render_variant, row["render"])
                self.assertEqual(contract.special_capabilities, row["special"])
                policy = contract.route_generation_policy
                policy_row = row["route_policy"]
                self.assertEqual(policy.ai_primary_default, policy_row["ai_primary_default"])
                self.assertEqual(policy.allow_provider_fallback, policy_row["allow_provider_fallback"])
                self.assertEqual(policy.fallback_audit_enabled, policy_row["fallback_audit_enabled"])
                self.assertEqual(policy.cache_freshness_requirements, policy_row["cache"])
                self.assertEqual(policy.required_refinement_count_policy, policy_row["required_count"])
                self.assertEqual(policy.allow_previous_fill_policy, policy_row["previous_fill"])
                self.assertEqual(policy.result_filter_policy, policy_row["result_filter"])
                self.assertEqual(
                    policy.special_generation_capabilities,
                    policy_row["generation_special"],
                )

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
                self.assertIs(
                    contract.route_generation_policy,
                    route_generation_policy_for(vertical.slug),
                )

    def test_route_generation_policies_are_explicit_for_active_verticals(self):
        policies = registered_route_generation_policies()

        self.assertEqual(tuple(policies), ACTIVE_VERTICAL_SLUGS)
        for slug in ACTIVE_VERTICAL_SLUGS:
            with self.subTest(vertical=slug):
                policy = policies[slug]
                self.assertIs(policy, route_generation_policy_for(slug))
                self.assertIn(policy.required_refinement_count_policy, {
                    "none",
                    "round_2_3_default_round_4_min_6",
                })
                self.assertIn(policy.allow_previous_fill_policy, {"never", "rounds_before_four"})
                self.assertIn(policy.result_filter_policy, {"none", "baby_gender_and_avoid"})

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

        with self.assertRaisesRegex(
            CapabilityContractError,
            "Route/generation policy is not declared for active vertical: pet",
        ):
            vertical_capability_contract(PET, route_policy_lookup=lambda _slug: None)

    def test_required_refinement_count_uses_route_generation_policy(self):
        self.assertIsNone(_required_baby_refinement_count(BABY, 1))
        self.assertEqual(_required_baby_refinement_count(BABY, 2), BABY.default_result_count)
        self.assertEqual(_required_baby_refinement_count(BABY, 3), BABY.default_result_count)
        self.assertEqual(_required_baby_refinement_count(BABY, 4), 6)
        self.assertEqual(_required_baby_refinement_count(BABY, 5), 6)

        for vertical in (PET, BUSINESS, BOAT):
            for round_number in (1, 2, 3, 4, 5):
                with self.subTest(vertical=vertical.slug, round_number=round_number):
                    self.assertIsNone(_required_baby_refinement_count(vertical, round_number))

    def test_provider_fallback_audit_uses_route_generation_policy(self):
        for vertical in (BABY, PET, BUSINESS, BOAT):
            with self.subTest(vertical=vertical.slug):
                brief = NamingBrief(vertical=vertical.slug, inputs={})
                result = NameResult(
                    id=f"{vertical.slug}-fallback",
                    name="Contract",
                    slug="contract",
                    metadata={
                        "provider": "fallback",
                        "provider_failures": [
                            {
                                "provider": "openai",
                                "exception_type": "generation_error",
                                "latency_ms": 17,
                            }
                        ],
                    },
                )

                with patch("app.save_failed_generation_audit") as save_failed_generation_audit:
                    _record_provider_failures_from_fallback(vertical, brief, [result])

                if route_generation_policy_for(vertical.slug).fallback_audit_enabled:
                    save_failed_generation_audit.assert_called_once()
                    self.assertNotIn("provider_failures", result.metadata)
                else:
                    save_failed_generation_audit.assert_not_called()
                    self.assertIn("provider_failures", result.metadata)


if __name__ == "__main__":
    unittest.main()
