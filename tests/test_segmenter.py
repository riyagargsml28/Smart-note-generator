"""
Tests for Topic Segmenter Service.
"""

import unittest
from services.segmenter import TopicSegmenter


class TestTopicSegmenter(unittest.TestCase):

    def test_short_transcript_segmentation(self):
        short_text = "Today we discuss quantum mechanics. The wave function describes the quantum state of a particle."
        segments = TopicSegmenter.segment_transcript(short_text, max_chunk_words=1000)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["index"], 1)
        self.assertIn("quantum mechanics", segments[0]["content"].lower())

    def test_transition_segmentation(self):
        p1 = "First, let us examine classical mechanics. " * 30
        p2 = "Now let's turn to quantum duality and wave mechanics. " * 30
        p3 = "Moving on to the uncertainty principle. " * 30
        full_text = f"{p1}\n\n{p2}\n\n{p3}"

        segments = TopicSegmenter.segment_transcript(full_text, max_chunk_words=300, min_chunk_words=100)
        self.assertGreaterEqual(len(segments), 2)
        for seg in segments:
            self.assertTrue("title" in seg)
            self.assertTrue("content" in seg)
            self.assertGreater(seg["word_count"], 0)


if __name__ == "__main__":
    unittest.main()
