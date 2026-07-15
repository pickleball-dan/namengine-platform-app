"""Thin Flask shell for the shared NamEngine platform."""

from __future__ import annotations

import logging
import os
from threading import Lock, Thread
from hashlib import sha1
from urllib.parse import urlencode

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, url_for

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - Render uses real env vars; local dev may skip dotenv
    load_dotenv = None

from namengine import CONTRACT_VERSION
from namengine.core import (
    ReactionError,
    build_brief,
    build_compare_items,
    build_reaction,
    build_taste_profile,
    build_trust_cue,
    compare_contrast_groups,
    ensure_keepsake_for_chosen,
    generate_names,
    get_reaction_counts,
    is_ai_generation_configured,
    get_chosen_snapshot,
    get_database_path,
    get_session_snapshot,
    keepsake_preview_for_chosen,
    get_taste_profile,
    keepsake_runtime_config,
    load_taste_engine_fixtures,
    prepare_keepsake_for_chosen,
    refine_session,
    run_taste_engine_fixture_set,
    save_reaction,
    save_chosen_name,
    save_session,
    StorageError,
    summarize_taste_engine_eval,
    vertical_theme_style,
)
from namengine.core.name_facts import build_name_fact_card
from namengine.core.schemas import NameResult, NamingBrief, ValidationResult, to_plain_data
from namengine.core.validation import filter_results_for_brief
from namengine.verticals import VERTICALS, get_vertical


logger = logging.getLogger(__name__)
_portrait_jobs: set[str] = set()
_portrait_jobs_lock = Lock()
MIN_REACTIONS_FOR_REFINEMENT = 3


def grouped_questions(vertical) -> list[dict]:
    groups: list[dict] = []
    by_section: dict[str, list] = {}

    for question in vertical.intake_questions:
        section = question.section or "Tell us what matters"
        if section not in by_section:
            by_section[section] = []
            groups.append({"title": section, "questions": by_section[section]})
        by_section[section].append(question)

    return groups


def feeling_section_titles(vertical) -> list[str]:
    return [group["title"] for group in grouped_questions(vertical) if group["title"] != "Tell us what matters"]


def feelings_scale_enabled(vertical) -> bool:
    return len(feeling_section_titles(vertical)) >= 2


def section_strength_field(section_title: str) -> str:
    return "taste_strength_" + slugify_for_field(section_title)


def slugify_for_field(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.lower()).strip("_") or "section"


def feeling_center_icon(vertical, source=None) -> dict[str, str]:
    source = source or {}
    if vertical.slug == "baby":
        return {"kind": "baby", "noun": "baby", "label": "baby"}
    if vertical.slug == "business":
        return {"kind": "building", "noun": "building", "label": "building"}
    if vertical.slug == "product":
        return {"kind": "product", "noun": "product", "label": "product"}
    if vertical.slug == "pet":
        pet_type = str(source.get("pet_type") or source.get("species") or "pet").strip().lower()
        pet_kind = pet_type if pet_type in {"dog", "cat", "horse", "bird", "rabbit", "reptile"} else "other"
        noun = pet_kind if pet_kind != "other" else "pet"
        return {"kind": f"pet-{pet_kind}", "noun": noun, "label": noun}
    return {"kind": "namengine", "noun": "mark", "label": "NamEngine mark"}


def apply_taste_strength_inputs(brief, source) -> None:
    strengths: dict[str, int] = {}
    for key, value in source.items():
        if not str(key).startswith("taste_strength_"):
            continue
        try:
            strength = int(float(value))
        except (TypeError, ValueError):
            continue
        strength = max(0, min(100, strength))
        brief.inputs[str(key)] = strength
        strengths[str(key)[len("taste_strength_") :]] = strength

    if strengths:
        strongest = max(strengths.items(), key=lambda item: item[1])
        readable = strongest[0].replace("_", " ")
        brief.inputs["taste_focus"] = (
            f"Let {readable} guide this list most while still honoring every intake answer."
        )


def intake_edit_url(vertical, brief, field_id: str) -> str:
    query = {
        key: value
        for key, value in brief.inputs.items()
        if key not in {"species", "personality"}
        and not str(key).startswith("taste_")
        and value not in ("", None)
    }
    query["edit"] = field_id
    return f"{vertical.route_prefix}?{urlencode(query)}"


