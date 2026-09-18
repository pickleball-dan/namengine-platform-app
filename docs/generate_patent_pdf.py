"""Generate a clean PDF from the NamEngine provisional patent markdown.
Embeds real SVG figures at [Figure X] placeholder lines.
"""
import re
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

IN_FILE  = os.path.join(os.path.dirname(__file__), "namengine-provisional-patent.md")
OUT_FILE = os.path.join(os.path.dirname(__file__), "namengine-provisional-patent.pdf")
FIG_DIR  = os.path.join(os.path.dirname(__file__), "figures")

# Map figure numbers to SVG files
FIGURE_MAP = {
    "1": "figure-01-system-architecture.svg",
    "2": "figure-02-intake-flow.svg",
    "3": "figure-03-cni-data-structure.svg",
    "4": "figure-04-multi-provider-routing.svg",
    "5": "figure-05-quality-adapter.svg",
    "6": "figure-06-taste-profile-construction.svg",
    "7": "figure-07-multi-round-refinement.svg",
    "8": "figure-08-multi-vertical-config.svg",
    "9": "figure-09-taste-engine-feedback-loop.svg",
}

doc = SimpleDocTemplate(
    OUT_FILE,
    pagesize=letter,
    rightMargin=1*inch, leftMargin=1*inch,
    topMargin=1*inch, bottomMargin=1*inch,
    title="NamEngine Provisional Patent Application",
    author="Dan Normand",
)

INK     = colors.HexColor("#18212f")
MUTED   = colors.HexColor("#607086")
BODY_FG = colors.HexColor("#2a3040")
WARN_BG = colors.HexColor("#fffbe6")
WARN_FG = colors.HexColor("#7a5500")
RULE    = colors.HexColor("#dde3ec")

S = {
    "title":     ParagraphStyle("PTitle", fontSize=17, leading=22, spaceAfter=4,
                     textColor=INK, alignment=TA_CENTER, fontName="Helvetica-Bold"),
    "meta":      ParagraphStyle("PMeta",  fontSize=9,  leading=13, spaceAfter=2,
                     textColor=MUTED, alignment=TA_CENTER, fontName="Helvetica"),
    "warn":      ParagraphStyle("PWarn",  fontSize=8.5, leading=13, spaceAfter=8, spaceBefore=4,
                     textColor=WARN_FG, backColor=WARN_BG,
                     leftIndent=10, rightIndent=10, fontName="Helvetica"),
    "h1":        ParagraphStyle("PH1",    fontSize=12, leading=16, spaceAfter=4, spaceBefore=14,
                     textColor=INK, fontName="Helvetica-Bold"),
    "h2":        ParagraphStyle("PH2",    fontSize=10.5, leading=14, spaceAfter=3, spaceBefore=10,
                     textColor=INK, fontName="Helvetica-Bold"),
    "h3":        ParagraphStyle("PH3",    fontSize=10, leading=13, spaceAfter=2, spaceBefore=7,
                     textColor=INK, fontName="Helvetica-BoldOblique"),
    "body":      ParagraphStyle("PBody",  fontSize=9.5, leading=14.5, spaceAfter=5,
                     textColor=BODY_FG, alignment=TA_JUSTIFY, fontName="Helvetica"),
    "bullet":    ParagraphStyle("PBullet", fontSize=9.5, leading=13.5, spaceAfter=3,
                     textColor=BODY_FG, leftIndent=18, fontName="Helvetica"),
    "subbullet": ParagraphStyle("PSubBullet", fontSize=9, leading=13, spaceAfter=2,
                     textColor=BODY_FG, leftIndent=34, fontName="Helvetica"),
    "figcap":    ParagraphStyle("PFigCap", fontSize=9, leading=12, spaceAfter=8, spaceBefore=4,
                     textColor=MUTED, alignment=TA_CENTER, fontName="Helvetica"),
}


