"""Gunicorn runtime configuration for Render.

Render may run a dashboard-level Start Command like:
    gunicorn app:app --bind 0.0.0.0:$PORT

Gunicorn automatically loads this file from the working directory, so these
settings still apply even when Procfile/render.yaml are bypassed.
"""

# The three-pass LLM engine intentionally preserves quality over speed while
# OpenAI completes taste interpretation, candidate generation, and final ranking.
# Keep enough request headroom for all three provider calls plus app overhead so
# slow high-quality generations fail gracefully instead of being cut off by
# Gunicorn near the end of the pipeline.
timeout = 420
