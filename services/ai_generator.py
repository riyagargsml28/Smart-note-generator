"""
AI Notes Generator Service.
Transforms raw or cleaned lecture transcripts into structured academic study notes
conforming to the required JSON schema, using OpenAI LLM or an intelligent heuristic engine.
"""

import json
import os
import re
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator


# ==========================================
# Pydantic Schemas for Structured AI Notes
# ==========================================

class Definition(BaseModel):
    term: str = Field(description="Name of the technical or academic term")
    meaning: str = Field(description="Clear explanation or definition based strictly on the lecture")


class Section(BaseModel):
    heading: str = Field(description="Subtopic heading")
    key_points: List[str] = Field(default_factory=list, description="Core concepts and takeaways")
    definitions: List[Definition] = Field(default_factory=list, description="Key definitions in this section")
    examples: List[str] = Field(default_factory=list, description="Real-world examples, analogies, or case studies")


class RevisionQuestion(BaseModel):
    question: str = Field(description="Revision or test question based on the lecture")
    answer: str = Field(description="Detailed answer derived from the lecture content")


class MCQ(BaseModel):
    question: str = Field(description="Multiple-choice question")
    options: List[str] = Field(description="List of 4 distinct choices, e.g. ['A) ...', 'B) ...']")
    correct_answer: str = Field(description="The correct choice matching one of the options")
    explanation: str = Field(description="Brief explanation of why this answer is correct")


class LectureNotes(BaseModel):
    title: str = Field(description="Concise, descriptive lecture title")
    overview: str = Field(description="Executive overview of what was covered")
    sections: List[Section] = Field(default_factory=list, description="Main topics and subheadings")
    formulas: List[Union[Dict[str, str], str]] = Field(default_factory=list, description="Formulas, equations, or laws")
    glossary: List[Union[Dict[str, str], str]] = Field(default_factory=list, description="Alphabetized or categorized glossary")
    summary: str = Field(description="Comprehensive concluding summary")
    revision_questions: List[RevisionQuestion] = Field(default_factory=list, description="Self-study revision Q&A")
    mcqs: List[MCQ] = Field(default_factory=list, description="Multiple-choice quiz questions")

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, v):
        if not v:
            # Fallback section if none returned
            return [Section(heading="Lecture Notes", key_points=["Notes generated from lecture transcript."])]
        return v


# ==========================================
# AI Generator Implementation
# ==========================================