def safe_text(text):
    parts = re.split(r'(`[^`]+`)', text)
    out = []
    for part in parts:
        if part.startswith('`') and part.endswith('`') and len(part) > 1:
            code = part[1:-1]
            code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            out.append('<font name="Courier" size="8.5">' + code + '</font>')
        else:
            p = part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            p = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', p)
            p = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', p)
            p = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', p)
            p = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<i>\1</i>', p)
            out.append(p)
    return ''.join(out)


def make_svg_flowable(fig_num, avail_w=6.5*inch, avail_h=7.5*inch):
    """Load SVG and return a scaled drawing that fits the available space."""
    svg_file = FIGURE_MAP.get(str(fig_num))
    if not svg_file:
        return None
    svg_path = os.path.join(FIG_DIR, svg_file)
    if not os.path.exists(svg_path):
        return None
    drawing = svg2rlg(svg_path)
    if drawing is None:
        return None
    scale = min(avail_w / drawing.width, avail_h / drawing.height)
    drawing.width  *= scale
    drawing.height *= scale
    drawing.transform = (scale, 0, 0, scale, 0, 0)
    return drawing


def build_story(lines):
    story = []
    for raw in lines:
        raw = raw.rstrip('\n')
        stripped = raw.strip()

        # Detect [Figure X — ...] placeholder lines
        fig_match = re.match(r'^>\s*\*\*\[Figure\s+(\d+)\s*[—\-]', stripped)
        if fig_match:
            fig_num = fig_match.group(1)
            drawing = make_svg_flowable(fig_num)
            if drawing:
                story.append(Spacer(1, 8))
                story.append(drawing)
                story.append(Paragraph(f"FIG. {fig_num}", S["figcap"]))
                story.append(Spacer(1, 8))
            else:
                # Fallback: render as blockquote text
                story.append(Paragraph(safe_text(stripped.lstrip('> ')), S["warn"]))
            continue

        if not stripped:
            story.append(Spacer(1, 4))
            continue

        if stripped in ('---', '***', '___'):
            story.append(HRFlowable(width='100%', thickness=0.5,
                                    color=RULE, spaceAfter=6, spaceBefore=4))
            continue

        if raw.startswith('# '):
            story.append(Paragraph(safe_text(raw[2:].strip()), S['title']))
            continue

        if raw.startswith('## '):
            story.append(HRFlowable(width='100%', thickness=0.5,
                                    color=RULE, spaceAfter=3, spaceBefore=8))
            story.append(Paragraph(safe_text(raw[3:].strip()), S['h1']))
            continue

        if raw.startswith('### '):
            story.append(Paragraph(safe_text(raw[4:].strip()), S['h2']))
            continue

        if raw.startswith('#### '):
            story.append(Paragraph(safe_text(raw[5:].strip()), S['h3']))
            continue

        if raw.startswith('> '):
            story.append(Paragraph(safe_text(raw[2:].strip()), S['warn']))
            continue

        if re.match(r'^(    |\t)[*\-] ', raw):
            content = re.sub(r'^(    |\t)[*\-] ', '', raw)
            story.append(Paragraph('\u2013\u00a0' + safe_text(content.strip()), S['subbullet']))
            continue

        if re.match(r'^[*\-] ', raw):
            story.append(Paragraph('\u2022\u00a0' + safe_text(raw[2:].strip()), S['bullet']))
            continue

        if re.match(r'^\d+\. ', raw):
            content = re.sub(r'^\d+\.\s+', '', raw)
            story.append(Paragraph(safe_text(content.strip()), S['bullet']))
            continue

        if re.match(r'^\*\*(Prepared|Revised|Inventor|Status):', raw):
            story.append(Paragraph(safe_text(stripped), S['meta']))
            continue

        story.append(Paragraph(safe_text(stripped), S['body']))

    return story


with open(IN_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

story = build_story(lines)
doc.build(story)

size = os.path.getsize(OUT_FILE)
print(f'PDF written: {OUT_FILE}')
print(f'Size: {size:,} bytes ({size // 1024} KB)')
