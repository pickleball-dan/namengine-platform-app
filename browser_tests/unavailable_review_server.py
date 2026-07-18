"""Local-only recovery-state server used by the Baby browser audit."""

import sys
from pathlib import Path

from flask import Flask, render_template

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from namengine.verticals import get_vertical


app: Flask = create_app()


@app.get("/__review/baby-generation-unavailable")
def baby_generation_unavailable():
    return (
        render_template(
            "generation_unavailable.html",
            message="",
            vertical=get_vertical("baby"),
        ),
        503,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5006, debug=False, use_reloader=False)
