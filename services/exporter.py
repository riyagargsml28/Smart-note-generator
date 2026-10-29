"""
Notes Exporter Service.
Exports structured lecture notes to:
1. Markdown (.md)
2. Plain Text (.txt)
3. Formatted PDF (.pdf) using ReportLab with clean academic styling and Hindi/English/Bilingual font support.
"""

import io
import os
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Unicode Font for Hindi (Devanagari) & Bilingual PDF exports
UNICODE_FONT = "Helvetica"
UNICODE_FONT_BOLD = "Helvetica-Bold"

_font_candidates = [
    (r"C:\Windows\Fonts\Nirmala.ttc", 0, "Nirmala"),
    (r"C:\Windows\Fonts\mangal.ttf", None, "Mangal"),
    (r"C:\Windows\Fonts\aparaj.ttf", None, "Aparajita"),
    (r"/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf", None, "NotoSansDevanagari"),
]
for _fpath, _sidx, _fname in _font_candidates:
    if os.path.exists(_fpath):
        try:
            if _sidx is not None:
                pdfmetrics.registerFont(TTFont(_fname, _fpath, subfontIndex=_sidx))
            else:
                pdfmetrics.registerFont(TTFont(_fname, _fpath))
            UNICODE_FONT = _fname
            UNICODE_FONT_BOLD = _fname
            break
        except Exception:
            continue