def feelings_scale_edit_url(vertical, brief) -> str:
    query = {
        key: value
        for key, value in brief.inputs.items()
        if key not in {"species", "personality", "taste_focus"} and value not in ("", None)
    }
    return f"{vertical.route_prefix}/feelings?{urlencode(query)}"


def display_brief_items(vertical, brief) -> list[dict[str, str]]:
    hidden_keys = {"species", "personality"}
    label_overrides = {
        "pet_type": "Pet",
        "pet_gender": "Gender",
        "pet_breed": "Breed",
        "pet_color": "Color",
        "pet_life_stage": "Age",
        "notes": "About them",
        "discovery_style": "Discovery",
        "style": "Style",
        "timeless_vs_distinctive": "Timeless vs distinctive",
        "familiarity_preference": "Familiarity",
        "pronunciation_importance": "Callability",
        "vibe": "Personality",
        "cultural_context": "Inspiration",
        "partner_alignment": "Torn between",
        "business_description": "Business",
        "industry": "Category",
        "stage": "Stage",
        "audience": "Audience",
        "name_shape": "Name shape",
        "domain_preference": "Domain priority",
        "product_description": "Product",
        "category": "Category",
        "sales_channel": "Sales channel",
    }

    items: list[dict[str, str]] = []
    for key, value in brief.inputs.items():
        if key in hidden_keys or str(key).startswith("taste_") or value in ("", None):
            continue
        label = label_overrides.get(key, key.replace("_", " ").title())
        items.append(
            {
                "key": key,
                "label": label,
                "value": str(value),
                "edit_url": intake_edit_url(vertical, brief, key),
            }
        )
    return items


def result_detail_from_session(session_id: str, result_id: str) -> dict | None:
    snapshot = get_session_snapshot(session_id)
    if snapshot is None:
        return None

    for row in snapshot["results"]:
        if row["id"] == result_id:
            return {
                "session": snapshot["session"],
                "result": json_loads(row["result_json"]),
                "reaction_counts": snapshot["reaction_counts"],
                "taste_profile": _taste_profile_from_snapshot(snapshot),
            }
    return None


def brief_query_string(brief_json: str) -> str:
    brief = json_loads(brief_json)
    inputs = {
        key: value
        for key, value in brief.get("inputs", {}).items()
        if value not in ("", None)
    }
    return urlencode(inputs)


def make_session_id(vertical_slug: str, query_string: bytes) -> str:
    digest = sha1(vertical_slug.encode("utf-8") + b":" + query_string).hexdigest()
    return f"{vertical_slug}-{digest[:12]}"


def _query_string_from_mapping(source) -> str:
    return urlencode(
        {
            key: value
            for key, value in source.items()
            if value not in ("", None)
        }
    )


def _normalize_other_inputs(source) -> dict[str, str]:
    normalized = {
        key: value
        for key, value in source.items()
        if value not in ("", None) and not str(key).endswith("_other")
    }
    for key, value in source.items():
        if not str(key).endswith("_other"):
            continue
        base_key = str(key)[: -len("_other")]
        other_value = str(value or "").strip()
        if other_value and normalized.get(base_key) == "Other":
            normalized[base_key] = other_value
    return normalized


def _reaction_total(reaction_counts: dict[str, int]) -> int:
    return sum(int(reaction_counts.get(value, 0)) for value in ("love", "maybe", "no"))


def _brief_from_snapshot(snapshot: dict) -> NamingBrief:
    return NamingBrief(**json_loads(snapshot["session"]["brief_json"]))


def _render_results_snapshot(
    session_id: str,
    *,
    status: int = 200,
    refinement_error: str | None = None,
):
    snapshot = get_session_snapshot(session_id)
    if snapshot is None:
        abort(404)

    vertical = get_vertical(snapshot["session"]["vertical"])
    names = _names_from_snapshot(snapshot)
    brief = _brief_from_snapshot(snapshot)
    reaction_counts = get_reaction_counts(session_id)
    return (
        render_template(
            "results.html",
            vertical=vertical,
            brief=brief,
            names=names,
            trust_cue=build_trust_cue(names),
            session_id=session_id,
            reaction_counts=reaction_counts,
            reaction_total=_reaction_total(reaction_counts),
            min_reactions_for_refinement=MIN_REACTIONS_FOR_REFINEMENT,
            taste_profile=_taste_profile_from_snapshot(snapshot),
            round_number=int(snapshot["session"]["round_number"]),
            parent_session_id=snapshot["session"]["parent_session_id"],
            original_mode=session_id.startswith("pet-original"),
            refinement_error=refinement_error,
        ),
        status,
    )


