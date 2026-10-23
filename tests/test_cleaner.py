"""
Tests for Transcript Cleaner Service.
"""

import unittest
from services.cleaner import TranscriptCleaner


class TestTranscriptCleaner(unittest.TestCase):

    def test_filler_removal(self):
        raw = "Um, so today we are, uh, you know, going to basically talk about virtual memory, sort of."
        cleaned, stats = TranscriptCleaner.clean(raw, remove_fillers=True, remove_timestamps=True)
        self.assertNotIn("Um,", cleaned)
        self.assertNotIn("uh,", cleaned)
        self.assertNotIn("you know", cleaned)
        self.assertNotIn("sort of", cleaned)
        self.assertGreater(stats["fillers_removed"], 0)
        self.assertGreater(stats["reduction_percentage"], 0)

    def test_stutter_removal(self):
        raw = "The the operating system is is allocating memory."
        cleaned, _ = TranscriptCleaner.clean(raw)
        self.assertNotIn("the the", cleaned.lower())
        self.assertNotIn("is is", cleaned.lower())
        self.assertIn("The operating system is allocating memory", cleaned)

    def test_timestamp_and_speaker_removal(self):
        raw = "[00:12:45] Professor Smith: Welcome class. Today we discuss paging.\n(13:10) Speaker 1: What is a page fault?"
        cleaned, _ = TranscriptCleaner.clean(raw, remove_timestamps=True)
        self.assertNotIn("[00:12:45]", cleaned)
        self.assertNotIn("(13:10)", cleaned)
        self.assertNotIn("Professor Smith:", cleaned)
        self.assertIn("Welcome class", cleaned)
        self.assertIn("What is a page fault?", cleaned)

    def test_empty_string(self):
        cleaned, stats = TranscriptCleaner.clean("")
        self.assertEqual(cleaned, "")
        self.assertEqual(stats["original_words"], 0)


if __name__ == "__main__":
    unittest.main()
