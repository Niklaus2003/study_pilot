import io
import json
from datetime import datetime, date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# Premium Color Themes Palette Definition
PALETTES = {
    "Emerald Trust": {
        "primary": "#0f766e",      # Deep teal header
        "text_header": "#ffffff",
        "urgent": "#fee2e2",       # Soft rose (<= 7 days)
        "medium": "#fef08a",       # Soft yellow (<= 14 days)
        "normal": "#d1fae5",       # Soft emerald (<= 30 days)
        "relaxed": "#f8fafc",      # Very light blue-grey (> 30 days / None)
        "grid": "#cbd5e1",
        "primary_light": "#ccfbf1"
    },
    "Warm Amber": {
        "primary": "#b45309",      # Deep amber header
        "text_header": "#ffffff",
        "urgent": "#fee2e2",       # Soft rose (<= 7 days)
        "medium": "#ffedd5",       # Soft orange (<= 14 days)
        "normal": "#fef3c7",       # Soft amber (<= 30 days)
        "relaxed": "#f8fafc",      # Very light slate (> 30 days / None)
        "grid": "#cbd5e1",
        "primary_light": "#fef3c7"
    },
    "Cool Teal": {
        "primary": "#0369a1",      # Deep ocean blue header
        "text_header": "#ffffff",
        "urgent": "#fee2e2",       # Soft rose (<= 7 days)
        "medium": "#fef08a",       # Soft yellow (<= 14 days)
        "normal": "#e0f2fe",       # Soft sky-blue (<= 30 days)
        "relaxed": "#f8fafc",      # Very light grey (> 30 days / None)
        "grid": "#cbd5e1",
        "primary_light": "#e0f2fe"
    },
    "Classic Navy": {
        "primary": "#1e3a8a",      # Navy header
        "text_header": "#ffffff",
        "urgent": "#fee2e2",       # Soft rose (<= 7 days)
        "medium": "#fef08a",       # Soft yellow (<= 14 days)
        "normal": "#dbeafe",       # Soft blue (<= 30 days)
        "relaxed": "#f8fafc",      # Very light grey (> 30 days / None)
        "grid": "#cbd5e1",
        "primary_light": "#dbeafe"
    }
}

def subject_color_by_deadline(exam_date_str, palette, today=None):
    """
    Returns the reportlab color hex based on how close the exam date is.
    """
    if today is None:
        today = date.today()

    if not exam_date_str:
        return colors.HexColor(palette["relaxed"])

    try:
        exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    except Exception:
        return colors.HexColor(palette["relaxed"])

    days_remaining = (exam_date - today).days
    if days_remaining < 0:
        return colors.HexColor(palette["relaxed"]) # Exam passed or irrelevant
    if days_remaining <= 7:
        return colors.HexColor(palette["urgent"])
    if days_remaining <= 14:
        return colors.HexColor(palette["medium"])
    if days_remaining <= 30:
        return colors.HexColor(palette["normal"])
    return colors.HexColor(palette["relaxed"])

def _subject_meta_map(syllabus_data):
    """
    Creates a mapping of subject names to exam dates and weights.
    """
    meta = {}
    for item in syllabus_data:
        name = item.get("subject")
        if name and name not in meta:
            meta[name] = {
                "exam_date": item.get("exam_date", ""),
                "weightage": item.get("weightage", "")
            }
    return meta

