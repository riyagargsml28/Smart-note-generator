"""
Tests for Notes Exporter (PDF, Markdown, TXT).
"""

import unittest
from services.exporter import NotesExporter


class TestNotesExporter(unittest.TestCase):

    def setUp(self):
        self.sample_notes = {
            "title": "Introduction to DNA Replication",
            "overview": "DNA replication is the biological process of producing two identical replicas of DNA from one original DNA molecule.",
            "sections": [
                {
                    "heading": "The Replication Fork",
                    "key_points": [
                        "Helicase unwinds the double helix.",
                        "DNA Polymerase builds new strands in the 5' to 3' direction."
                    ],
                    "definitions": [
                        {"term": "Helicase", "meaning": "Enzyme that breaks hydrogen bonds between nucleotide bases."}
                    ],
                    "examples": [
                        "In E. coli, replication proceeds at roughly 1,000 nucleotides per second."
                    ]
                }
            ],
            "formulas": [
                {"name": "Base Pairing", "formula": "A=T, G#C", "explanation": "Hydrogen bond complementation"}
            ],
            "glossary": [
                {"term": "Helicase", "meaning": "Unwinding enzyme"}
            ],
            "summary": "DNA replication guarantees accurate transmission of genetic information across generations.",
            "revision_questions": [
                {"question": "What is the role of DNA helicase?", "answer": "It unwinds the double helix at the replication fork."}
            ],
            "mcqs": [
                {
                    "question": "In which direction does DNA Polymerase synthesize new strands?",
                    "options": ["A) 5' to 3'", "B) 3' to 5'", "C) Bidirectional", "D) 1' to 4'"],
                    "correct_answer": "A) 5' to 3'",
                    "explanation": "DNA Polymerase requires a free 3'-OH group to attach incoming nucleotides."
                }
            ]
        }

    def test_markdown_export(self):
        md = NotesExporter.to_markdown(self.sample_notes, subject="Biology")
        self.assertIn("# Introduction to DNA Replication", md)
        self.assertIn("## Overview", md)
        self.assertIn("Helicase unwinds the double helix", md)
        self.assertIn("## Multiple-Choice Questions", md)

    def test_txt_export(self):
        txt = NotesExporter.to_txt(self.sample_notes, subject="Biology")
        self.assertIn("SMART NOTES: INTRODUCTION TO DNA REPLICATION", txt)
        self.assertIn("OVERVIEW", txt)
        self.assertIn("REVISION QUESTIONS & ANSWERS", txt)

    def test_pdf_export(self):
        pdf_bytes = NotesExporter.to_pdf_bytes(self.sample_notes, subject="Biology")
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 1000)
        # PDF file header verification
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
