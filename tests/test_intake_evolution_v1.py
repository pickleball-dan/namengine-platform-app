import json
import math
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path

from namengine.core import build_brief, generate_names
from namengine.core.baby_intake_adapter import (
    BABY_INTAKE_ADAPTER_VERSION,
    BABY_INTAKE_VERSION,
    BABY_LEGACY_INTAKE_VERSION,
    BABY_NORMALIZER_VERSION,
)
from namengine.core.canonical_intent import CanonicalNamingIntent
from namengine.core.intake import (
    IntakeAdapter,
    IntakeFieldDefinition,
    IntakeSchema,
    compare_normalized_intakes,
    list_intake_schemas,
    normalize_intake,
    register_intake_adapter,
    register_intake_schema,
    resolve_intake_schema,
    set_default_intake_version,
    unregister_intake_adapter,
    unregister_intake_schema,
    validate_intake,
)
from namengine.core.intake_migrations import (
    IntakeMigration,
    IntakeMigrationError,
    migrate_intake,
    register_intake_migration,
    unregister_intake_migration,
)
from namengine.core.name_evaluation import (
    DEFAULT_PACK_ROOT,
    evaluate_generated_fixture,
    load_evaluation_pack,
    validate_fixture,
)
from namengine.core.schemas import NamingBrief
from namengine.core.storage import get_recent_audit_sessions, save_session
from namengine.verticals import BABY, PET


def _test_intent(values, schema):
    return CanonicalNamingIntent(
        vertical=schema.vertical,
        naming_target="test target",
        naming_styles=(str(values.get("label") or ""),),
        priority_weights={"importance": float(values.get("weight", 0))},
        source_intake_version=schema.schema_version,
        normalization_version=schema.normalizer_version,
        extensions={"enabled": values.get("enabled", False)},
    )


