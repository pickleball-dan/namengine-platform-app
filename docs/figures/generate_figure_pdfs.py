"""
Generate individual PDFs for each of the 9 patent figure SVG files.
Uses canvas.drawDrawing() so tall figures never overflow — each fits one page.
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

FIGURES_DIR = os.path.dirname(os.path.abspath(__file__))

FIGURES = [
    "figure-01-system-architecture.svg",
    "figure-02-intake-flow.svg",
    "figure-03-cni-data-structure.svg",
    "figure-04-multi-provider-routing.svg",
    "figure-05-quality-adapter.svg",
    "figure-06-taste-profile-construction.svg",
    "figure-07-multi-round-refinement.svg",
    "figure-08-multi-vertical-config.svg",
    "figure-09-taste-engine-feedback-loop.svg",
]

MARGIN = 36  # 0.5 inch

for svg_name in FIGURES:
    svg_path = os.path.join(FIGURES_DIR, svg_name)
    pdf_path = os.path.join(FIGURES_DIR, svg_name.replace(".svg", ".pdf"))

    if not os.path.exists(svg_path):
        print(f"  MISSING: {svg_name}")
        continue

    try:
        drawing = svg2rlg(svg_path)
        if drawing is None:
            print(f"  FAILED (None): {svg_name}")
            continue

        svg_w = drawing.width
        svg_h = drawing.height

        # Scale to fit within letter page margins
        page_w, page_h = letter
        avail_w = page_w - 2 * MARGIN
        avail_h = page_h - 2 * MARGIN

        scale = min(avail_w / svg_w, avail_h / svg_h)
        scaled_w = svg_w * scale
        scaled_h = svg_h * scale

        # Center on page
        x = MARGIN + (avail_w - scaled_w) / 2
        y = MARGIN + (avail_h - scaled_h) / 2

        c = canvas.Canvas(pdf_path, pagesize=(page_w, page_h))
        c.translate(x, y)
        c.scale(scale, scale)
        renderPDF.draw(drawing, c, 0, 0)
        c.save()

        size = os.path.getsize(pdf_path)
        print(f"  OK  {svg_name.replace('.svg', '.pdf')}: {size:,} bytes")

    except Exception as e:
        print(f"  ERROR {svg_name}: {e}")

print("Done.")
