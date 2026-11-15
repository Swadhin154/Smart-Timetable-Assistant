import io
from datetime import date, datetime, time

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


def clean_value(value):
    """Format dates and times for readable reports."""

    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%d %B %Y, %I:%M %p")

    if isinstance(value, date):
        return value.strftime("%d %B %Y")

    if isinstance(value, time):
        return value.strftime("%I:%M %p")

    if isinstance(value, str):
        value = value.strip()

        for fmt in (
            "%H:%M:%S",
            "%H:%M",
            "%I:%M:%S %p",
            "%I:%M %p",
        ):
            try:
                return datetime.strptime(
                    value, fmt
                ).strftime("%I:%M %p")
            except ValueError:
                continue

    return str(value)


def prepare_records(records):
    """Prepare clean records with serial numbers for academic reports."""

    if not records:
        return []

    excluded_fields = {"id", "user_id", "created_at"}

    prepared_records = []

    for serial_no, record in enumerate(records, start=1):
        clean_record = {
            "Sl. No.": serial_no
        }

        for key, value in record.items():
            if key not in excluded_fields:
                clean_record[str(key)] = clean_value(value)

        prepared_records.append(clean_record)

    return prepared_records


def generate_academic_excel(data):
    """Generate a multi-sheet Excel academic report."""

    workbook = Workbook()
    workbook.remove(workbook.active)

    sections = [
        ("Timetable", "timetable"),
        ("Courses", "courses"),
        ("Exams", "exams"),
        ("Study Sessions", "study_sessions"),
        ("Assignment Deadlines", "deadlines"),
        ("Academic Events", "academic_events"),
    ]

    for sheet_name, data_key in sections:
        worksheet = workbook.create_sheet(sheet_name)
        records = prepare_records(data.get(data_key, []))

        if not records:
            worksheet.append(["No records available"])
            continue

        headers = list(records[0].keys())
        worksheet.append(headers)

        for record in records:
            worksheet.append([
                record.get(header, "")
                for header in headers
            ])

        for cell in worksheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="365F91",
            )
            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
            )

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for column_cells in worksheet.columns:
            column_letter = get_column_letter(
                column_cells[0].column
            )

            max_length = max(
                len(str(cell.value or ""))
                for cell in column_cells
            )

            worksheet.column_dimensions[column_letter].width = min(
                max(max_length + 3, 12),
                35,
            )

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return output.getvalue()


def generate_academic_pdf(data):
    """Generate a printable PDF academic report."""

    output = io.BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=19,
        spaceAfter=8,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=10,
        spaceAfter=6,
    )

    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["BodyText"],
        fontSize=7,
        leading=9,
    )

    story = [
        Paragraph("Smart Timetable Assistant", title_style),
        Paragraph(
            "Consolidated Academic Report",
            styles["Heading2"],
        ),
        Paragraph(
            f"Generated on: {date.today().strftime('%d %B %Y')}",
            styles["Normal"],
        ),
        Spacer(1, 12),
    ]

    sections = [
        ("Timetable", "timetable"),
        ("Courses", "courses"),
        ("Exams", "exams"),
        ("Study Sessions", "study_sessions"),
        ("Assignment Deadlines", "deadlines"),
        ("Personal Academic Events", "academic_events"),
    ]

    for index, (section_title, data_key) in enumerate(sections):
        records = prepare_records(data.get(data_key, []))

        story.append(
            Paragraph(section_title, heading_style)
        )

        if not records:
            story.append(
                Paragraph("No records available.", styles["Normal"])
            )
            story.append(Spacer(1, 8))
            continue

        headers = list(records[0].keys())

        table_data = [[
            Paragraph(str(header), cell_style)
            for header in headers
        ]]

        for record in records:
            table_data.append([
                Paragraph(
                    str(record.get(header, "")).replace(
                        "&", "&amp;"
                    ).replace("<", "&lt;").replace(">", "&gt;"),
                    cell_style,
                )
                for header in headers
            ])

        column_width = document.width / len(headers)

        table = Table(
            table_data,
            colWidths=[column_width] * len(headers),
            repeatRows=1,
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#365F91")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))

        story.append(table)
        story.append(Spacer(1, 12))

        if index < len(sections) - 1:
            story.append(PageBreak())

    document.build(story)

    output.seek(0)
    return output.getvalue()