class AINotesGenerator:
    """Orchestrates structured note generation with LLM and heuristic fallbacks."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
        self.model = model
        self.client = None

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] OpenAI client initialization failed: {e}")
                self.client = None

    def generate_notes(
        self,
        transcript: str,
        subject: str = "General",
        detail_level: str = "medium",
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates structured notes from transcript content.

        Args:
            transcript: Cleaned lecture transcript text.
            subject: Academic subject (e.g., Computer Science, Physics).
            detail_level: 'short', 'medium', or 'detailed'.
            segments: Optional pre-computed topic segments.

        Returns:
            Dictionary matching the required JSON schema with generation metadata.
        """
        if not transcript or not transcript.strip():
            raise ValueError("Transcript text cannot be empty.")

        # Attempt OpenAI generation if client is available
        if self.client:
            try:
                result = self._generate_with_openai(transcript, subject, detail_level)
                result["_meta"] = {
                    "engine": "OpenAI " + self.model,
                    "detail_level": detail_level,
                    "subject": subject
                }
                return result
            except Exception as e:
                print(f"[Notice] OpenAI API generation failed ({e}). Using intelligent heuristic engine.")

        # Heuristic fallback engine (guarantees a working response without API keys)
        result = self._generate_with_heuristics(transcript, subject, detail_level, segments)
        result["_meta"] = {
            "engine": "Academic Heuristic Engine (Offline / Local Mode)",
            "detail_level": detail_level,
            "subject": subject,
            "notice": "Generated using built-in semantic analysis. To use GPT-4o, add your OPENAI_API_KEY to .env."
        }
        return result

    def _generate_with_openai(self, transcript: str, subject: str, detail_level: str) -> Dict[str, Any]:
        """Calls OpenAI Chat Completion to generate strictly structured JSON notes."""
        depth_instructions = {
            "short": "Provide a quick, concise review. 2-3 key sections, 3 revision Q&As, and 3 MCQs.",
            "medium": "Provide balanced, thorough lecture study notes. 3-5 sections with clear key points, definitions, examples, 5 revision Q&As, and 5 MCQs.",
            "detailed": "Provide comprehensive, in-depth academic study notes. 5-8 detailed sections with exhaustive key points, clear definitions, illustrative examples, equations/formulas, full glossary, 8 revision Q&As, and 8 MCQs."
        }

        system_prompt = (
            "You are a distinguished university professor and academic note-taking expert. "
            "Your task is to convert raw lecture transcripts into well-organized, accurate, and easy-to-understand study notes.\n\n"
            "STRICT RULES:\n"
            "1. Base all facts, definitions, and claims solely on the provided transcript. Do NOT fabricate or invent facts.\n"
            "2. If formulas or equations appear in the lecture, format them cleanly in the 'formulas' array.\n"
            "3. Return ONLY valid JSON adhering strictly to the requested schema. No conversational filler or markdown fences outside the JSON."
        )

        user_prompt = f"""
Subject: {subject}
Desired Detail Level: {detail_level.upper()} ({depth_instructions.get(detail_level, '')})

TRANSCRIPT CONTENT:
\"\"\"
{transcript[:25000]}
\"\"\"

Produce the notes as a single JSON object with EXACTLY this structure:
{{
  "title": "A clear, descriptive lecture title",
  "overview": "Short 2-3 sentence overview of the lecture purpose and scope",
  "sections": [
    {{
      "heading": "Topic heading",
      "key_points": ["Point 1 based on lecture", "Point 2 based on lecture"],
      "definitions": [
        {{
          "term": "Technical term",
          "meaning": "Meaning based on the transcript"
        }}
      ],
      "examples": ["Concrete example mentioned in the lecture"]
    }}
  ],
  "formulas": [
    {{
      "name": "Name of formula or law (if any)",
      "formula": "e.g. E = mc^2 or equation",
      "explanation": "What each variable represents"
    }}
  ],
  "glossary": [
    {{
      "term": "Term name",
      "meaning": "Clear definition"
    }}
  ],
  "summary": "Cohesive concluding summary of the lecture",
  "revision_questions": [
    {{
      "question": "Conceptual or factual question",
      "answer": "Accurate answer grounded in the lecture"
    }}
  ],
  "mcqs": [
    {{
      "question": "Multiple choice question testing a key concept",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "A) Option 1",
      "explanation": "Why this option is correct based on the lecture"
    }}
  ]
}}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        raw_json_str = response.choices[0].message.content
        data = json.loads(raw_json_str)

        # Validate with Pydantic
        validated = LectureNotes.model_validate(data)
        return validated.model_dump()

    def _generate_with_heuristics(
        self,
        transcript: str,
        subject: str,
        detail_level: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Intelligent rule-based analyzer that constructs rich academic notes
        even when offline or running without third-party API credentials.
        """
        paragraphs = [p.strip() for p in transcript.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [transcript.strip()]

        # 1. Infer Title
        first_p = paragraphs[0]
        title_match = re.search(r"(?:today we['’]?re going to (?:talk about|discuss|cover)|welcome to|this lecture is about)\s+([^.,;\n]+)", first_p, re.IGNORECASE)
        if title_match:
            raw_title = title_match.group(1).strip()
            title = f"{subject}: {raw_title.title()}"
        else:
            first_sent = first_p.split(".")[0].strip()
            words = first_sent.split()[:6]
            title = f"{subject} Lecture: " + " ".join(words).rstrip(",;:")

        # 2. Extract Overview
        overview = first_p
        if len(overview.split()) > 60:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", first_p) if s.strip()]
            overview = " ".join(sentences[:2]) if len(sentences) >= 2 else sentences[0]

        # 3. Extract Definitions
        # Look for patterns like "X is defined as Y", "X refers to Y", "X is a Y that"
        definitions_found: List[Dict[str, str]] = []
        definition_patterns = [
            r"\b([A-Z][a-zA-Z\s]{2,25})\s+is\s+(?:defined\s+as|known\s+as|called|referred\s+to\s+as)\s+([^.!?]+[.!?])",
            r"\b([A-Z][a-zA-Z\s]{2,25})\s+refers\s+to\s+([^.!?]+[.!?])",
            r"\b([A-Za-z\s]{3,25})\s+is\s+(?:essentially|basically|fundamentally)?\s*(?:a|an|the)\s+([^.!?]+[.!?])"
        ]

        full_text = " ".join(paragraphs)
        for pat in definition_patterns:
            for match in re.finditer(pat, full_text):
                term = match.group(1).strip().capitalize()
                meaning = match.group(2).strip()
                if len(term.split()) <= 4 and not any(d["term"].lower() == term.lower() for d in definitions_found):
                    definitions_found.append({"term": term, "meaning": meaning})
                if len(definitions_found) >= 10:
                    break

        # 4. Extract Formulas / Equations
        # Look for math formulas e.g. "E = mc^2", "O(n log n)", equations with =, +, -, *, /
        formulas_found: List[Dict[str, str]] = []
        formula_patterns = [
            r"([A-Za-z0-9_\s]{2,20})\s*=\s*([A-Za-z0-9_\+\-\*\/\^\(\)\s\.\\]+)",
            r"(?:Big[- ]O|Time complexity|Space complexity)\s*(?:is|of)?\s*(O\([^\)]+\))",
        ]
        for pat in formula_patterns:
            for match in re.finditer(pat, full_text):
                matched_str = match.group(0).strip()
                if any(sym in matched_str for sym in ("=", "O(", "^", "/")):
                    if len(matched_str) < 60 and not any(f.get("formula") == matched_str for f in formulas_found):
                        formulas_found.append({
                            "name": "Mathematical / Algorithmic Relation",
                            "formula": matched_str,
                            "explanation": f"Expression extracted directly from the lecture: '{matched_str}'"
                        })
                if len(formulas_found) >= 5:
                    break

        # 5. Build Sections
        sections: List[Dict[str, Any]] = []
        num_sections = 3 if detail_level == "short" else (5 if detail_level == "medium" else 7)
        paras_per_section = max(1, len(paragraphs) // max(1, num_sections))

        for idx in range(0, min(len(paragraphs), num_sections * paras_per_section), paras_per_section):
            chunk = paragraphs[idx:idx + paras_per_section]
            if not chunk:
                continue

            first_sentence = chunk[0].split(".")[0].strip()
            heading_words = [w for w in first_sentence.split() if w.lower() not in {"now", "so", "today", "well", "let's"}]
            heading = " ".join(heading_words[:6]).title() or f"Key Topic {len(sections) + 1}"

            # Key points from the sentences in the chunk
            key_points = []
            examples = []
            sec_definitions = []

            for p in chunk:
                sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if len(s.strip()) > 15]
                for s in sents:
                    if re.search(r"\b(?:for example|for instance|such as|consider the case|e\.g\.)\b", s, re.IGNORECASE):
                        if len(examples) < 2:
                            examples.append(s)
                    elif len(key_points) < 4 and len(s.split()) >= 6:
                        key_points.append(s)

            # Assign matching definitions to section
            for d in definitions_found:
                if d["term"].lower() in " ".join(chunk).lower() and len(sec_definitions) < 2:
                    sec_definitions.append(d)

            sections.append({
                "heading": heading,
                "key_points": key_points if key_points else ["Covers foundational concepts discussed in this part of the lecture."],
                "definitions": sec_definitions,
                "examples": examples
            })

            if len(sections) >= num_sections:
                break

        if not sections:
            sections.append({
                "heading": "Core Lecture Content",
                "key_points": ["Key lecture material reviewed and synthesized."],
                "definitions": definitions_found[:2],
                "examples": []
            })

        # 6. Summary
        last_p = paragraphs[-1]
        summary = last_p if len(last_p.split()) < 80 else " ".join(re.split(r"(?<=[.!?])\s+", last_p)[:3])
        if not summary or len(summary.split()) < 15:
            summary = f"This lecture provided a comprehensive examination of {subject.lower()} fundamentals, highlighting core principles, real-world examples, and academic frameworks."

        # 7. Glossary
        glossary = []
        for d in definitions_found:
            glossary.append({"term": d["term"], "meaning": d["meaning"]})

        # 8. Revision Questions & MCQs
        revision_count = 3 if detail_level == "short" else (5 if detail_level == "medium" else 7)
        revision_questions = []
        mcqs = []

        all_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_text) if len(s.split()) >= 8]

        for i in range(min(revision_count, len(all_sentences))):
            target_sent = all_sentences[i * max(1, len(all_sentences) // max(1, revision_count))]
            words = target_sent.split()
            first_clause = " ".join(words[:5])

            question = f"According to the lecture, what is the significance of: '{first_clause}...'?"
            answer = target_sent

            revision_questions.append({
                "question": question,
                "answer": answer
            })

            # Create an MCQ
            correct_choice = f"A) {target_sent[:70]}..." if len(target_sent) > 70 else f"A) {target_sent}"
            mcqs.append({
                "question": f"Which statement best reflects the discussion regarding {subject} in this lecture?",
                "options": [
                    correct_choice,
                    "B) It is completely unrelated to the core principles presented in the course.",
                    "C) The concept was proven obsolete and replaced entirely by manual methods.",
                    "D) The lecture demonstrated that no practical applications currently exist."
                ],
                "correct_answer": correct_choice,
                "explanation": f"As highlighted directly in the lecture transcript: '{target_sent}'"
            })

        result = {
            "title": title,
            "overview": overview,
            "sections": sections,
            "formulas": formulas_found,
            "glossary": glossary,
            "summary": summary,
            "revision_questions": revision_questions,
            "mcqs": mcqs
        }

        # Validate with Pydantic
        validated = LectureNotes.model_validate(result)
        return validated.model_dump()
