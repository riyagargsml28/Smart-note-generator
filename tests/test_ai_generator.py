"""
Tests for AI Notes Generator & Pydantic Schema.
Verifies that all timestamps are thoroughly purged from generated notes,
question answers, and practice quizzes.
"""

import unittest
import re
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

    def test_timestamps_removed_from_notes_questions_and_quizzes(self):
        """
        Verifies that when a lecture transcript contains pervasive timestamps,
        no timestamps leak into notes, question answers, or practice quizzes.
        """
        raw_transcript_with_timestamps = (
            "[00:00:05] Professor Davis: Welcome everyone to today's lecture. "
            "[00:00:15] Today we're going to dive into Virtual Memory and Paging. "
            "[00:01:23] Virtual memory is defined as a storage allocation scheme in which secondary memory is treated as main memory. "
            "[00:02:45] At 02:45, a page fault occurs when a program attempts to access an unmapped page. "
            "[00:03:50] The Effective Access Time is calculated using the formula: EAT = (1 - p) * ma + p * page_fault_time. "
            "[00:05:10] (05:10) In FIFO replacement, Belady's Anomaly can cause more page faults with more frames. "
            "[00:06:20] In summary, virtual memory guarantees process isolation and expands usable storage."
        )

        notes = self.generator.generate_notes(
            raw_transcript_with_timestamps,
            subject="Computer Science",
            detail_level="medium"
        )

        timestamp_regex = re.compile(r"\[\d{1,2}:\d{2}(?::\d{2})?\]|\(\d{1,2}:\d{2}\)|\b\d{1,2}:\d{2}:\d{2}\b")

        # 1. Notes Title, Overview, and Summary
        self.assertFalse(timestamp_regex.search(notes["title"]), f"Timestamp found in title: {notes['title']}")
        self.assertFalse(timestamp_regex.search(notes["overview"]), f"Timestamp found in overview: {notes['overview']}")
        self.assertFalse(timestamp_regex.search(notes["summary"]), f"Timestamp found in summary: {notes['summary']}")

        # 2. Sections, Headings, Key Points, Definitions, Examples
        for sec in notes.get("sections", []):
            self.assertFalse(timestamp_regex.search(sec["heading"]), f"Timestamp in section heading: {sec['heading']}")
            for kp in sec.get("key_points", []):
                self.assertFalse(timestamp_regex.search(kp), f"Timestamp in key point: {kp}")
            for d in sec.get("definitions", []):
                self.assertFalse(timestamp_regex.search(d["term"]), f"Timestamp in definition term: {d['term']}")
                self.assertFalse(timestamp_regex.search(d["meaning"]), f"Timestamp in definition meaning: {d['meaning']}")
            for ex in sec.get("examples", []):
                self.assertFalse(timestamp_regex.search(ex), f"Timestamp in example: {ex}")

        # 3. Revision Questions & Answers
        self.assertGreater(len(notes["revision_questions"]), 0)
        for rq in notes["revision_questions"]:
            self.assertFalse(timestamp_regex.search(rq["question"]), f"Timestamp found in revision question: {rq['question']}")
            self.assertFalse(timestamp_regex.search(rq["answer"]), f"Timestamp found in revision answer: {rq['answer']}")

        # 4. Practice Quizzes (MCQs)
        self.assertGreater(len(notes["mcqs"]), 0)
        for mcq in notes["mcqs"]:
            self.assertFalse(timestamp_regex.search(mcq["question"]), f"Timestamp found in MCQ question: {mcq['question']}")
            for opt in mcq["options"]:
                self.assertFalse(timestamp_regex.search(opt), f"Timestamp found in MCQ option: {opt}")
            self.assertFalse(timestamp_regex.search(mcq["correct_answer"]), f"Timestamp found in MCQ correct_answer: {mcq['correct_answer']}")
            self.assertFalse(timestamp_regex.search(mcq["explanation"]), f"Timestamp found in MCQ explanation: {mcq['explanation']}")


if __name__ == "__main__":
    unittest.main()
