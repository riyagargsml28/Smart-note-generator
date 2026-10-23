"""
Smart Transcript Cleaner Module.
Removes verbal fillers, stuttering/repetitions, timestamps, speaker labels,
and formatting artifacts while preserving source meaning and technical terms.
"""

import re
from typing import Dict, Any, Tuple


class TranscriptCleaner:
    """Cleans lecture transcripts for improved readability and optimal AI summarization."""

    # Common spoken filler words and phrases
    FILLER_PHRASES = [
        r"\byou know what I mean\b",
        r"\byou know\b",
        r"\bas I was saying\b",
        r"\bto be honest\b",
        r"\blet's see\b",
        r"\blet me see\b",
        r"\bso yeah\b",
        r"\band so on and so forth\b",
        r"\bsort of\b",
        r"\bkind of\b",
        r"\bat the end of the day\b",
        r"\bif you will\b",
    ]

    FILLER_WORDS = [
        r"\bum+\b",
        r"\buh+\b",
        r"\ber+\b",
        r"\bah+\b",
        r"\bhm+\b",
        r"\bhmm+\b",
    ]

    # Comprehensive Timestamp Patterns:
    # 00:00:00.000 --> 00:00:05.000 (VTT / SRT time ranges)
    # [00:12:34], (12:45), <01:23:45>, [1:23]
    # Standalone HH:MM:SS or MM:SS at line start, within dialogue, or after prepositions
    TIMESTAMP_PATTERNS = [
        # VTT/SRT arrow time ranges
        r"\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*(?:-->|->|–|-)\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?",
        # Prepositions immediately preceding bracketed timestamps: 'at [00:12:34]', 'in (12:45)'
        r"\b(?:at|on|in|around|timestamp|timecode)\s*\[\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\]",
        r"\b(?:at|on|in|around|timestamp|timecode)\s*\(\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\)",
        # Bracketed or parenthesized timestamps anywhere
        r"\[\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\]",
        r"\(\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\)",
        r"\<\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\>",
        # Standalone HH:MM:SS (e.g. 00:12:45, 01:23:45.678)
        r"\b\d{1,2}:\d{2}:\d{2}(?:[\.,]\d{1,3})?\b",
        # Timestamps with prepositions or labels: 'at 04:15', 'timestamp: 12:30'
        r"\b(?:at|timestamp|timecode)\s+\[?\d{1,2}:\d{2}(?::\d{2})?\]?\b",
        # Line-start or hyphen-separated timestamps: '00:05 - ' or '12:34: ' or '04:15 '
        r"^\s*(?:at\s+|timestamp\s*:?\s*)?\d{1,2}:\d{2}(?::\d{2})?\s*[-–:]?\s*",
        # Standalone MM:SS bounded by whitespace or punctuation
        r"(?<=\s)\d{1,2}:\d{2}(?=\s|[-–:,\.]|$)",
        r"^\s*\d{1,2}:\d{2}(?=\s|[-–:,\.]|$)",
        # SRT line index numbers
        r"^\s*\d+\s*$",
    ]

    # Speaker labels e.g. "Professor Smith:", "Speaker 1:", "Lecturer [01:23]:"
    SPEAKER_PATTERN = r"^\s*(?:[A-Z][A-Za-z\.\s]{1,25}|Speaker\s*\d+|Prof(?:essor)?\.?\s*[A-Z][a-z]+|Instructor|Student\s*\d?)\s*(?:\[\d{1,2}:\d{2}(?::\d{2})?\])?\s*:\s*"

    @classmethod
    def clean_timestamps(cls, text: str) -> str:
        """
        Removes all time codes, timestamps, and residual time markers from text.
        """
        if not text:
            return ""

        res = text
        for pattern in cls.TIMESTAMP_PATTERNS:
            res = re.sub(pattern, " ", res, flags=re.MULTILINE | re.IGNORECASE)

        # Remove dangling prepositions before punctuation (e.g., 'discussed at ,' -> 'discussed,')
        res = re.sub(r"\b(?:at|on|in|around)\s*([,.:;?!])", r"\1", res, flags=re.IGNORECASE)

        # Clean punctuation and spacing
        res = re.sub(r"[ \t]+", " ", res)
        res = re.sub(r"\s+([,.:;?!])", r"\1", res)
        res = re.sub(r"^\s*[,;:\-\.]\s*", "", res)
        res = res.strip()
        if res and res[0].islower():
            res = res[0].upper() + res[1:]
        return res

    @classmethod
    def clean(cls, text: str, remove_fillers: bool = True, remove_timestamps: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        Cleans the input transcript and returns the cleaned text along with statistics.

        Args:
            text: Raw input transcript text
            remove_fillers: Whether to remove filler words and verbal pauses
            remove_timestamps: Whether to strip timestamps and subtitle indices

        Returns:
            Tuple of (cleaned_text, stats_dict)
        """
        if not text or not text.strip():
            return "", {
                "original_words": 0,
                "cleaned_words": 0,
                "reduction_percentage": 0.0,
                "fillers_removed": 0
            }

        original_text = text
        original_words = len(text.split())
        fillers_removed_count = 0

        # Step 1: Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Step 2: Remove timestamps and speaker labels if requested
        if remove_timestamps:
            for pattern in cls.TIMESTAMP_PATTERNS:
                text = re.sub(pattern, " ", text, flags=re.MULTILINE | re.IGNORECASE)

            # Remove speaker labels line-by-line
            lines = text.split("\n")
            cleaned_lines = []
            for line in lines:
                cleaned_line = re.sub(cls.SPEAKER_PATTERN, "", line, flags=re.IGNORECASE)
                cleaned_lines.append(cleaned_line)
            text = "\n".join(cleaned_lines)

            # Remove dangling prepositions before punctuation
            text = re.sub(r"\b(?:at|on|in|around)\s*([,.:;?!])", r"\1", text, flags=re.IGNORECASE)

        # Step 3: Remove filler phrases and words if requested
        if remove_fillers:
            for phrase_pat in cls.FILLER_PHRASES:
                matches = len(re.findall(phrase_pat, text, flags=re.IGNORECASE))
                fillers_removed_count += matches
                text = re.sub(phrase_pat, "", text, flags=re.IGNORECASE)

            for word_pat in cls.FILLER_WORDS:
                matches = len(re.findall(word_pat, text, flags=re.IGNORECASE))
                fillers_removed_count += matches
                text = re.sub(word_pat, "", text, flags=re.IGNORECASE)

            # Clean standalone conversational interjections at sentence starts
            interjections = [
                r"(?<=[\.\?\!]\s)(?:Like|Basically|Literally|Actually|Honestly|So yeah|I mean),\s*",
                r"^(?:Like|Basically|Literally|Actually|Honestly|So yeah|I mean),\s*"
            ]
            for inj in interjections:
                text = re.sub(inj, "", text, flags=re.MULTILINE | re.IGNORECASE)

        # Step 4: Remove stuttering / duplicate consecutive identical words (e.g., "the the", "is is")
        text = re.sub(r"\b([a-zA-Z]{2,})\s+\1\b", r"\1", text, flags=re.IGNORECASE)
        text = re.sub(r"\b([a-zA-Z]{2,})\s+\1\b", r"\1", text, flags=re.IGNORECASE)

        # Step 5: Clean punctuation artifacts (e.g., double commas, hanging commas before periods)
        text = re.sub(r",\s*,+", ", ", text)
        text = re.sub(r"\s+([,.:;?!])", r"\1", text)
        text = re.sub(r",\s*([.?!])", r"\1", text)
        text = re.sub(r"\.{2,}", "...", text)  # normalize ellipsis

        # Step 6: Normalize whitespace while preserving paragraphs
        paragraphs = text.split("\n\n")
        cleaned_paragraphs = []
        for p in paragraphs:
            # Collapse multiple spaces into single space
            clean_p = re.sub(r"[ \t]+", " ", p).strip()
            # Collapse single linebreaks within a paragraph into spaces
            clean_p = re.sub(r"\n", " ", clean_p).strip()
            if clean_p:
                # Capitalize first letter of paragraph if needed
                if len(clean_p) > 0 and clean_p[0].islower():
                    clean_p = clean_p[0].upper() + clean_p[1:]
                cleaned_paragraphs.append(clean_p)

        cleaned_text = "\n\n".join(cleaned_paragraphs)
        cleaned_words = len(cleaned_text.split())

        reduction = 0.0
        if original_words > 0:
            reduction = round(((original_words - cleaned_words) / original_words) * 100, 1)

        stats = {
            "original_words": original_words,
            "cleaned_words": cleaned_words,
            "reduction_percentage": max(0.0, reduction),
            "fillers_removed": fillers_removed_count
        }

        return cleaned_text, stats
