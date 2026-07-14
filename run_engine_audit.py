"""Run the NamEngine lane-discovery audit and write Google Sheets-ready files.

Usage:
    python run_engine_audit.py
    python run_engine_audit.py --fixture baby-classic-soft-familiar --rounds 4
    python run_engine_audit.py --use-ai

The CSV can be uploaded/imported directly into Google Sheets.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

try:
    import gspread
except ImportError:  # pragma: no cover - optional Google Sheets integration
    gspread = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is already in requirements
    load_dotenv = None

from namengine.core.engine_audit import (
    make_audit_run_id,
    run_engine_audit,
    summarize_engine_audit,
    write_engine_audit_csv,
    write_engine_audit_json,
)
from namengine.core.evals import load_taste_engine_fixtures


ACTIVE_AUDIT_VERTICALS = {"baby", "pet", "business"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NamEngine engine audit harness.")
    parser.add_argument("--fixture", action="append", default=[], help="Fixture id to include. Repeat for multiple.")
    parser.add_argument("--vertical", action="append", default=[], help="Vertical slug to include. Repeat for multiple.")
    parser.add_argument(
        "--include-under-development",
        action="store_true",
        help="Include all fixture verticals instead of defaulting to Baby, Pet, and Business.",
    )
    parser.add_argument("--rounds", type=int, default=4, help="Consecutive rounds to run per fixture.")
    parser.add_argument("--use-ai", action="store_true", help="Use live AI generation when configured.")
    parser.add_argument("--max-overlap", type=float, default=0.30, help="Max allowed overlap with previous round.")
    parser.add_argument("--min-signal-hits", type=int, default=2, help="Minimum expected-signals hits per round.")
    parser.add_argument("--out-dir", default="audit_outputs", help="Output directory.")
    parser.add_argument(
        "--append-to-sheets",
        action="store_true",
        help="Append audit rows to Google Sheets using service-account env vars.",
    )
    parser.add_argument(
        "--sheet-id",
        default="",
        help="Google Sheet id. Defaults to GOOGLE_ENGINE_AUDIT_SHEET_ID or GOOGLE_SMOKE_TEST_SHEET_ID.",
    )
    parser.add_argument(
        "--worksheet",
        default="",
        help="Worksheet name. Defaults to GOOGLE_ENGINE_AUDIT_WORKSHEET or Engine Audit.",
    )
    return parser.parse_args()


def append_rows_to_google_sheet(rows, *, sheet_id: str = "", worksheet_name: str = "") -> tuple[bool, str]:
    """Append audit rows to an existing Google Sheet, creating the worksheet if needed."""
    if gspread is None:
        return False, "gspread is not installed"

    import os

    resolved_sheet_id = (
        sheet_id.strip()
        or os.getenv("GOOGLE_ENGINE_AUDIT_SHEET_ID", "").strip()
        or os.getenv("GOOGLE_SMOKE_TEST_SHEET_ID", "").strip()
    )
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    credentials_json_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    resolved_worksheet = (
        worksheet_name.strip()
        or os.getenv("GOOGLE_ENGINE_AUDIT_WORKSHEET", "").strip()
        or "Engine Audit"
    )
    if not resolved_sheet_id:
        return False, "missing GOOGLE_ENGINE_AUDIT_SHEET_ID or GOOGLE_SMOKE_TEST_SHEET_ID"
    if not credentials_json and not credentials_json_path:
        return False, "missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_JSON_PATH"

    if credentials_json_path:
        credentials = json.loads(Path(credentials_json_path).read_text(encoding="utf-8"))
    else:
        credentials = json.loads(credentials_json)
    client = gspread.service_account_from_dict(credentials)
    spreadsheet = client.open_by_key(resolved_sheet_id)
    try:
        worksheet = spreadsheet.worksheet(resolved_worksheet)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=resolved_worksheet, rows=1000, cols=len(rows[0].to_sheet_row()) if rows else 26)
        worksheet.append_row(list(rows[0].to_sheet_row().keys()), value_input_option="USER_ENTERED")

    if rows and not worksheet.row_values(1):
        worksheet.append_row(list(rows[0].to_sheet_row().keys()), value_input_option="USER_ENTERED")
    values = [list(row.to_sheet_row().values()) for row in rows]
    if values:
        worksheet.append_rows(values, value_input_option="USER_ENTERED")
    return True, f"appended {len(values)} rows to worksheet '{resolved_worksheet}'"


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()
    args = parse_args()
    if args.rounds < 1:
        raise SystemExit("--rounds must be at least 1")

    fixtures = load_taste_engine_fixtures()
    if not args.fixture and not args.vertical and not args.include_under_development:
        fixtures = [fixture for fixture in fixtures if fixture.vertical in ACTIVE_AUDIT_VERTICALS]
    if args.fixture:
        wanted = set(args.fixture)
        fixtures = [fixture for fixture in fixtures if fixture.id in wanted]
        missing = sorted(wanted - {fixture.id for fixture in fixtures})
        if missing:
            raise SystemExit(f"Unknown fixture id(s): {', '.join(missing)}")
    if args.vertical:
        wanted_verticals = set(args.vertical)
        fixtures = [fixture for fixture in fixtures if fixture.vertical in wanted_verticals]
    if not fixtures:
        raise SystemExit("No fixtures selected.")

    run_id = make_audit_run_id()
    rows = run_engine_audit(
        fixtures,
        rounds=args.rounds,
        use_ai=args.use_ai,
        max_previous_overlap_pct=args.max_overlap,
        min_signal_hits=args.min_signal_hits,
        run_id=run_id,
    )
    out_dir = Path(args.out_dir)
    csv_path = write_engine_audit_csv(rows, out_dir / f"{run_id}.csv")
    json_path = write_engine_audit_json(rows, out_dir / f"{run_id}.json")
    summary = summarize_engine_audit(rows)
    summary_path = out_dir / f"{run_id}-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    sheets_result = {"attempted": False, "uploaded": False, "message": "not requested"}
    if args.append_to_sheets:
        uploaded, message = append_rows_to_google_sheet(rows, sheet_id=args.sheet_id, worksheet_name=args.worksheet)
        sheets_result = {"attempted": True, "uploaded": uploaded, "message": message}

    print(json.dumps({
        "run_id": run_id,
        "created_at_local_hint": datetime.now().isoformat(timespec="seconds"),
        "csv": str(csv_path),
        "json": str(json_path),
        "summary": str(summary_path),
        "google_sheets": sheets_result,
        "google_sheets_note": "CSV remains available as a backup; judge_score and judge_notes are blank review columns.",
        **summary,
    }, ensure_ascii=False, indent=2))
    return 0 if not sheets_result["attempted"] or sheets_result["uploaded"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