def has_devanagari(text: str) -> bool:
    """Checks if the given string contains Devanagari (Hindi) Unicode characters."""
    if not text:
        return False
    return any(0x0900 <= ord(c) <= 0x097F for c in text)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page numbers and running footers."""

    def __init__(self, *args, **kwargs):
        self.font_name = kwargs.pop("font_name", "Helvetica")
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
        self.setFont(self.font_name, 9)
        self.setFillColor(colors.HexColor("#64748B"))  # Slate-500

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Smart Notes Generator — Study Guide / अध्ययन गाइड")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer
        footer_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(8.5 * inch - 54, 36, footer_text)
        self.drawString(54, 36, "Smart Notes AI — Academic Study Companion")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * inch - 54, 48)

        self.restoreState()


class NotesExporter:
    """Exports structured notes to Markdown, TXT, and PDF with Hindi, English, and Bilingual support."""

    @classmethod
    def to_markdown(cls, notes: Dict[str, Any], subject: str = "General") -> str:
        """Converts notes dict into formatted Markdown."""
        lines = []
        title = notes.get("title", "Lecture Notes")
        lang = notes.get("_meta", {}).get("language", "english").upper()
        lines.append(f"# {title}\n")
        lines.append(f"**Subject:** {subject} | **Language:** {lang}\n")

        # Overview
        overview = notes.get("overview", "")
        if overview:
            lines.append("## Overview / अवलोकन\n")
            lines.append(f"{overview}\n")

        # Sections
        sections = notes.get("sections", [])
        if sections:
            lines.append("## Lecture Content & Key Concepts / मुख्य अध्ययन बिंदु\n")
            for idx, sec in enumerate(sections, 1):
                heading = sec.get("heading", f"Section {idx}")
                lines.append(f"### {idx}. {heading}\n")

                key_points = sec.get("key_points", [])
                if key_points:
                    lines.append("**Key Points:**")
                    for kp in key_points:
                        lines.append(f"- {kp}")
                    lines.append("")

                definitions = sec.get("definitions", [])
                if definitions:
                    lines.append("**Key Definitions:**")
                    for d in definitions:
                        term = d.get("term", "")
                        meaning = d.get("meaning", "")
                        lines.append(f"- **{term}:** {meaning}")
                    lines.append("")

                examples = sec.get("examples", [])
                if examples:
                    lines.append("**Examples & Explanations:**")
                    for ex in examples:
                        lines.append(f"- {ex}")
                    lines.append("")

        # Formulas
        formulas = notes.get("formulas", [])
        if formulas:
            lines.append("## Important Formulas & Mathematical Models / महत्वपूर्ण सूत्र\n")
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
            lines.append("## Glossary of Terms / शब्दावली\n")
            lines.append("| Term / पद | Definition / परिभाषा |")
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
            lines.append("## Summary & Conclusion / निष्कर्ष सारांश\n")
            lines.append(f"{summary}\n")

        # Revision Questions
        rev_q = notes.get("revision_questions", [])
        if rev_q:
            lines.append("## Revision Questions & Answers / पुनरीक्षण प्रश्न एवं उत्तर\n")
            for i, q in enumerate(rev_q, 1):
                ques = q.get("question", "")
                ans = q.get("answer", "")
                lines.append(f"**Q{i}: {ques}**\n")
                lines.append(f"> **Answer:** {ans}\n")

        # MCQs
        mcqs = notes.get("mcqs", [])
        if mcqs:
            lines.append("## Multiple-Choice Questions / Practice Quiz (MCQs) / अभ्यास प्रश्नोत्तरी\n")
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
        lang = notes.get("_meta", {}).get("language", "english").upper()
        lines.append(divider)
        lines.append(f"SMART NOTES: {title.upper()}")
        lines.append(f"Subject: {subject} | Language: {lang}")
        lines.append(divider)
        lines.append("")

        overview = notes.get("overview", "")
        if overview:
            lines.append("OVERVIEW / अवलोकन")
            lines.append(sub_divider)
            lines.append(overview)
            lines.append("")

        sections = notes.get("sections", [])
        if sections:
            lines.append("LECTURE TOPICS & KEY POINTS / मुख्य विषय")
            lines.append(sub_divider)
            for idx, sec in enumerate(sections, 1):
                heading = sec.get("heading", f"Topic {idx}")
                lines.append(f"\n[{idx}] {heading}")

                key_points = sec.get("key_points", [])
                if key_points:
                    lines.append("  Key Points / मुख्य बिंदु:")
                    for kp in key_points:
                        lines.append(f"    * {kp}")

                definitions = sec.get("definitions", [])
                if definitions:
                    lines.append("  Definitions / परिभाषाएँ:")
                    for d in definitions:
                        lines.append(f"    * {d.get('term', '')}: {d.get('meaning', '')}")

                examples = sec.get("examples", [])
                if examples:
                    lines.append("  Examples / उदाहरण:")
                    for ex in examples:
                        lines.append(f"    * {ex}")
            lines.append("")

        formulas = notes.get("formulas", [])
        if formulas:
            lines.append("FORMULAS & EQUATIONS / महत्वपूर्ण सूत्र")
            lines.append(sub_divider)
            for f in formulas:
                if isinstance(f, dict):
                    lines.append(f"  * {f.get('name', 'Formula')}: {f.get('formula', '')}")
                    lines.append(f"    Meaning: {f.get('explanation', '')}")
                else:
                    lines.append(f"  * {f}")
            lines.append("")

        glossary = notes.get("glossary", [])
        if glossary:
            lines.append("GLOSSARY / शब्दावली")
            lines.append(sub_divider)
            for g in glossary:
                if isinstance(g, dict):
                    lines.append(f"  * {g.get('term', '')} - {g.get('meaning', g.get('definition', ''))}")
                else:
                    lines.append(f"  * {g}")
            lines.append("")

        summary = notes.get("summary", "")
        if summary:
            lines.append("SUMMARY / निष्कर्ष सारांश")
            lines.append(sub_divider)
            lines.append(summary)
            lines.append("")

        rev_q = notes.get("revision_questions", [])
        if rev_q:
            lines.append("REVISION QUESTIONS & ANSWERS / पुनरीक्षण प्रश्न")
            lines.append(sub_divider)
            for i, q in enumerate(rev_q, 1):
                lines.append(f"  Q{i}: {q.get('question', '')}")
                lines.append(f"  Ans: {q.get('answer', '')}\n")

        mcqs = notes.get("mcqs", [])
        if mcqs:
            lines.append("PRACTICE MCQS / अभ्यास प्रश्नोत्तरी")
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
        Builds a styled PDF document in memory using ReportLab.
        Automatically uses Unicode font (Nirmala) when Hindi / Devanagari text is present.
        """
        buffer = io.BytesIO()

        # Detect if Hindi text is present in notes content
        sample_text = f"{notes.get('title', '')} {notes.get('overview', '')} {notes.get('summary', '')}"
        lang = notes.get("_meta", {}).get("language", "").lower()
        use_unicode = has_devanagari(sample_text) or lang in ("hindi", "both", "bilingual")

        font_normal = UNICODE_FONT if use_unicode else "Helvetica"
        font_bold = UNICODE_FONT_BOLD if use_unicode else "Helvetica-Bold"

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        PRIMARY = colors.HexColor("#312E81")
        ACCENT = colors.HexColor("#4F46E5")
        BODY_TEXT = colors.HexColor("#334155")
        LIGHT_BG = colors.HexColor("#F8FAFC")
        BORDER_COL = colors.HexColor("#CBD5E1")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18 if use_unicode else 22,
            leading=24 if use_unicode else 26,
            textColor=PRIMARY,
            fontName=font_bold,
            spaceAfter=6
        )

        h1_style = ParagraphStyle(
            "SectionH1",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=PRIMARY,
            fontName=font_bold,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )

        h2_style = ParagraphStyle(
            "SubH2",
            parent=styles["Heading3"],
            fontSize=12,
            leading=16,
            textColor=ACCENT,
            fontName=font_bold,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=15,
            textColor=BODY_TEXT,
            fontName=font_normal,
            spaceAfter=6
        )

        bullet_style = ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=14,
            textColor=BODY_TEXT,
            fontName=font_normal,
            leftIndent=14,
            spaceAfter=3
        )

        def_term_style = ParagraphStyle(
            "DefTerm",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=14,
            textColor=PRIMARY,
            fontName=font_bold
        )

        story = []

        # 1. Header Title & Badge Table
        title = notes.get("title", "Lecture Notes")
        story.append(Paragraph(title, title_style))

        lang_label = "Bilingual (EN + HI)" if lang in ("both", "bilingual") else (lang.upper() if lang else "Standard")
        badge_data = [[
            Paragraph(f"<b>Subject:</b> {subject.upper()}", ParagraphStyle("Subj", parent=body_style, textColor=PRIMARY, fontName=font_bold)),
            Paragraph(f"<b>Language:</b> {lang_label}", ParagraphStyle("Det", parent=body_style, textColor=PRIMARY, alignment=2, fontName=font_bold))
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
            overview_heading = "Lecture Overview / व्याख्यान अवलोकन" if use_unicode else "Lecture Overview"
            story.append(Paragraph(overview_heading, h1_style))
            overview_data = [[Paragraph(overview.replace("\n", "<br/>"), body_style)]]
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
            sec_main_heading = "Lecture Topics & Core Material / मुख्य अध्ययन सामग्री" if use_unicode else "Lecture Topics & Core Material"
            story.append(Paragraph(sec_main_heading, h1_style))
            story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COL, spaceAfter=8))

            for idx, sec in enumerate(sections, 1):
                sec_elements = []
                heading = sec.get("heading", f"Topic {idx}")
                sec_elements.append(Paragraph(f"{idx}. {heading}", h2_style))

                key_points = sec.get("key_points", [])
                if key_points:
                    kp_label = "<b>Key Points / मुख्य बिंदु:</b>" if use_unicode else "<b>Key Points:</b>"
                    sec_elements.append(Paragraph(kp_label, bullet_style))
                    for kp in key_points:
                        sec_elements.append(Paragraph(f"• {kp}", bullet_style))
                    sec_elements.append(Spacer(1, 4))

                definitions = sec.get("definitions", [])
                if definitions:
                    for d in definitions:
                        term = d.get("term", "")
                        meaning = d.get("meaning", "")
                        def_label = "Definition / परिभाषा" if use_unicode else "Definition"
                        sec_elements.append(Paragraph(f"<b>{def_label} ({term}):</b> {meaning}", bullet_style))
                    sec_elements.append(Spacer(1, 4))

                examples = sec.get("examples", [])
                if examples:
                    for ex in examples:
                        sec_elements.append(Paragraph(f"<i>Example / उदाहरण:</i> {ex}", bullet_style))
                    sec_elements.append(Spacer(1, 4))

                sec_elements.append(Spacer(1, 6))
                story.append(KeepTogether(sec_elements))

        # 4. Formulas
        formulas = notes.get("formulas", [])
        if formulas:
            story.append(Spacer(1, 6))
            formula_heading = "Important Formulas & Equations / महत्वपूर्ण सूत्र" if use_unicode else "Important Formulas & Equations"
            story.append(Paragraph(formula_heading, h1_style))
            formula_rows = [["Formula / Law", "Explanation / व्याख्या"]]
            for f in formulas:
                if isinstance(f, dict):
                    f_name = f.get("name", "Equation")
                    f_val = f.get("formula", "")
                    f_exp = f.get("explanation", "")
                    content_str = f"<b>{f_name}</b><br/><font color='#4F46E5'><b>{f_val}</b></font>"
                    formula_rows.append([Paragraph(content_str, body_style), Paragraph(f_exp, body_style)])
                else:
                    formula_rows.append([Paragraph(f"<b>{f}</b>", body_style), Paragraph("Formula identified in lecture", body_style)])

            f_table = Table(formula_rows, colWidths=[200, 300])
            f_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), PRIMARY),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COL),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(f_table)

        # 5. Glossary
        glossary = notes.get("glossary", [])
        if glossary:
            story.append(Spacer(1, 10))
            glossary_heading = "Glossary of Key Terms / शब्दावली" if use_unicode else "Glossary of Key Terms"
            story.append(Paragraph(glossary_heading, h1_style))
            glossary_rows = [["Term / पद", "Definition / परिभाषा"]]
            for g in glossary:
                if isinstance(g, dict):
                    t = g.get("term", "")
                    m = g.get("meaning", g.get("definition", ""))
                    glossary_rows.append([Paragraph(f"<b>{t}</b>", def_term_style), Paragraph(m, body_style)])
                else:
                    glossary_rows.append([Paragraph(f"<b>Term</b>", def_term_style), Paragraph(str(g), body_style)])

            g_table = Table(glossary_rows, colWidths=[160, 340])
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
            summary_heading = "Summary & Key Takeaways / निष्कर्ष सारांश" if use_unicode else "Summary & Key Takeaways"
            story.append(Paragraph(summary_heading, h1_style))
            story.append(Paragraph(summary.replace("\n", "<br/>"), body_style))

        # 7. Revision Questions
        rev_q = notes.get("revision_questions", [])
        if rev_q:
            story.append(Spacer(1, 10))
            rev_heading = "Revision Questions & Model Answers / पुनरीक्षण प्रश्न एवं उत्तर" if use_unicode else "Revision Questions & Model Answers"
            story.append(Paragraph(rev_heading, h1_style))
            for i, q in enumerate(rev_q, 1):
                ans_text = q.get("answer", "").replace("\n", "<br/>")
                ans_label = "Model Answer / आदर्श उत्तर" if use_unicode else "Model Answer"
                q_elem = [
                    Paragraph(f"<b>Q{i}:</b> {q.get('question', '')}", h2_style),
                    Paragraph(f"<b>{ans_label}:</b> {ans_text}", body_style),
                    Spacer(1, 4)
                ]
                story.append(KeepTogether(q_elem))

        # 8. MCQs
        mcqs = notes.get("mcqs", [])
        if mcqs:
            story.append(Spacer(1, 10))
            quiz_heading = "Practice Quiz (MCQs) / अभ्यास प्रश्नोत्तरी" if use_unicode else "Multiple-Choice Self-Assessment"
            story.append(Paragraph(quiz_heading, h1_style))
            for i, mcq in enumerate(mcqs, 1):
                mcq_elem = [
                    Paragraph(f"<b>Question {i}:</b> {mcq.get('question', '')}", h2_style),
                ]
                for opt in mcq.get("options", []):
                    mcq_elem.append(Paragraph(f"• {opt}", bullet_style))
                ans_label = "Correct Answer / सही उत्तर" if use_unicode else "Correct Answer"
                ans_str = f"<b>{ans_label}:</b> <font color='#059669'>{mcq.get('correct_answer', '')}</font>"
                if mcq.get("explanation"):
                    exp_label = "Explanation / स्पष्टीकरण" if use_unicode else "Explanation"
                    ans_str += f"<br/><i>{exp_label}:</i> {mcq.get('explanation')}"
                mcq_elem.append(Paragraph(ans_str, body_style))
                mcq_elem.append(Spacer(1, 6))
                story.append(KeepTogether(mcq_elem))

        # Build document with custom canvas
        def make_canvas(*args, **kwargs):
            return NumberedCanvas(*args, font_name=font_normal, **kwargs)

        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer.getvalue()
