"""Thin Flask shell for the shared NamEngine platform."""

from __future__ import annotations

from hashlib import sha1
from urllib.parse import urlencode

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from namengine import CONTRACT_VERSION
from namengine.core import (
    ReactionError,
    build_brief,
    build_compare_items,
    build_reaction,
    build_taste_profile,
    build_trust_cue,
    generate_names,
    get_reaction_counts,
    get_chosen_snapshot,
    get_session_snapshot,
    get_taste_profile,
    refine_session,
    save_reaction,
    save_chosen_name,
    save_session,
    StorageError,
    vertical_theme_style,
)
from namengine.core.schemas import to_plain_data
from namengine.verticals import VERTICALS, get_vertical


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


def intake_edit_url(vertical, brief, field_id: str) -> str:
    query = {
        key: value
        for key, value in brief.inputs.items()
        if key not in {"species", "personality"} and value not in ("", None)
    }
    query["edit"] = field_id
    return f"{vertical.route_prefix}?{urlencode(query)}"


def display_brief_items(vertical, brief) -> list[dict[str, str]]:
    hidden_keys = {"species", "personality"}
    label_overrides = {
        "pet_type": "Pet",
        "pet_gender": "Gender",
        "notes": "About them",
        "discovery_style": "Discovery",
        "style": "Style",
        "timeless_vs_distinctive": "Timeless vs distinctive",
        "familiarity_preference": "Familiarity",
        "pronunciation_importance": "Callability",
        "vibe": "Personality",
        "cultural_context": "Inspiration",
        "partner_alignment": "Torn between",
    }

    items: list[dict[str, str]] = []
    for key, value in brief.inputs.items():
        if key in hidden_keys or value in ("", None):
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


def create_app() -> Flask:
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
        }

    app.add_template_filter(brief_query_string, "brief_query_string")

    @app.get("/")
    def index():
        return render_template("index.html", verticals=VERTICALS)

    @app.get("/<vertical_slug>")
    def intake(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        return render_template("intake.html", vertical=vertical)

    @app.get("/<vertical_slug>/results")
    def results(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        brief = build_brief(vertical, request.args)
        if vertical.slug != "pet":
            abort(501)

        names = generate_names(vertical, brief)
        session_id = make_session_id(vertical.slug, request.query_string)
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
        )

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

        vertical = get_vertical(snapshot["session"]["vertical"])
        if vertical.slug != "pet":
            abort(501)

        try:
            child_session_id, brief, names = refine_session(
                session_id,
                vertical,
                instruction=instruction,
            )
        except StorageError:
            abort(404)

        child_snapshot = get_session_snapshot(child_session_id)
        round_number = int(child_snapshot["session"]["round_number"])
        taste_profile = _taste_profile_from_snapshot(child_snapshot)
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
            reaction_counts=detail["reaction_counts"],
            taste_profile=detail["taste_profile"],
        )

    @app.get("/chosen/<chosen_id>")
    def chosen_name(chosen_id: str):
        snapshot = get_chosen_snapshot(chosen_id)
        if snapshot is None or snapshot["result"] is None:
            abort(404)

        result = to_plain_data(json_loads(snapshot["result"]["result_json"]))
        return render_template(
            "chosen.html",
            vertical=get_vertical(snapshot["chosen"]["vertical"]),
            chosen=snapshot["chosen"],
            result=result,
            session=snapshot["session"],
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


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
