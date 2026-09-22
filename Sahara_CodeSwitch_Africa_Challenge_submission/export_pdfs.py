"""Export every Markdown submission document to a review-friendly PDF.

Run from the repository root:
  python Sahara_CodeSwitch_Africa_Challenge_submission/export_pdfs.py
"""
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pdf"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s: str) -> str:
    s = esc(s.strip())
    s = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[([^]]+)\]\([^)]*\)", r"<u>\1</u>", s)
    return s


def make_pdf(md: Path) -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=13, spaceAfter=6)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=HexColor("#17293A"), spaceAfter=12)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=HexColor("#17293A"), spaceBefore=10, spaceAfter=7)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=HexColor("#17293A"), spaceBefore=8, spaceAfter=5)
    code = ParagraphStyle("Code", parent=body, fontName="Courier", fontSize=7.5, leading=10, backColor=HexColor("#F3F5F7"), leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=6)
    story = []
    lines = md.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            i += 1; block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(esc(lines[i])); i += 1
            story.append(Paragraph("<br/>".join(block) or " ", code)); i += 1; continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), h1))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), h2))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), h3))
        elif line.startswith("|") and "|" in line[1:]:
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells): rows.append([Paragraph(inline(c), body) for c in cells])
                i += 1
            if rows:
                widths = [16.5 * cm / len(rows[0])] * len(rows[0])
                table = Table(rows, colWidths=widths, repeatRows=1)
                table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), HexColor("#17293A")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .25, HexColor("#C9D2DA")), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4), ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
                story.extend([table, Spacer(1, 8)])
            continue
        elif line.startswith(("- ", "* ")):
            story.append(Paragraph("• " + inline(line[2:]), body))
        elif re.match(r"\d+\. ", line):
            story.append(Paragraph(inline(line), body))
        elif line.strip() and not re.fullmatch(r"[-*_]{3,}", line.strip()):
            story.append(Paragraph(inline(line), body))
        i += 1
    doc = SimpleDocTemplate(str(OUT / f"{md.stem}.pdf"), pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=1.7*cm, bottomMargin=1.7*cm, title=md.stem)
    doc.build(story)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for source in sorted(ROOT.glob("*.md")):
        make_pdf(source)
        print(OUT / f"{source.stem}.pdf")
