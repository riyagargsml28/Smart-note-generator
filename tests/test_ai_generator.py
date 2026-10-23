"""
Tests for AI Notes Generator & Pydantic Schema.
"""

import unittest
from services.ai_generator import AINotesGenerator, LectureNotes


class TestAINotesGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = AINotesGenerator(api_key=None)  # Use heuristic fallback engine

    def test_schema_validation(self):
        sample_json = {
            "title": "Quantum Physics Notes",
            "overview": "Overview of quantum mechanics.",
            "sections": [
                {
                    "heading": "Wave-Particle Duality",
                    "key_points": ["Photons have both wave and particle properties."],
                    "definitions": [{"term": "Photon", "meaning": "Quantum of electromagnetic radiation."}],
                    "examples": ["Photoelectric effect"]
                }
            ],
            "formulas": [{"name": "Energy", "formula": "E = h * f", "explanation": "Planck relation"}],
            "glossary": [{"term": "Photon", "meaning": "Light particle"}],
            "summary": "Quantum mechanics revolutionizes our view of atomic physics.",
            "revision_questions": [{"question": "What is a photon?", "answer": "A quantum of light."}],
            "mcqs": [
                {
                    "question": "What is Planck's constant represented by?",
                    "options": ["A) h", "B) c", "C) G", "D) k"],
                    "correct_answer": "A) h",
                    "explanation": "h denotes Planck's constant."
                }
            ]
        }
        validated = LectureNotes.model_validate(sample_json)
        self.assertEqual(validated.title, "Quantum Physics Notes")
        self.assertEqual(len(validated.sections), 1)
        self.assertEqual(len(validated.mcqs), 1)

    def test_heuristic_generator_output(self):
        sample_text = (
            "Virtual memory is defined as a storage allocation scheme in which secondary memory "
            "can be addressed as though it were part of main memory. "
            "Paging breaks virtual address space into pages. "
            "A page fault occurs when a program attempts to access an unmapped page. "
            "The effective access time formula is EAT = (1 - p) * ma + p * page_fault_time. "
            "For example, reading from an SSD takes 10 milliseconds compared to 100 nanoseconds for RAM. "
            "In summary, virtual memory ensures memory protection and expands usable storage."
        )

        notes = self.generator.generate_notes(sample_text, subject="Computer Science", detail_level="medium")

        self.assertIn("title", notes)
        self.assertIn("overview", notes)
        self.assertIn("sections", notes)
        self.assertIn("formulas", notes)
        self.assertIn("glossary", notes)
        self.assertIn("summary", notes)
        self.assertIn("revision_questions", notes)
        self.assertIn("mcqs", notes)
        self.assertGreater(len(notes["sections"]), 0)


if __name__ == "__main__":
    unittest.main()