def create_study_plan_pdf(timetable_data, syllabus_data, output_path="study_plan.pdf", output_stream=None, theme_name="Emerald Trust"):
    """
    Generates a beautifully colored study plan PDF with reportlab.
    """
    # Resolve color palette
    palette = PALETTES.get(theme_name, PALETTES["Emerald Trust"])
    
    subject_meta = _subject_meta_map(syllabus_data)
    
    if output_stream is not None:
        doc = SimpleDocTemplate(output_stream, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    else:
        doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        "PlanTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor(palette["primary"]),
        spaceAfter=12
    )
    
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4
    )
    
    header_style = ParagraphStyle(
        "Header",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor(palette["primary"]),
        spaceBefore=10,
        spaceAfter=6
    )
    
    legend_style = ParagraphStyle(
        "LegendText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569")
    )
    
    story = []

    # Title & Subtitle
    story.append(Paragraph("STUDY PILOT — ACADEMIC TIMETABLE", title_style))
    story.append(Paragraph(f"<b>Generated on:</b> {date.today().strftime('%B %d, %Y')} | <b>Theme:</b> {theme_name}", body_style))
    story.append(Spacer(1, 10))
    
    # Weekly Summary Section
    if timetable_data.get("weekly_summary"):
        summary_title_style = ParagraphStyle("SumTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor(palette["primary"]))
        story.append(Paragraph("Weekly Objective & Insights", summary_title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(timetable_data["weekly_summary"], body_style))
        story.append(Spacer(1, 12))

    # Priority Color Legend Table
    story.append(Paragraph("<b>Deadline Proximity Legend (Row Backgrounds):</b>", legend_style))
    legend_data = [
        [
            Paragraph("🚨 <b>Urgent</b> (<= 7 days)", legend_style),
            Paragraph("⚠️ <b>Medium</b> (<= 14 days)", legend_style),
            Paragraph("📅 <b>Normal</b> (<= 30 days)", legend_style),
            Paragraph("☕ <b>Relaxed</b> (> 30 days / No Exam)", legend_style)
        ]
    ]
    legend_table = Table(legend_data, colWidths=[135, 135, 135, 135])
    legend_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(palette["urgent"])),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(palette["medium"])),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor(palette["normal"])),
        ("BACKGROUND", (3, 0), (3, 0), colors.HexColor(palette["relaxed"])),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(legend_table)
    story.append(Spacer(1, 15))

    # Daily Schedule Table Rows
    for day in timetable_data.get("timetable", []):
        story.append(Paragraph(f"Day {day['day']} — {day['date']} ({day.get('total_study_minutes', 0)} mins total)", header_style))
        
        table_data = [[
            Paragraph("<b>Subject</b>", ParagraphStyle("H1", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor(palette["text_header"]))),
            Paragraph("<b>Duration</b>", ParagraphStyle("H2", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor(palette["text_header"]))),
            Paragraph("<b>Chapters to Cover</b>", ParagraphStyle("H3", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor(palette["text_header"]))),
            Paragraph("<b>Study Notes</b>", ParagraphStyle("H4", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor(palette["text_header"]))),
        ]]
        
        row_colors = []
        for slot in day.get("slots", []):
            subject = slot.get("subject", "Unknown")
            meta = subject_meta.get(subject, {})
            color = subject_color_by_deadline(meta.get("exam_date", ""), palette)
            row_colors.append(color)
            
            table_data.append([
                Paragraph(f"<b>{subject}</b>", body_style),
                Paragraph(f"{slot.get('duration_minutes', 0)} min", body_style),
                Paragraph(", ".join(slot.get("chapters_to_cover", [])) or "—", body_style),
                Paragraph(slot.get("notes", "—"), body_style),
            ])

        column_widths = [130, 60, 220, 130]
        table = Table(table_data, colWidths=column_widths, repeatRows=1)
        
        # Base table formatting
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(palette["primary"])),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor(palette["grid"])),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor(palette["primary"])),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])

        # Apply deadline-based colors to slots
        for row_idx, bg_color in enumerate(row_colors, start=1):
            style.add("BACKGROUND", (0, row_idx), (-1, row_idx), bg_color)

        table.setStyle(style)
        story.append(table)
        story.append(Spacer(1, 10))

    # Build PDF
    doc.build(story)
    
    if output_stream is not None:
        output_stream.seek(0)
        return output_stream
    return output_path

if __name__ == "__main__":
    # Test stub
    try:
        with open("timetable.json", "r") as f:
            timetable_data = json.load(f)
        with open("syllabus.json", "r") as f:
            syllabus_data = json.load(f)
        create_study_plan_pdf(timetable_data, syllabus_data, output_path="study_plan.pdf", theme_name="Emerald Trust")
        print("Test PDF successfully built in local directory.")
    except Exception as e:
        print(f"Error test building PDF: {e}")
