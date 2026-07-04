"""Render ReportData to csv/xlsx/pdf bytes."""

from __future__ import annotations

import csv
import io

from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from .builders import ReportData


def render_csv(data: ReportData) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(data.columns)
    writer.writerows(data.rows)
    return buffer.getvalue().encode("utf-8-sig")  # BOM: Excel-friendly


def render_xlsx(data: ReportData) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = data.title[:31]  # Excel sheet name limit
    sheet.append(data.columns)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in data.rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def render_pdf(data: ReportData) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=data.title)
    styles = getSampleStyleSheet()
    table_rows = [data.columns] + [[str(cell) for cell in row] for row in data.rows]
    table = Table(table_rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
            ]
        )
    )
    document.build(
        [
            Paragraph(data.title, styles["Title"]),
            Spacer(1, 4 * mm),
            table,
        ]
    )
    return buffer.getvalue()


RENDERERS = {"csv": render_csv, "xlsx": render_xlsx, "pdf": render_pdf}
