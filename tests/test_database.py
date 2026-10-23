"""
Tests for SQLite Database CRUD operations.
"""

import unittest
import tempfile
from pathlib import Path
from database import NotesDatabase


class TestNotesDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_notes.db"
        self.db = NotesDatabase(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_get_note(self):
        structured = {
            "title": "Test Title",
            "overview": "Overview text",
            "sections": [],
            "formulas": [],
            "glossary": [],
            "summary": "Summary",
            "revision_questions": [],
            "mcqs": []
        }
        note_id = self.db.create_note(
            title="Test Title",
            subject="Physics",
            detail_level="medium",
            raw_transcript="raw text",
            cleaned_transcript="clean text",
            structured_notes=structured,
            word_count=100
        )
        self.assertIsInstance(note_id, int)
        self.assertGreater(note_id, 0)

        retrieved = self.db.get_note(note_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["title"], "Test Title")
        self.assertEqual(retrieved["subject"], "Physics")
        self.assertEqual(retrieved["structured_notes"]["overview"], "Overview text")

    def test_update_note(self):
        structured = {"title": "Original"}
        note_id = self.db.create_note("Original", "Biology", "short", "raw", "clean", structured, 50)

        updated = self.db.update_note(note_id, title="Updated Title", subject="Genetics")
        self.assertTrue(updated)

        retrieved = self.db.get_note(note_id)
        self.assertEqual(retrieved["title"], "Updated Title")
        self.assertEqual(retrieved["subject"], "Genetics")

    def test_delete_note(self):
        note_id = self.db.create_note("To Delete", "CS", "short", "raw", "clean", {}, 10)
        deleted = self.db.delete_note(note_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.db.get_note(note_id))

    def test_get_all_notes_and_search(self):
        self.db.create_note("Quantum Mechanics", "Physics", "detailed", "r", "c", {}, 200)
        self.db.create_note("Operating Systems", "Computer Science", "medium", "r", "c", {}, 150)

        all_notes = self.db.get_all_notes()
        self.assertEqual(len(all_notes), 2)

        physics_notes = self.db.get_all_notes(subject_filter="Physics")
        self.assertEqual(len(physics_notes), 1)
        self.assertEqual(physics_notes[0]["title"], "Quantum Mechanics")

        search_notes = self.db.get_all_notes(search_query="Operating")
        self.assertEqual(len(search_notes), 1)
        self.assertEqual(search_notes[0]["title"], "Operating Systems")


if __name__ == "__main__":
    unittest.main()
