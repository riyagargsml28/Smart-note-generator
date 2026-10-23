"""
Topic Segmentation and Chunking Service.
Divides long lecture transcripts into logical, topic-based sections using
transition markers, paragraph boundaries, and smart length chunking.
"""

import re
from typing import List, Dict, Any


class TopicSegmenter:
    """Segments long transcripts into coherent topic units for AI processing."""

    # Transition phrases professors frequently use when changing topics
    TRANSITION_PATTERNS = [
        r"(?:now\s+let['’]?s\s+(?:turn\s+to|discuss|look\s+at|talk\s+about|move\s+to|explore))",
        r"(?:moving\s+on\s+to)",
        r"(?:the\s+next\s+(?:topic|concept|section|idea|part|thing)\s+(?:is|we['’]?ll\s+cover))",
        r"(?:another\s+(?:important|critical|key)\s+(?:concept|point|aspect|topic))",
        r"(?:let['’]?s\s+(?:shift\s+our\s+focus\s+to|examine|analyze))",
        r"(?:first(?:ly)?,\s+|second(?:ly)?,\s+|third(?:ly)?,\s+|finally,\s+)",
        r"(?:in\s+contrast\s+to\s+that|on\s+the\s+other\s+hand)",
        r"(?:to\s+summarize\s+what\s+we['’]?ve\s+seen|in\s+conclusion)",
    ]

    @classmethod
    def segment_transcript(cls, text: str, max_chunk_words: int = 1200, min_chunk_words: int = 250) -> List[Dict[str, Any]]:
        """
        Segments a transcript into topic-based chunks.

        Args:
            text: Cleaned transcript text.
            max_chunk_words: Target maximum words per segment to fit LLM prompts gracefully.
            min_chunk_words: Minimum words before splitting on a transition.

        Returns:
            List of segments: [{"index": int, "title": str, "content": str, "word_count": int}]
        """
        if not text or not text.strip():
            return []

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        total_words = len(text.split())

        # If transcript is relatively short, keep as single or dual topic
        if total_words <= max_chunk_words:
            title = cls._extract_topic_title(paragraphs[0])
            return [{
                "index": 1,
                "title": title or "Introduction and Core Lecture Material",
                "content": text.strip(),
                "word_count": total_words
            }]

        segments = []
        current_paragraphs = []
        current_word_count = 0
        segment_index = 1

        for i, para in enumerate(paragraphs):
            para_words = len(para.split())
            is_transition = cls._is_topic_transition(para)

            # Split if we encounter a topic transition and we already have enough content,
            # or if adding this paragraph exceeds our maximum chunk size.
            should_split = False
            if current_word_count >= min_chunk_words and is_transition:
                should_split = True
            elif current_word_count + para_words > max_chunk_words and current_paragraphs:
                should_split = True

            if should_split and current_paragraphs:
                chunk_text = "\n\n".join(current_paragraphs)
                chunk_title = cls._extract_topic_title(current_paragraphs[0]) or f"Topic Section {segment_index}"
                segments.append({
                    "index": segment_index,
                    "title": chunk_title,
                    "content": chunk_text,
                    "word_count": current_word_count
                })
                segment_index += 1
                current_paragraphs = [para]
                current_word_count = para_words
            else:
                current_paragraphs.append(para)
                current_word_count += para_words

        # Append final segment
        if current_paragraphs:
            chunk_text = "\n\n".join(current_paragraphs)
            chunk_title = cls._extract_topic_title(current_paragraphs[0]) or f"Topic Section {segment_index}"
            segments.append({
                "index": segment_index,
                "title": chunk_title,
                "content": chunk_text,
                "word_count": current_word_count
            })

        return segments

    @classmethod
    def _is_topic_transition(cls, paragraph: str) -> bool:
        """Checks if the paragraph begins with or contains a strong topic transition."""
        first_sentence = paragraph.split(".")[0].strip()
        for pattern in cls.TRANSITION_PATTERNS:
            if re.search(pattern, first_sentence, flags=re.IGNORECASE):
                return True
        return False

    @classmethod
    def _extract_topic_title(cls, paragraph: str) -> str:
        """Infers a reasonable short title from the first sentence of a paragraph."""
        if not paragraph:
            return ""

        first_sentence = paragraph.split(".")[0].strip()
        # Remove leading transitions
        clean_sentence = re.sub(
            r"^(?:Now\s+let['’]?s\s+(?:talk\s+about|look\s+at|discuss|turn\s+to)|"
            r"Moving\s+on\s+to|The\s+next\s+topic\s+is|Let['’]?s\s+examine|Secondly,|Finally,)\s*",
            "",
            first_sentence,
            flags=re.IGNORECASE
        ).strip()

        # Limit to 6-8 words for a crisp section title
        words = clean_sentence.split()
        if len(words) > 7:
            title = " ".join(words[:7]).rstrip(",;:") + "..."
        else:
            title = " ".join(words).rstrip(",;:")

        if title:
            # Capitalize first letter
            return title[0].upper() + title[1:]
        return ""