def save_feedback_submission(source) -> None:
    import json

    feedback_path = get_database_path().parent / "feedback.jsonl"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    allowed_keys = (
        "name",
        "tester_type",
        "overall_rating",
        "liked_most",
        "confusing",
        "missing",
    )
    payload = {
        key: str(source.get(key, "")).strip()
        for key in allowed_keys
        if str(source.get(key, "")).strip()
    }
    if not payload:
        return
    with feedback_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def create_app() -> Flask:
    if load_dotenv is not None:
        load_dotenv()
    app = Flask(__name__)

    @app.context_processor
    def inject_platform_context():
        return {
            "contract_version": CONTRACT_VERSION,
            "verticals": VERTICALS,
            "vertical_theme_style": vertical_theme_style,
            "grouped_questions": grouped_questions,
            "display_brief_items": display_brief_items,
            "intake_edit_url": intake_edit_url,
            "feelings_scale_edit_url": feelings_scale_edit_url,
            "feelings_scale_enabled": feelings_scale_enabled,
            "feeling_section_titles": feeling_section_titles,
            "section_strength_field": section_strength_field,
            "feeling_center_icon": feeling_center_icon,
        }

    app.add_template_filter(brief_query_string, "brief_query_string")

    @app.get("/")
    def index():
        return render_template("index.html", verticals=VERTICALS)

    @app.get("/baby/beta")
    def baby_beta():
        return render_template(
            "baby_beta.html",
            vertical=get_vertical("baby"),
            stripe_payment_link=os.getenv("NAMENGINE_BABY_BETA_PAYMENT_LINK", "").strip(),
            beta_price=os.getenv("NAMENGINE_BABY_BETA_PRICE", "$19").strip() or "$19",
            paid=request.args.get("paid") == "1",
        )

    @app.get("/privacy")
    def privacy_policy():
        return render_template("legal_privacy.html")

    @app.get("/terms")
    def terms_of_use():
        return render_template("legal_terms.html")

    @app.get("/disclaimers")
    def disclaimers():
        return render_template("legal_disclaimers.html")

    @app.get("/data-protection")
    def data_protection():
        return render_template("legal_data_protection.html")

    @app.get("/<vertical_slug>")
    def intake(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        return render_template("intake.html", vertical=vertical)


    @app.get("/<vertical_slug>/feelings")
    def feelings_scale(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        if not feelings_scale_enabled(vertical):
            query = _query_string_from_mapping(_normalize_other_inputs(request.args.to_dict(flat=True)))
            return redirect(f"{vertical.route_prefix}/results?{query}")

        source = _normalize_other_inputs(request.args.to_dict(flat=True))
        brief = build_brief(vertical, source)
        return render_template(
            "feelings_scale.html",
            vertical=vertical,
            brief=brief,
            source=source,
            sections=feeling_section_titles(vertical),
            center_icon=feeling_center_icon(vertical, source),
        )

    @app.get("/pet/original")
    def pet_original():
        vertical = get_vertical("pet")
        return render_template("original_intake.html", vertical=vertical)

    @app.post("/pet/original/results")
    def pet_original_submit():
        query = _query_string_from_mapping(_normalize_other_inputs(request.form))
        return redirect(f"{url_for('pet_original_results')}?{query}")

    @app.get("/pet/original/results")
    def pet_original_results():
        vertical = get_vertical("pet")
        source_for_id = _normalize_other_inputs(request.args.to_dict(flat=True))
        source = dict(source_for_id)
        source["discovery_style"] = source.get("discovery_style") or "Completely original"
        source["original_mode"] = "true"
        brief = build_brief(vertical, source)
        apply_taste_strength_inputs(brief, source)
        for key in ("starting_letter", "length_preference", "avoid_feel", "original_mode"):
            if source.get(key):
                brief.inputs[key] = source[key]
        session_id = make_session_id("pet-original", _query_string_from_mapping(source_for_id).encode("utf-8"))
        snapshot = get_session_snapshot(session_id)
        if snapshot and snapshot["results"]:
            names = _names_from_snapshot(snapshot)
        else:
            names = generate_names(vertical, brief, use_ai=_should_use_ai_for_vertical(vertical))
            save_session(session_id, vertical.slug, brief, names)
        taste_profile_row = get_taste_profile(session_id)
        return render_template(
            "results.html",
            vertical=vertical,
            brief=brief,
            names=names,
            trust_cue=build_trust_cue(names),
            session_id=session_id,
            reaction_counts=get_reaction_counts(session_id),
            taste_profile=json_loads(taste_profile_row["profile_json"]) if taste_profile_row else None,
            round_number=1,
            parent_session_id=None,
            original_mode=True,
        )

    def _create_results_session(vertical, source: dict[str, str]) -> str:
        source = _normalize_other_inputs(source)
        brief = build_brief(vertical, source)
        apply_taste_strength_inputs(brief, source)

        session_id = make_session_id(
            vertical.slug,
            _query_string_from_mapping(source).encode("utf-8"),
        )
        snapshot = get_session_snapshot(session_id)
        if snapshot and snapshot["results"]:
            names = _names_from_snapshot(snapshot)
            if not _cached_names_match_current_rules(vertical, brief, names):
                names = generate_names(vertical, brief, use_ai=_should_use_ai_for_vertical(vertical))
                save_session(session_id, vertical.slug, brief, names)
        else:
            names = generate_names(vertical, brief, use_ai=_should_use_ai_for_vertical(vertical))
            save_session(session_id, vertical.slug, brief, names)
        return session_id

    @app.post("/<vertical_slug>/results")
    def submit_results(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        session_id = _create_results_session(vertical, request.form.to_dict(flat=True))
        return redirect(url_for("session_results", session_id=session_id))

    @app.get("/<vertical_slug>/results")
    def results(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        source = _normalize_other_inputs(request.args.to_dict(flat=True))
        brief = build_brief(vertical, source)
        apply_taste_strength_inputs(brief, source)

        session_id = make_session_id(vertical.slug, _query_string_from_mapping(source).encode("utf-8"))
        snapshot = get_session_snapshot(session_id)
        if snapshot and snapshot["results"]:
            names = _names_from_snapshot(snapshot)
            if not _cached_names_match_current_rules(vertical, brief, names):
                names = generate_names(vertical, brief, use_ai=_should_use_ai_for_vertical(vertical))
                save_session(session_id, vertical.slug, brief, names)
        else:
            names = generate_names(vertical, brief, use_ai=_should_use_ai_for_vertical(vertical))
            save_session(session_id, vertical.slug, brief, names)
        taste_profile_row = get_taste_profile(session_id)
        return render_template(
            "results.html",
            vertical=vertical,
            brief=brief,
            names=names,
            trust_cue=build_trust_cue(names),
            session_id=session_id,
            reaction_counts=get_reaction_counts(session_id),
            taste_profile=json_loads(taste_profile_row["profile_json"]) if taste_profile_row else None,
            round_number=1,
            parent_session_id=None,
            original_mode=False,
        )

    @app.get("/results/session/<session_id>")
    def session_results(session_id: str):
        return _render_results_snapshot(session_id)

    @app.post("/api/react")
    def react():
        payload = request.get_json(silent=True) or request.form

        try:
            reaction = build_reaction(
                session_id=str(payload.get("session_id", "")),
                result_id=str(payload.get("result_id", "")),
                value=str(payload.get("value", "")),
            )
        except ReactionError as exc:
            return jsonify({"error": str(exc)}), 400

        try:
            save_reaction(reaction)
        except StorageError as exc:
            return jsonify({"error": str(exc)}), 404

        taste_profile = build_taste_profile(reaction.session_id)
        return jsonify(
            {
                "reaction": to_plain_data(reaction),
                "reaction_counts": get_reaction_counts(reaction.session_id),
                "taste_profile": to_plain_data(taste_profile),
            }
        ), 201

    @app.post("/choose")
    def choose():
        session_id = str(request.form.get("session_id", ""))
        result_id = str(request.form.get("result_id", ""))
        if not session_id or not result_id:
            abort(400)

        try:
            chosen = save_chosen_name(session_id, result_id)
        except StorageError:
            abort(404)

        _queue_keepsake_generation(chosen.id)
        return redirect(url_for("chosen_name", chosen_id=chosen.id))

    @app.post("/refine")
    def refine():
        session_id = str(request.form.get("session_id", ""))
        instruction = str(request.form.get("instruction", ""))
        if not session_id:
            abort(400)

        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            abort(404)

        reaction_counts = get_reaction_counts(session_id)
        if _reaction_total(reaction_counts) < MIN_REACTIONS_FOR_REFINEMENT:
            remaining = MIN_REACTIONS_FOR_REFINEMENT - _reaction_total(reaction_counts)
            noun = "name" if remaining == 1 else "names"
            return _render_results_snapshot(
                session_id,
                status=400,
                refinement_error=f"React to {remaining} more {noun} before generating the next list.",
            )

        vertical = get_vertical(snapshot["session"]["vertical"])

        try:
            child_session_id, brief, names = refine_session(
                session_id,
                vertical,
                instruction=instruction,
                use_ai=_should_use_ai_for_vertical(vertical),
            )
        except StorageError:
            abort(404)

        child_snapshot = get_session_snapshot(child_session_id)
        round_number = int(child_snapshot["session"]["round_number"])
        taste_profile = _taste_profile_from_snapshot(child_snapshot)
        if request.headers.get("X-NamEngine-Progress") == "1":
            return redirect(url_for("session_results", session_id=child_session_id))

        return render_template(
            "results.html",
            vertical=vertical,
            brief=brief,
            names=names,
            trust_cue=build_trust_cue(names),
            session_id=child_session_id,
            reaction_counts=get_reaction_counts(child_session_id),
            taste_profile=taste_profile,
            round_number=round_number,
            parent_session_id=session_id,
            original_mode=False,
        )

    @app.get("/compare/<session_id>")
    def compare(session_id: str):
        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            abort(404)

        vertical = get_vertical(snapshot["session"]["vertical"])
        items = build_compare_items(session_id)
        taste_profile = _taste_profile_from_snapshot(snapshot)
        return render_template(
            "compare.html",
            vertical=vertical,
            session=snapshot["session"],
            items=items,
            taste_profile=taste_profile,
        )

    @app.get("/share/<session_id>")
    def shared_shortlist(session_id: str):
        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            return render_template(
                "share_missing.html",
                session_id=session_id,
                vertical=get_vertical("pet") if session_id.startswith("pet") else None,
            ), 410

        vertical = get_vertical(snapshot["session"]["vertical"])
        names = [json_loads(row["result_json"]) for row in snapshot["results"]]
        brief = json_loads(snapshot["session"]["brief_json"])
        taste_profile = _taste_profile_from_snapshot(snapshot)
        return render_template(
            "shared_shortlist.html",
            vertical=vertical,
            session=snapshot["session"],
            brief=brief,
            names=names,
            reaction_counts=snapshot["reaction_counts"],
            taste_profile=taste_profile,
        )

    @app.get("/dev/engine-audit/<session_id>")
    def engine_audit(session_id: str):
        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            abort(404)

        vertical = get_vertical(snapshot["session"]["vertical"])
        return render_template(
            "engine_audit.html",
            vertical=vertical,
            session=snapshot["session"],
            brief=json_loads(snapshot["session"]["brief_json"]),
            names=_names_from_snapshot(snapshot),
            reaction_counts=get_reaction_counts(session_id),
            audit=_engine_audit_from_snapshot(snapshot),
        )

    @app.get("/dev/eval-report")
    def eval_report():
        fixtures = load_taste_engine_fixtures()
        limit = _positive_int(request.args.get("limit"))
        use_ai = request.args.get("ai") == "1"
        if limit:
            fixtures = fixtures[:limit]

        results = run_taste_engine_fixture_set(fixtures, use_ai=use_ai)
        summary = summarize_taste_engine_eval(results)
        contrasts = compare_contrast_groups(results)
        return render_template(
            "eval_report.html",
            fixtures=fixtures,
            results=results,
            summary=summary,
            contrasts=contrasts,
            use_ai=use_ai,
            limit=limit,
        )

    @app.get("/<vertical_slug>/name/<session_id>/<result_id>")
    def name_detail(vertical_slug: str, session_id: str, result_id: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        detail = result_detail_from_session(session_id, result_id)
        if detail is None:
            abort(404)

        vertical = get_vertical(detail["session"]["vertical"])
        if vertical.slug != vertical_slug:
            abort(404)

        return render_template(
            "name_detail.html",
            vertical=vertical,
            session=detail["session"],
            result=detail["result"],
            name_fact_card=build_name_fact_card(vertical.slug, detail["result"]),
            reaction_counts=detail["reaction_counts"],
            taste_profile=detail["taste_profile"],
        )

    @app.get("/chosen/<chosen_id>")
    def chosen_name(chosen_id: str):
        snapshot = get_chosen_snapshot(chosen_id)
        if snapshot is None or snapshot["result"] is None:
            abort(404)

        result = to_plain_data(json_loads(snapshot["result"]["result_json"]))
        _queue_keepsake_generation(chosen_id)
        portrait = _keepsake_preview(chosen_id)
        return render_template(
            "chosen.html",
            vertical=get_vertical(snapshot["chosen"]["vertical"]),
            chosen=snapshot["chosen"],
            result=result,
            name_fact_card=build_name_fact_card(str(snapshot["chosen"]["vertical"]), result),
            session=snapshot["session"],
            portrait=portrait,
        )

    @app.get("/generated/pet-portraits/<filename>")
    def generated_pet_portrait(filename: str):
        portrait_dir = get_database_path().parent / "generated_pet_portraits"
        return send_from_directory(portrait_dir, filename)

    @app.get("/generated/baby-keepsakes/<filename>")
    def generated_baby_keepsake(filename: str):
        keepsake_dir = get_database_path().parent / "generated_baby_keepsakes"
        return send_from_directory(keepsake_dir, filename)

    @app.get("/api/chosen/<chosen_id>/portrait")
    def chosen_portrait_status(chosen_id: str):
        snapshot = get_chosen_snapshot(chosen_id)
        if snapshot is None:
            abort(404)

        vertical_slug = str(snapshot["chosen"].get("vertical", ""))
        portrait = _keepsake_preview(chosen_id)
        if portrait and portrait.get("status") not in {"ready", "not_configured", "failed"}:
            _queue_keepsake_generation(chosen_id)
        return jsonify(
            {
                "chosen_id": chosen_id,
                "runtime": keepsake_runtime_config(vertical_slug),
                "portrait": portrait or {"status": "not_attempted"},
            }
        )

    @app.route("/feedback", methods=["GET", "POST"])
    def feedback():
        submitted = request.method == "POST"
        if submitted:
            save_feedback_submission(request.form)
        return render_template(
            "feedback.html",
            vertical=get_vertical("pet"),
            submitted=submitted,
            form_data=request.form if submitted else {},
        )

    return app


def json_loads(value: str):
    import json

    return json.loads(value)


def _taste_profile_from_snapshot(snapshot: dict):
    row = snapshot.get("taste_profile")
    if not row:
        return None
    return json_loads(row["profile_json"])


def _names_from_snapshot(snapshot: dict) -> list[NameResult]:
    names: list[NameResult] = []
    for row in snapshot["results"]:
        data = json_loads(row["result_json"])
        data["validation"] = [
            item if isinstance(item, ValidationResult) else ValidationResult(**item)
            for item in data.get("validation", [])
        ]
        names.append(NameResult(**data))
    return names


def _engine_audit_from_snapshot(snapshot: dict) -> dict:
    names = _names_from_snapshot(snapshot)
    first = names[0] if names else None
    metadata = first.metadata if first else {}
    ai_calls = metadata.get("ai_calls") if isinstance(metadata.get("ai_calls"), list) else []
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    total_latency_ms = 0
    for call in ai_calls:
        if not isinstance(call, dict):
            continue
        try:
            total_latency_ms += int(call.get("latency_ms") or 0)
        except (TypeError, ValueError):
            pass
        usage = call.get("usage") if isinstance(call.get("usage"), dict) else {}
        for key in usage_totals:
            try:
                usage_totals[key] += int(usage.get(key) or 0)
            except (TypeError, ValueError):
                pass

    providers = sorted(
        {
            str(name.metadata.get("provider") or name.metadata.get("source") or "unknown")
            for name in names
        }
    )
    return {
        "generation_id": metadata.get("generation_id") or snapshot["session"]["id"],
        "prompt_version": metadata.get("prompt_version", "unknown"),
        "engine_pipeline": metadata.get("engine_pipeline", "unknown"),
        "model": metadata.get("model", "unknown"),
        "providers": providers,
        "ai_calls": ai_calls,
        "usage_totals": usage_totals,
        "total_latency_ms": total_latency_ms,
        "taste_strategy": metadata.get("taste_strategy", {}),
        "candidate_pool": metadata.get("candidate_pool", []),
        "rejected_candidates": metadata.get("rejected_candidates", []),
        "result_metadata": metadata,
    }


def _positive_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _ai_primary_verticals() -> set[str]:
    raw_value = os.getenv("NAMENGINE_AI_PRIMARY_VERTICALS", "baby")
    if raw_value.strip().lower() in {"", "none", "off", "false", "0"}:
        return set()
    if raw_value.strip().lower() in {"all", "*"}:
        return set(VERTICALS)
    return {
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    }


def _should_use_ai_for_vertical(vertical) -> bool:
    return vertical.slug in _ai_primary_verticals() and is_ai_generation_configured()


def _result_is_ai_sourced(name: NameResult) -> bool:
    source = str(name.metadata.get("source", "")).lower()
    provider = str(name.metadata.get("provider", "")).lower()
    return source in {"openai", "ai"} or provider in {"openai", "ai"}


def _cached_names_match_current_rules(
    vertical,
    brief: NamingBrief,
    names: list[NameResult],
) -> bool:
    if _should_use_ai_for_vertical(vertical) and not all(_result_is_ai_sourced(name) for name in names):
        return False
    if vertical.slug == "baby":
        if len(filter_results_for_brief(vertical, brief, names)) != len(names):
            return False
        return all(
            "baby_gender_direction" in {item.module for item in name.validation}
            for name in names
        )
    if vertical.slug == "business":
        return all(
            "business_domain" in {item.module for item in name.validation}
            and isinstance(name.metadata.get("domain_info"), dict)
            for name in names
        )
    return True


def _try_generate_keepsake(chosen_id: str):
    snapshot = get_chosen_snapshot(chosen_id)
    if snapshot is None or snapshot["result"] is None:
        return None
    if snapshot["chosen"].get("vertical") not in {"pet", "baby"}:
        return None

    result = to_plain_data(json_loads(snapshot["result"]["result_json"]))
    try:
        return ensure_keepsake_for_chosen(
            snapshot["chosen"],
            result,
            snapshot["session"],
        )
    except Exception as exc:
        logger.warning(
            "Keepsake generation failed for %s: %s: %s",
            chosen_id,
            exc.__class__.__name__,
            str(exc)[:500],
        )
        return None


def _keepsake_preview(chosen_id: str):
    snapshot = get_chosen_snapshot(chosen_id)
    if snapshot is None or snapshot["result"] is None:
        return None
    if snapshot["chosen"].get("vertical") not in {"pet", "baby"}:
        return None

    return keepsake_preview_for_chosen(snapshot["chosen"], snapshot["session"])


def _queue_keepsake_generation(chosen_id: str):
    snapshot = get_chosen_snapshot(chosen_id)
    if snapshot is None or snapshot["result"] is None:
        return None
    if snapshot["chosen"].get("vertical") not in {"pet", "baby"}:
        return None

    result = to_plain_data(json_loads(snapshot["result"]["result_json"]))
    portrait = prepare_keepsake_for_chosen(
        snapshot["chosen"],
        result,
        snapshot["session"],
    )
    if not portrait or portrait.get("status") in {"ready", "not_configured", "failed"}:
        return portrait

    with _portrait_jobs_lock:
        if chosen_id in _portrait_jobs:
            return portrait
        _portrait_jobs.add(chosen_id)

    def run() -> None:
        try:
            _try_generate_keepsake(chosen_id)
        finally:
            with _portrait_jobs_lock:
                _portrait_jobs.discard(chosen_id)

    Thread(target=run, daemon=True).start()
    return portrait


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
