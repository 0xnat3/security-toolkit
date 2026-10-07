"""Turn report rows into CSV or PDF bytes.

Row values come from user input and from scanned systems (banners, folder names), so they are untrusted.
"""
import csv
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .definitions import Column, Report

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Stop spreadsheets from running a text cell as a formula (CSV injection)."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _cell(column: Column, row: dict):
    value = row.get(column.key)
    if value is None:
        return ""
    return column.fmt(value) if column.fmt else value


def to_csv(report: Report, rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([c.header for c in report.columns])
    for row in rows:
        writer.writerow([csv_safe(_cell(c, row)) for c in report.columns])
    return buffer.getvalue().encode("utf-8-sig")  # BOM so Excel detects UTF-8


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#718096"))
    canvas.drawString(doc.leftMargin, 9 * mm, "Security Toolkit")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def to_pdf(report: Report, rows: list[dict], *, username: str, generated_at: datetime, note: str | None = None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=f"{report.title} report",
        author="Security Toolkit",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8, leading=10)
    head = ParagraphStyle("head", parent=body, fontName="Helvetica-Bold", textColor=colors.white)
    muted = ParagraphStyle("muted", parent=styles["BodyText"], fontSize=9, textColor=colors.HexColor("#4a5568"))

    def para(text, style):
        return Paragraph(escape(str(text)), style)  # escape: ReportLab parses <b>, <font>, &entities; in text

    story = [
        para(f"{report.title} report", styles["Heading1"]),
        para(f"Generated {generated_at:%Y-%m-%d %H:%M:%S} UTC for {username} | {len(rows)} entries", muted),
        Spacer(1, 6 * mm),
    ]

    if rows:
        total = sum(c.weight for c in report.columns)
        widths = [doc.width * c.weight / total for c in report.columns]
        data = [[para(c.header, head) for c in report.columns]]
        data += [[para(_cell(c, row), body) for c in report.columns] for row in rows]
        table = Table(data, colWidths=widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6cb0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
    else:
        story.append(para("No entries yet.", body))

    if note:
        story += [Spacer(1, 4 * mm), para(note, muted)]

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()