class IntakeEvolutionV1Test(unittest.TestCase):
    def setUp(self):
        self.vertical = "intake-test"
        self.schema = IntakeSchema(
            schema_id="intake-test-schema",
            schema_version="intake-test-v1",
            vertical=self.vertical,
            display_name="Test intake",
            description="Cross-vertical test adapter",
            fields=(
                IntakeFieldDefinition(
                    "label", required=True, aliases=("name",), deprecated_aliases=("old_name",),
                    allowed_values=("Soft", "Strong"), max_length=20,
                ),
                IntakeFieldDefinition(
                    "weight", data_type="number", has_default=True, default=0.0,
                    minimum=0, maximum=1, intent_path="priority_weights.importance",
                ),
                IntakeFieldDefinition(
                    "enabled", data_type="boolean", has_default=True, default=False,
                    intent_path="extensions.enabled",
                ),
                IntakeFieldDefinition(
                    "items", data_type="string_list", max_items=2, max_length=10,
                ),
            ),
            unknown_field_policy="reject",
            normalizer_version="intake-test-normalizer-v1",
        )
        self.adapter = IntakeAdapter(
            vertical_slug=self.vertical,
            version="intake-test-adapter-v1",
            canonical_intent_version="canonical-naming-intent-v1",
            build_intent=_test_intent,
        )
        register_intake_schema(self.schema, make_default=True)
        register_intake_adapter(self.adapter)

    def tearDown(self):
        unregister_intake_schema(self.vertical, self.schema.schema_version)
        unregister_intake_adapter(self.vertical)
        for source in ("migration-a", "migration-b", "migration-c"):
            unregister_intake_migration(self.vertical, source)

    def test_registry_registration_duplicate_defaults_listing_and_cleanup(self):
        self.assertEqual(resolve_intake_schema(self.vertical), self.schema)
        register_intake_schema(self.schema)
        with self.assertRaisesRegex(ValueError, "already registered"):
            register_intake_schema(replace(self.schema, display_name="Conflict"))
        v2 = replace(self.schema, schema_id="intake-test-schema-2", schema_version="intake-test-v2")
        register_intake_schema(v2)
        self.addCleanup(unregister_intake_schema, self.vertical, v2.schema_version)
        set_default_intake_version(self.vertical, v2.schema_version)
        self.assertEqual(resolve_intake_schema(self.vertical).schema_version, v2.schema_version)
        versions = [row["schema_version"] for row in list_intake_schemas(self.vertical)]
        self.assertEqual(versions, sorted(versions))
        unregister_intake_schema(self.vertical, v2.schema_version)
        self.assertEqual(resolve_intake_schema(self.vertical).schema_version, self.schema.schema_version)

    def test_registry_rejects_invalid_vertical_versions_and_disabled_schema(self):
        with self.assertRaises(ValueError):
            replace(self.schema, vertical="Baby Bad")
        with self.assertRaises(ValueError):
            replace(self.schema, schema_version=" ")
        disabled = replace(self.schema, schema_version="intake-test-disabled", enabled=False)
        register_intake_schema(disabled)
        self.addCleanup(unregister_intake_schema, self.vertical, disabled.schema_version)
        result = validate_intake(self.vertical, {}, intake_version=disabled.schema_version)
        self.assertFalse(result.valid)
        self.assertEqual(result.errors[0].code, "unsupported_schema")

    def test_validation_required_alias_defaults_enums_ranges_and_unknowns(self):
        missing = validate_intake(self.vertical, {})
        self.assertEqual(missing.errors[0].code, "required")
        valid = normalize_intake(self.vertical, {"name": " soft ", "weight": "0", "enabled": "false"})
        self.assertTrue(valid.valid)
        self.assertEqual(valid.canonical_intent.naming_styles, ("Soft",))
        self.assertEqual(valid.canonical_intent.priority_weights["importance"], 0.0)
        self.assertFalse(valid.canonical_intent.extensions["enabled"])
        self.assertEqual(valid.applied_aliases[0]["alias"], "name")
        self.assertFalse(validate_intake(self.vertical, {"label": "Unknown"}).valid)
        self.assertFalse(validate_intake(self.vertical, {"label": "Soft", "weight": 2}).valid)
        self.assertFalse(validate_intake(self.vertical, {"label": "Soft", "extra": True}).valid)

    def test_validation_bounds_malformed_nonfinite_and_collections(self):
        cases = (
            {"label": "S" * 21},
            {"label": "Soft", "weight": math.inf},
            {"label": "Soft", "enabled": "perhaps"},
            {"label": "Soft", "items": ["one", "two", "three"]},
            {"label": "Soft", "items": {"nested": "invalid"}},
            {"label": object()},
        )
        for payload in cases:
            with self.subTest(payload_type=type(next(iter(payload.values()))).__name__):
                self.assertFalse(validate_intake(self.vertical, payload).valid)

    def test_normalization_conflicts_determinism_json_and_no_value_leakage(self):
        secret = "private-customer-value"
        conflict = normalize_intake(self.vertical, {"label": "Soft", "name": "Strong"})
        self.assertFalse(conflict.valid)
        self.assertEqual(conflict.validation.errors[-1].code, "conflicting_aliases")
        oversized = normalize_intake(self.vertical, {"label": secret * 10})
        self.assertNotIn(secret, oversized.serialize())
        first = normalize_intake(self.vertical, {"old_name": " strong ", "enabled": 0})
        second = normalize_intake(self.vertical, {"enabled": 0, "old_name": " strong "})
        self.assertEqual(first.serialize(), second.serialize())
        json.loads(first.serialize())
        self.assertTrue(first.deprecation_warnings)

    def test_canonical_core_is_generic_immutable_and_baby_extensions_are_isolated(self):
        payload = {"gender": "Girl", "style": "Classic", "sound": "Soft", "partner_alignment": "shared preference"}
        original = dict(payload)
        normalized = normalize_intake("baby", payload)
        self.assertTrue(normalized.valid)
        self.assertEqual(payload, original)
        self.assertEqual(normalized.canonical_intent.vertical, "baby")
        self.assertEqual(normalized.canonical_intent.extensions, {"partner_alignment": "shared preference"})
        generic = CanonicalNamingIntent(vertical="pet", naming_target="pet name")
        self.assertEqual(generic.gender_context, "")
        self.assertEqual(generic.extensions, {})
        self.assertEqual(generic.serialize(), generic.serialize())

    def test_current_baby_and_legacy_result_link_inputs_normalize(self):
        current = build_brief(BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        legacy = build_brief(BABY, {"baby_gender": "Girl", "name_style": "Classic", "sound_preference": "Soft"})
        self.assertEqual(current.inputs, legacy.inputs)
        self.assertEqual(current.canonical_intent, legacy.canonical_intent)
        self.assertEqual(current.intake_metadata["intake_schema_version"], BABY_INTAKE_VERSION)
        self.assertEqual(current.intake_metadata["normalizer_version"], BABY_NORMALIZER_VERSION)
        self.assertEqual(current.intake_metadata["intake_adapter_version"], BABY_INTAKE_ADAPTER_VERSION)

    def test_migration_identity_chain_missing_cycle_and_warnings(self):
        identity = migrate_intake(self.vertical, {"label": "Soft"}, "same", "same")
        self.assertEqual(identity.payload, {"label": "Soft"})
        register_intake_migration(IntakeMigration(self.vertical, "migration-a", "migration-b", lambda p: ({**p, "step": 1}, ["deprecated field mapped"]), {}))
        register_intake_migration(IntakeMigration(self.vertical, "migration-b", "migration-c", lambda p: ({**p, "done": True}, []), {}))
        migrated = migrate_intake(self.vertical, {}, "migration-a", "migration-c")
        self.assertEqual(migrated.history, ("migration-a->migration-b", "migration-b->migration-c"))
        self.assertEqual(migrated.warnings, ("deprecated field mapped",))
        self.assertEqual(migrated.to_dict(), migrated.to_dict())
        with self.assertRaises(IntakeMigrationError):
            migrate_intake(self.vertical, {}, "missing", "migration-c")
        with self.assertRaisesRegex(ValueError, "cycle"):
            register_intake_migration(IntakeMigration(self.vertical, "migration-c", "migration-a", lambda p: (p, []), {}))

        baby = normalize_intake(
            "baby",
            {"baby_gender": "Girl", "name_style": "Classic", "sound_preference": "Soft"},
            intake_version=BABY_LEGACY_INTAKE_VERSION,
        )
        self.assertTrue(baby.valid)
        self.assertEqual(baby.migration_source_version, BABY_LEGACY_INTAKE_VERSION)
        self.assertEqual(baby.migration_destination_version, BABY_INTAKE_VERSION)
        self.assertTrue(baby.migration_warnings)

    def test_comparison_added_removed_changed_weights_and_stability(self):
        left = normalize_intake(self.vertical, {"label": "Soft", "weight": 0})
        right = normalize_intake(self.vertical, {"label": "Strong", "weight": 1, "enabled": True})
        comparison = compare_normalized_intakes(left, right)
        self.assertIn("naming_styles", comparison.changed_fields)
        self.assertEqual(comparison.changed_priority_weights, ("importance",))
        self.assertEqual(comparison.serialize(), comparison.serialize())
        json.loads(comparison.serialize())

    def test_evaluation_optional_intake_expectations_and_existing_pack(self):
        pack = load_evaluation_pack(DEFAULT_PACK_ROOT / "baby")
        self.assertEqual(len(pack), 10)
        raw = json.loads((DEFAULT_PACK_ROOT / "baby" / "classic_soft_familiar_girl.json").read_text(encoding="utf-8"))
        raw.update({
            "intake_schema_version": BABY_INTAKE_VERSION,
            "expected_canonical_intent_attributes": {"gender_context": "Girl"},
            "expected_normalization_warnings": [],
            "expected_migration_behavior": {},
        })
        fixture = validate_fixture(raw)
        evaluated = evaluate_generated_fixture(fixture)
        self.assertEqual(evaluated.intake_schema_version, BABY_INTAKE_VERSION)
        self.assertIn("canonical_intent_expectations", {row.criterion for row in evaluated.criterion_results})

    def test_audit_metadata_is_versioned_without_canonical_intent_persistence(self):
        brief = build_brief(BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft", "notes": "private family note"})
        results = generate_names(BABY, brief, use_ai=False)
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "audit.sqlite3"
            save_session("intake-audit", "baby", brief, results, db_path=db_path)
            summary = get_recent_audit_sessions("baby", db_path=db_path)[0]
            self.assertEqual(summary["intake_schema_version"], BABY_INTAKE_VERSION)
            import sqlite3
            with closing(sqlite3.connect(db_path)) as connection:
                stored = json.loads(connection.execute("SELECT brief_json FROM sessions").fetchone()[0])
            self.assertNotIn("canonical_intent", stored)
            self.assertEqual(stored["intake_metadata"]["canonical_intent_version"], "canonical-naming-intent-v1")

    def test_generation_quality_and_pet_ordering_are_unchanged(self):
        baby_brief = build_brief(BABY, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        legacy_brief = NamingBrief(vertical="baby", inputs=dict(baby_brief.inputs), avoid=[], notes="")
        self.assertEqual(
            [item.name for item in generate_names(BABY, baby_brief, use_ai=False)],
            [item.name for item in generate_names(BABY, legacy_brief, use_ai=False)],
        )
        pet_brief = build_brief(PET, {"style": "Warm", "pet_type": "Dog", "vibe": "Gentle"})
        self.assertEqual(
            [item.name for item in generate_names(PET, pet_brief, use_ai=False)],
            ["Rosie", "Juniper", "Ollie", "Remy", "Lottie", "Theo", "Maple", "Clover"],
        )


if __name__ == "__main__":
    unittest.main()
