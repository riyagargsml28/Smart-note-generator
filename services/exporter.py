"""
Notes Exporter Service.
Exports structured lecture notes to:
1. Markdown (.md)
2. Plain Text (.txt)
3. Formatted PDF (.pdf) using ReportLab with clean academic styling.
"""

import io
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page numbers and running footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))  # Slate-500

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Smart Notes Generator — Lecture Study Guide")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer
        footer_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(8.5 * inch - 54, 36, footer_text)
        self.drawString(54, 36, "Generated with Smart Notes AI — For Academic Study Use")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * inch - 54, 48)

        self.restoreState()


class NotesExporter:
    """Exports structured notes to Markdown, TXT, and PDF."""

    @classmethod
    def to_markdown(cls, notes: Dict[str, Any], subject: str = "General") -> str:
        """Converts notes dict into formatted Markdown."""
        lines = []
        title = notes.get("title", "Lecture Notes")
        lines.append(f"# {title}\n")
        lines.append(f"**Subject:** {subject}\n")

        # Overview
        overview = notes.get("overview", "")
        if overview:
            lines.append("## Overview\n")
            lines.append(f"{overview}\n")

        # Sections
        sections = notes.get("sections", [])
        if sections:
            lines.append("## Lecture Content & Key Concepts\n")
            for idx, sec in enumerate(sections, 1):
                heading = sec.get("heading", f"Section {idx}")
                lines.append(f"### {idx}. {heading}\n")

                # Key Points
                key_points = sec.get("key_points", [])
                if key_points:
                    lines.append("**Key Points:**")
                    for kp in key_points:
                        lines.append(f"- {kp}")
                    lines.append("")

                # Definitions
                definitions = sec.get("definitions", [])
                if definitions:
                    lines.append("**Key Definitions:**")
                    for d in definitions:
                        term = d.get("term", "")
                        meaning = d.get("meaning", "")
                        lines.append(f"- **{term}:** {meaning}")
                    lines.append("")

                # Examples
                examples = sec.get("examples", [])
                if examples:
                    lines.append("**Examples & Explanations:**")
                    for ex in examples:
                        lines.append(f"- {ex}")
                    lines.append("")

        # Formulas
        formulas = notes.get("formulas", [])
        if formulas:
            lines.append("## Important Formulas & Mathematical Models\n")
            for f in formulas:
                if isinstance(f, dict):
                    name = f.get("name", "Formula")
                    form = f.get("formula", "")
                    exp = f.get("explanation", "")
                    lines.append(f"- **{name}:** `{form}`  \n  *{exp}*")
                else:
                    lines.append(f"- `{f}`")
            lines.append("")

        # Glossary
        glossary = notes.get("glossary", [])
        if glossary:
            lines.append("## Glossary of Terms\n")
            lines.append("| Term | Definition |")
            lines.append("| :--- | :--- |")
            for g in glossary:
                if isinstance(g, dict):
                    t = g.get("term", "")
                    m = g.get("meaning", g.get("definition", ""))
                    lines.append(f"| **{t}** | {m} |")
                else:
                    lines.append(f"| Term | {g} |")
            lines.append("")

        # Summary
        summary = notes.get("summary", "")
        if summary:
            lines.append("## Summary & Conclusion\n")
            lines.append(f"{summary}\n")

        # Revision Questions
        rev_q = notes.get("revision_questions", [])
        if rev_q:
            lines.append("## Revision Questions & Answers\n")
            for i, q in enumerate(rev_q, 1):
                ques = q.get("question", "")
                ans = q.get("answer", "")
                lines.append(f"**Q{i}: {ques}**\n")
                lines.append(f"> **Answer:** {ans}\n")

        # MCQs
        mcqs = notes.get("mcqs", [])
        if mcqs:
            lines.append("## Multiple-Choice Questions (MCQs)\n")
            for i, mcq in enumerate(mcqs, 1):
                ques = mcq.get("question", "")
                opts = mcq.get("options", [])
                ans = mcq.get("correct_answer", "")
                exp = mcq.get("explanation", "")
                lines.append(f"**{i}. {ques}**")
                for opt in opts:
                    lines.append(f"- {opt}")
                lines.append(f"\n*Correct Answer:* **{ans}**")
                if exp:
                    lines.append(f"*Explanation:* {exp}\n")
                else:
                    lines.append("")

        return "\n".join(lines)

    @classmethod
    def to_txt(cls, notes: Dict[str, Any], subject: str = "General") -> str:
        """Converts notes dict into formatted plain text."""
        lines = []
        divider = "=" * 70
        sub_divider = "-" * 70

        title = notes.get("title", "Lecture Notes")
        lines.append(divider)
        lines.append(f"SMART NOTES: {title.upper()}")
        lines.append(f"Subject: {subject}")
        lines.append(divider)
        lines.append("")

        # Overview
        overview = notes.get("overview", "")
        if overview:
            lines.append("OVERVIEW")
            lines.append(sub_divider)
            lines.append(overview)
            lines.append("")

        # Sections
        sections = notes.get("sections", [])
        if sections:
            lines.append("LECTURE TOPICS & KEY POINTS")
            lines.append(sub_divider)
            for idx, sec in enumerate(sections, 1):
                heading = sec.get("heading", f"Topic {idx}")
                lines.append(f"\n[{idx}] {heading.upper()}")

                key_points = sec.get("key_points", [])
                if key_points:
                    lines.append("  Key Points:")
                    for kp in key_points:
                        lines.append(f"    * {kp}")

                definitions = sec.get("definitions", [])
                if definitions:
                    lines.append("  Definitions:")
                    for d in definitions:
                        lines.append(f"    * {d.get('term', '')}: {d.get('meaning', '')}")

                examples = sec.get("examples", [])
                if examples:
                    lines.append("  Examples:")
                    for ex in examples:
                        lines.append(f"    * {ex}")
            lines.append("")

        # Formulas
        formulas = notes.get("formulas", [])
        if formulas:
            lines.append("FORMULAS & EQUATIONS")
            lines.append(sub_divider)
            for f in formulas:
                if isinstance(f, dict):
                    lines.append(f"  * {f.get('name', 'Formula')}: {f.get('formula', '')}")
                    lines.append(f"    Meaning: {f.get('explanation', '')}")
                else:
                    lines.append(f"  * {f}")
            lines.append("")

        # Glossary
        glossary = notes.get("glossary", [])
        if glossary:
            lines.append("GLOSSARY")
            lines.append(sub_divider)
            for g in glossary:
                if isinstance(g, dict):
                    lines.append(f"  * {g.get('term', '')} - {g.get('meaning', g.get('definition', ''))}")
                else:
                    lines.append(f"  * {g}")
            lines.append("")

        # Summary
        summary = notes.get("summary", "")
        if summary:
            lines.append("SUMMARY")
            lines.append(sub_divider)
            lines.append(summary)
            lines.append("")

        # Revision Q&A
        rev_q = notes.get("revision_questions", [])
        if rev_q:
            lines.append("REVISION QUESTIONS & ANSWERS")
            lines.append(sub_divider)
            for i, q in enumerate(rev_q, 1):
                lines.append(f"  Q{i}: {q.get('question', '')}")
                lines.append(f"  Ans: {q.get('answer', '')}\n")

        # MCQs
        mcqs = notes.get("mcqs", [])
        if mcqs:
            lines.append("PRACTICE MCQS")
            lines.append(sub_divider)
            for i, mcq in enumerate(mcqs, 1):
                lines.append(f"  {i}. {mcq.get('question', '')}")
                for opt in mcq.get("options", []):
                    lines.append(f"     {opt}")
                lines.append(f"     [Correct Answer: {mcq.get('correct_answer', '')}]")
                if mcq.get("explanation"):
                    lines.append(f"     Explanation: {mcq.get('explanation')}")
                lines.append("")

        return "\n".join(lines)

    @classmethod
    def to_pdf_bytes(cls, notes: Dict[str, Any], subject: str = "General") -> bytes:
        """
        Builds a styled PDF document in memory using ReportLab
        and returns the raw PDF bytes.
        """
        buffer = io.BytesIO()

        # Page setup: Letter size with 0.75-inch margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        # Custom academic palette
        PRIMARY = colors.HexColor("#312E81")     # Deep Indigo
        ACCENT = colors.HexColor("#4F46E5")      # Indigo 600
        DARK_TEXT = colors.HexColor("#0F172A")   # Slate 900
        BODY_TEXT = colors.HexColor("#334155")   # Slate 700
        LIGHT_BG = colors.HexColor("#F8FAFC")    # Slate 50
        BORDER_COL = colors.HexColor("#CBD5E1")  # Slate 300
        EMERALD = colors.HexColor("#059669")

        # Typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=PRIMARY,
            fontName="Helvetica-Bold",
            spaceAfter=6
        )

        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=12,
            textColor=colors.white,
            fontName="Helvetica-Bold"
        )

        h1_style = ParagraphStyle(
            "SectionH1",
            parent=styles["Heading2"],
            fontSize=15,
            leading=18,
            textColor=PRIMARY,
            fontName="Helvetica-Bold",
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )

        h2_style = ParagraphStyle(
            "SubH2",
            parent=styles["Heading3"],
            fontSize=12,
            leading=15,
            textColor=ACCENT,
            fontName="Helvetica-Bold",
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=BODY_TEXT,
            fontName="Helvetica",
            spaceAfter=6
        )

        bullet_style = ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13.5,
            textColor=BODY_TEXT,
            fontName="Helvetica",
            leftIndent=14,
            spaceAfter=3
        )

        def_term_style = ParagraphStyle(
            "DefTerm",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=PRIMARY,
            fontName="Helvetica-Bold"
        )

        story = []

        # 1. Header Banner
        title = notes.get("title", "Lecture Notes")
        story.append(Paragraph(title, title_style))

        # Subject and metadata badge bar
        badge_data = [[
            Paragraph(f"<b>Subject:</b> {subject.upper()}", ParagraphStyle("Subj", parent=body_style, textColor=PRIMARY)),
            Paragraph(f"<b>Detail:</b> {notes.get('_meta', {}).get('detail_level', 'Standard').capitalize()}", ParagraphStyle("Det", parent=body_style, textColor=PRIMARY, alignment=2))
        ]]
        badge_table = Table(badge_data, colWidths=[250, 250])
        badge_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2FF")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2FE")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(badge_table)
        story.append(Spacer(1, 12))

        # 2. Overview Callout Box
        overview = notes.get("overview", "")
        if overview:
            story.append(Paragraph("Lecture Overview", h1_style))
            overview_data = [[Paragraph(overview, body_style)]]
            overview_table = Table(overview_data, colWidths=[500])
            overview_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                ("LINELEFT", (0, 0), (0, -1), 3.5, ACCENT),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(overview_table)
            story.append(Spacer(1, 10))

        # 3. Sections & Topics
        sections = notes.get("sections", [])
        if sections:
            story.append(Paragraph("Lecture Topics & Core Material", h1_style))
            story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COL, spaceAfter=8))

            for idx, sec in enumerate(sections, 1):
                sec_elements = []
                heading = sec.get("heading", f"Topic {idx}")
                sec_elements.append(Paragraph(f"{idx}. {heading}", h2_style))

                # Key Points
                key_points = sec.get("key_points", [])
                if key_points:
                    sec_elements.append(Paragraph("<b>Key Points:</b>", bullet_style))
                    for kp in key_points:
                        sec_elements.append(Paragraph(f"• {kp}", bullet_style))
                    sec_elements.append(Spacer(1, 4))

                # Definitions
                definitions = sec.get("definitions", [])
                if definitions:
                    for d in definitions:
                        term = d.get("term", "")
                        meaning = d.get("meaning", "")
                        sec_elements.append(Paragraph(f"<b>Definition ({term}):</b> {meaning}", bullet_style))
                    sec_elements.append(Spacer(1, 4))

                # Examples
                examples = sec.get("examples", [])
                if examples:
                    for ex in examples:
                        sec_elements.append(Paragraph(f"<i>Example:</i> {ex}", bullet_style))
                    sec_elements.append(Spacer(1, 4))

                sec_elements.append(Spacer(1, 6))
                story.append(KeepTogether(sec_elements))

        # 4. Formulas
        formulas = notes.get("formulas", [])
        if formulas:
            story.append(Spacer(1, 6))
            story.append(Paragraph("Important Formulas & Equations", h1_style))
            formula_rows = [["Formula / Law", "Explanation"]]
            for f in formulas:
                if isinstance(f, dict):
                    f_name = f.get("name", "Equation")
                    f_val = f.get("formula", "")
                    f_exp = f.get("explanation", "")
                    content_str = f"<b>{f_name}</b><br/><font color='#4F46E5'><b>{f_val}</b></font>"
                    formula_rows.append([Paragraph(content_str, body_style), Paragraph(f_exp, body_style)])
                else:
                    formula_rows.append([Paragraph(f"<b>{f}</b>", body_style), Paragraph("Identified in lecture", body_style)])

            f_table = Table(formula_rows, colWidths=[200, 300])
            f_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), PRIMARY),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COL),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(f_table)

        # 5. Glossary
        glossary = notes.get("glossary", [])
        if glossary:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Glossary of Key Terms", h1_style))
            glossary_rows = [["Term", "Definition"]]
            for g in glossary:
                if isinstance(g, dict):
                    t = g.get("term", "")
                    m = g.get("meaning", g.get("definition", ""))
                    glossary_rows.append([Paragraph(f"<b>{t}</b>", def_term_style), Paragraph(m, body_style)])
                else:
                    glossary_rows.append([Paragraph(f"<b>Term</b>", def_term_style), Paragraph(str(g), body_style)])

            g_table = Table(glossary_rows, colWidths=[150, 350])
            g_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COL),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(g_table)

        # 6. Summary
        summary = notes.get("summary", "")
        if summary:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Summary & Key Takeaways", h1_style))
            story.append(Paragraph(summary, body_style))

        # 7. Revision Questions
        rev_q = notes.get("revision_questions", [])
        if rev_q:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Revision Questions & Model Answers", h1_style))
            for i, q in enumerate(rev_q, 1):
                q_elem = [
                    Paragraph(f"<b>Q{i}:</b> {q.get('question', '')}", h2_style),
                    Paragraph(f"<b>Model Answer:</b> {q.get('answer', '')}", body_style),
                    Spacer(1, 4)
                ]
                story.append(KeepTogether(q_elem))

        # 8. MCQs
        mcqs = notes.get("mcqs", [])
        if mcqs:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Multiple-Choice Self-Assessment", h1_style))
            for i, mcq in enumerate(mcqs, 1):
                mcq_elem = [
                    Paragraph(f"<b>Question {i}:</b> {mcq.get('question', '')}", h2_style),
                ]
                for opt in mcq.get("options", []):
                    mcq_elem.append(Paragraph(f"• {opt}", bullet_style))
                ans_str = f"<b>Correct Answer:</b> <font color='#059669'>{mcq.get('correct_answer', '')}</font>"
                if mcq.get("explanation"):
                    ans_str += f"<br/><i>Explanation:</i> {mcq.get('explanation')}"
                mcq_elem.append(Paragraph(ans_str, body_style))
                mcq_elem.append(Spacer(1, 6))
                story.append(KeepTogether(mcq_elem))

        # Build document with custom two-pass NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer.getvalue()
