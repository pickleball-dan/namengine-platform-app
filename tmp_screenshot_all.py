"""Create a mock business session and screenshot all fixed pages."""
import sys, json, datetime
sys.path.insert(0, ".")

from namengine.core.storage import get_database_path, initialize_database
from sqlite3 import connect
import contextlib

DB = get_database_path()
initialize_database(DB)

SESSION_ID = "business-screenshot-test-001"
NOW = datetime.datetime.utcnow().isoformat()

BRIEF = json.dumps({
    "vertical": "business",
    "company_type": "Equipment",
    "product_focus": "Pickleball paddles",
    "target_audience": "Competitive players",
    "tone": "Technical and premium",
    "avoid": "Generic sports names"
})

NAMES = [
    {"name": "CorePick Technologies", "tagline": "The Heart of Innovative Pickleball Equipment",
     "pronunciation": "Core-PICK tech-NAL-oh-jeez", "meaning": "A name that conveys essential precision.",
     "tags": ["clear", "descriptive", "tech-forward"]},
    {"name": "PaddlePrime Gear", "tagline": "Prime Performance for Serious Players",
     "pronunciation": "PAD-ul-prime gear", "meaning": "A clear, descriptive name signifying top-tier.",
     "tags": ["premium", "clear", "sporty"]},
    {"name": "Arcline Sports", "tagline": "Engineered for the Arc of Victory",
     "pronunciation": "ARK-line sports", "meaning": "Suggests trajectory, precision, and mastery.",
     "tags": ["evocative", "premium", "athletic"]},
]

with contextlib.closing(connect(DB)) as db:
    db.execute("DELETE FROM sessions WHERE id = ?", (SESSION_ID,))
    db.execute("DELETE FROM name_results WHERE session_id = ?", (SESSION_ID,))
    db.execute("""
        INSERT OR REPLACE INTO sessions (id, vertical, brief_json, created_at, updated_at)
        VALUES (?, 'business', ?, ?, ?)
    """, (SESSION_ID, BRIEF, NOW, NOW))
    for i, n in enumerate(NAMES, 1):
        db.execute("""
            INSERT INTO name_results (session_id, position, name, tagline, pronunciation, meaning, tags_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (SESSION_ID, i, n["name"], n["tagline"], n["pronunciation"], n["meaning"], json.dumps(n["tags"]), NOW))
    db.commit()

print(f"Session created: {SESSION_ID}")
