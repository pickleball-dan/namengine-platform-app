"""Gunicorn runtime configuration for Render.

Render may run a dashboard-level Start Command like:
    gunicorn app:app --bind 0.0.0.0:$PORT

Gunicorn automatically loads this file from the working directory, so these
settings still apply even when Procfile/render.yaml are bypassed.
"""

# The Baby three-pass LLM engine can legitimately take longer than Gunicorn's
# 30-second default while OpenAI completes taste interpretation, candidate
# generation, and final ranking. Keep this above the OpenAI client timeout.
timeout = 240
