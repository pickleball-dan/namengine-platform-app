"""
Generate USPTO Provisional Patent Application Cover Sheet (based on SB/16).
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

OUT_FILE = os.path.join(os.path.dirname(__file__), "namengine-provisional-cover-sheet.pdf")

W, H = letter
INK   = colors.HexColor("#18212f")
MUTED = colors.HexColor("#607086")
LIGHT = colors.HexColor("#dde3ec")
BOX   = colors.HexColor("#f5f7fa")

def rule(c, y, x1=0.75*inch, x2=7.75*inch, thickness=0.5, color=None):
    c.setStrokeColor(color or LIGHT)
    c.setLineWidth(thickness)
    c.line(x1, y, x2, y)

def label(c, text, x, y, size=8, bold=False, color=None):
    c.setFillColor(color or MUTED)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x, y, text)

def value(c, text, x, y, size=10):
    c.setFillColor(INK)
    c.setFont("Helvetica", size)
    c.drawString(x, y, text)

def field_box(c, x, y, w, h):
    c.setFillColor(BOX)
    c.setStrokeColor(LIGHT)
    c.setLineWidth(0.75)
    c.rect(x, y, w, h, fill=1, stroke=1)

c = canvas.Canvas(OUT_FILE, pagesize=letter)

# ── Header ──────────────────────────────────────────────────────────────────
c.setFillColor(INK)
c.setFont("Helvetica-Bold", 13)
c.drawCentredString(W/2, H - 0.65*inch, "PROVISIONAL PATENT APPLICATION COVER SHEET")
c.setFont("Helvetica", 9)
c.setFillColor(MUTED)
c.drawCentredString(W/2, H - 0.88*inch, "Based on USPTO Form SB/16 · 35 U.S.C. § 111(b) · 37 C.F.R. § 1.51(c)")
rule(c, H - 0.98*inch, thickness=1, color=INK)

# ── Section 1: Application Type ─────────────────────────────────────────────
y = H - 1.25*inch
label(c, "APPLICATION TYPE", 0.75*inch, y, size=8, bold=True, color=INK)
y -= 0.18*inch
field_box(c, 0.75*inch, y - 0.05*inch, 6.5*inch, 0.35*inch)
value(c, "☑  Provisional Patent Application  (35 U.S.C. § 111(b))", 0.85*inch, y + 0.06*inch, size=10)
rule(c, y - 0.12*inch)

# ── Section 2: Title ─────────────────────────────────────────────────────────
y -= 0.45*inch
label(c, "TITLE OF INVENTION", 0.75*inch, y, size=8, bold=True, color=INK)
y -= 0.18*inch
field_box(c, 0.75*inch, y - 0.32*inch, 6.5*inch, 0.68*inch)
c.setFillColor(INK)
c.setFont("Helvetica", 9)
title_lines = [
    "System and Method for Personalized Name Generation Using Structured Preference",
    "Elicitation, Canonical Intent Mapping, Reaction-Driven Refinement, Multi-Provider",
    "Quality Routing, Taste State Maintenance, and Exploration-Driven Refinement",
]
ty = y + 0.26*inch
for line in title_lines:
    c.drawString(0.85*inch, ty, line)
    ty -= 0.16*inch
rule(c, y - 0.45*inch)

# ── Section 3: Inventor ──────────────────────────────────────────────────────
y -= 0.75*inch
label(c, "INVENTOR(S)", 0.75*inch, y, size=8, bold=True, color=INK)
y -= 0.18*inch

# Sub-labels
label(c, "LAST NAME", 0.75*inch, y, size=7)
label(c, "FIRST NAME", 3.0*inch, y, size=7)
label(c, "MIDDLE NAME / INITIAL", 5.25*inch, y, size=7)
y -= 0.16*inch

field_box(c, 0.75*inch, y - 0.05*inch, 2.1*inch, 0.32*inch)
field_box(c, 3.0*inch,  y - 0.05*inch, 2.1*inch, 0.32*inch)
field_box(c, 5.25*inch, y - 0.05*inch, 2.0*inch, 0.32*inch)
value(c, "Normand", 0.85*inch, y + 0.06*inch)
value(c, "Daniel", 3.1*inch,  y + 0.06*inch)
value(c, "A.", 5.35*inch, y + 0.06*inch)
rule(c, y - 0.18*inch)

# ── Section 4: Residence ─────────────────────────────────────────────────────
y -= 0.48*inch
label(c, "INVENTOR RESIDENCE", 0.75*inch, y, size=8, bold=True, color=INK)
y -= 0.18*inch
label(c, "CITY", 0.75*inch, y, size=7)
label(c, "STATE", 3.0*inch, y, size=7)
label(c, "COUNTRY", 5.25*inch, y, size=7)
y -= 0.16*inch
field_box(c, 0.75*inch, y - 0.05*inch, 2.1*inch, 0.32*inch)
field_box(c, 3.0*inch,  y - 0.05*inch, 2.1*inch, 0.32*inch)
field_box(c, 5.25*inch, y - 0.05*inch, 2.0*inch, 0.32*inch)
value(c, "Temecula", 0.85*inch, y + 0.06*inch)
value(c, "CA", 3.1*inch, y + 0.06*inch)
value(c, "US", 5.35*inch, y + 0.06*inch)
rule(c, y - 0.18*inch)

# ── Section 5: Correspondence Address ───────────────────────────────────────
y -= 0.48*inch
label(c, "CORRESPONDENCE ADDRESS", 0.75*inch, y, size=8, bold=True, color=INK)
y -= 0.18*inch
field_box(c, 0.75*inch, y - 0.62*inch, 6.5*inch, 0.92*inch)
addr_lines = [
    "Daniel A. Normand",
    "43997 Eaglebluff Court",
    "Temecula, CA 92592",
    "United States",
]
ay = y + 0.18*inch
for line in addr_lines:
    value(c, line, 0.85*inch, ay)
    ay -= 0.18*inch
rule(c, y - 0.78*inch)

# ── Section 6: Entity Status ─────────────────────────────────────────────────
y -= 1.08*inch
label(c, "ENTITY STATUS", 0.75*inch, y, size=8, bold=True, color=INK)
y -= 0.18*inch
field_box(c, 0.75*inch, y - 0.05*inch, 6.5*inch, 0.32*inch)
value(c, "☑  Micro Entity  (37 C.F.R. § 1.29)    ☐  Small Entity    ☐  Large Entity",
      0.85*inch, y + 0.06*inch)
rule(c, y - 0.18*inch)

# ── Section 7: Filing Date / Priority ───────────────────────────────────────
y -= 0.48*inch
label(c, "FILING DATE (for office use)", 0.75*inch, y, size=8, bold=True, color=INK)
label(c, "ATTORNEY DOCKET NO.", 4.0*inch, y, size=8, bold=True, color=INK)
y -= 0.18*inch
field_box(c, 0.75*inch, y - 0.05*inch, 2.9*inch, 0.32*inch)
field_box(c, 4.0*inch,  y - 0.05*inch, 3.25*inch, 0.32*inch)
value(c, "September 15, 2026", 0.85*inch, y + 0.06*inch)
value(c, "DAN-NE-001-PROV", 4.1*inch, y + 0.06*inch)
rule(c, y - 0.18*inch)

# ── Section 8: Declaration ───────────────────────────────────────────────────
y -= 0.55*inch
label(c, "DECLARATION / STATEMENT", 0.75*inch, y, size=8, bold=True, color=INK)
y -= 0.16*inch
c.setFont("Helvetica", 8.5)
c.setFillColor(colors.HexColor("#2a3040"))
decl_lines = [
    "The undersigned inventor(s) hereby declare that the attached specification discloses the invention",
    "described herein and that this application is being filed pursuant to 35 U.S.C. § 111(b) as a",
    "Provisional Patent Application. The inventor(s) acknowledge that a non-provisional application",
    "claiming the benefit of this provisional must be filed within twelve (12) months of this filing date.",
]
for line in decl_lines:
    c.drawString(0.75*inch, y, line)
    y -= 0.16*inch

# ── Section 9: Signature ─────────────────────────────────────────────────────
y -= 0.3*inch
rule(c, y, thickness=0.5)
y -= 0.35*inch
label(c, "SIGNATURE OF INVENTOR", 0.75*inch, y, size=8, bold=True, color=INK)
label(c, "DATE", 5.0*inch, y, size=8, bold=True, color=INK)
y -= 0.16*inch
# Signature line
c.setStrokeColor(INK)
c.setLineWidth(0.75)
c.line(0.75*inch, y, 4.5*inch, y)
c.line(5.0*inch, y, 7.25*inch, y)
y -= 0.16*inch
value(c, "Daniel A. Normand", 0.75*inch, y, size=9)
value(c, "September 15, 2026", 5.0*inch, y, size=9)

# ── Section 10: Enclosures ───────────────────────────────────────────────────
y -= 0.5*inch
rule(c, y, thickness=0.5)
y -= 0.22*inch
label(c, "ENCLOSURES", 0.75*inch, y, size=8, bold=True, color=INK)
y -= 0.18*inch
enclosures = [
    "☑  Specification (including claims, abstract, and drawings)",
    "☑  Figures: 9 formal drawings (FIG. 1 – FIG. 9)",
    "☑  Filing fee (Micro Entity rate — to be submitted via USPTO Patent Center)",
]
for enc in enclosures:
    value(c, enc, 0.85*inch, y, size=9)
    y -= 0.18*inch

# ── Footer ───────────────────────────────────────────────────────────────────
rule(c, 0.65*inch, thickness=1, color=INK)
c.setFont("Helvetica", 7.5)
c.setFillColor(MUTED)
c.drawCentredString(W/2, 0.45*inch,
    "USPTO Provisional Patent Application · 35 U.S.C. § 111(b) · Daniel A. Normand · September 15, 2026")

c.save()
size = os.path.getsize(OUT_FILE)
print(f"Cover sheet written: {OUT_FILE}")
print(f"Size: {size:,} bytes")
