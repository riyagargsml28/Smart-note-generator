"""
AI Notes Generator Service.
Transforms raw or cleaned lecture transcripts into structured academic study notes
conforming to the required JSON schema, using Google Gemini 3.5 Flash or an intelligent heuristic engine.
Supports English, Hindi (हिंदी), and Bilingual (English + Hindi) output modes.
Guarantees that all timestamps are completely removed from generated notes, question answers,
and practice quizzes.
"""

import json
import os
import re
import time
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


class FormulaItem(BaseModel):
    name: str = Field(default="Formula", description="Name of the formula, law, or equation")
    formula: str = Field(default="", description="Mathematical representation or formula")
    explanation: str = Field(default="", description="Explanation of what variables and terms represent")


class GlossaryItem(BaseModel):
    term: str = Field(description="Name of academic or technical term")
    meaning: str = Field(description="Clear explanation or definition")


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
    formulas: List[FormulaItem] = Field(default_factory=list, description="Formulas, equations, or laws")
    glossary: List[GlossaryItem] = Field(default_factory=list, description="Alphabetized or categorized glossary")
    summary: str = Field(description="Comprehensive concluding summary")
    revision_questions: List[RevisionQuestion] = Field(default_factory=list, description="Self-study revision Q&A")
    mcqs: List[MCQ] = Field(default_factory=list, description="Multiple-choice quiz questions")

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, v):
        if not v:
            return [Section(heading="Lecture Notes", key_points=["Notes generated from lecture transcript."])]
        return v

    @field_validator("formulas", mode="before")
    @classmethod
    def validate_formulas(cls, v):
        if not v:
            return []
        res = []
        for item in v:
            if isinstance(item, str):
                res.append(FormulaItem(name="Formula", formula=item, explanation=""))
            elif isinstance(item, dict):
                res.append(FormulaItem(
                    name=item.get("name", "Formula"),
                    formula=item.get("formula", ""),
                    explanation=item.get("explanation", "")
                ))
            elif isinstance(item, FormulaItem):
                res.append(item)
        return res

    @field_validator("glossary", mode="before")
    @classmethod
    def validate_glossary(cls, v):
        if not v:
            return []
        res = []
        for item in v:
            if isinstance(item, str):
                parts = item.split(":", 1)
                term = parts[0].strip()
                meaning = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                res.append(GlossaryItem(term=term, meaning=meaning))
            elif isinstance(item, dict):
                res.append(GlossaryItem(
                    term=item.get("term", ""),
                    meaning=item.get("meaning", item.get("definition", ""))
                ))
            elif isinstance(item, GlossaryItem):
                res.append(item)
        return res


# ==========================================
# AI Generator Implementation
# ==========================================

class AINotesGenerator:
    """Orchestrates structured note generation with Gemini 3.5 Flash and heuristic fallbacks for English, Hindi, and Bilingual modes."""

    # Vocabulary mapping for academic concepts in Hindi
    HINDI_CONCEPT_MAP = {
        "computer science": "कंप्यूटर साइंस (Computer Science)",
        "physics": "भौतिक विज्ञान (Physics)",
        "biology": "जीव विज्ञान (Biology)",
        "chemistry": "रसायन विज्ञान (Chemistry)",
        "mathematics": "गणित (Mathematics)",
        "virtual memory": "वर्चुअल मेमोरी (Virtual Memory)",
        "paging": "पेजिंग (Paging)",
        "page table": "पेज टेबल (Page Table)",
        "page fault": "पेज फॉल्ट (Page Fault)",
        "mmu": "एमएमयू (Memory Management Unit)",
        "effective access time": "प्रभावी पहुँच समय (Effective Access Time)",
        "fifo": "फीफो - फर्स्ट-इन फर्स्ट-आउट (FIFO)",
        "lru": "एलआरयू - लीस्ट रिसेंटली यूज़्ड (LRU)",
        "belady's anomaly": "बेलाडी की विसंगति (Belady's Anomaly)",
        "quantum mechanics": "क्वांटम यांत्रिकी (Quantum Mechanics)",
        "wave-particle duality": "तरंग-कण द्वैतता (Wave-Particle Duality)",
        "uncertainty principle": "अनिश्चितता का सिद्धांत (Uncertainty Principle)",
        "quantum tunneling": "क्वांटम टनलिंग (Quantum Tunneling)",
        "planck": "प्लांक नियतांक (Planck's Constant)",
        "photon": "फोटॉन (Photon)",
        "dna replication": "डीएनए प्रतिकृति (DNA Replication)",
        "central dogma": "सेंट्रल डोग्मा (Central Dogma)",
        "helicase": "हेलीकेज़ एंजाइम (Helicase)",
        "dna polymerase": "डीएनए पॉलिमरेज़ (DNA Polymerase)",
        "transcription": "अनुलेखन (Transcription)",
        "translation": "रूपांतरण / अनुवाद (Translation)",
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash"):
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY", "")
            or os.environ.get("OPENAI_API_KEY", "")
        ).strip()
        self.model = model or "gemini-3.5-flash"
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] Google GenAI client initialization failed: {e}")
                self.client = None

    @classmethod
    def strip_timestamps_from_text(cls, text: str) -> str:
        """
        Thoroughly removes time stamps, time codes, and speaker prefixes from text,
        while preserving MCQ option prefixes (e.g. 'A) ') and clean punctuation.
        """
        if not text:
            return ""

        opt_prefix = ""
        opt_match = re.match(r"^([A-Da-d][\)\.]|\d+[\)\.])\s*", text)
        if opt_match:
            opt_prefix = opt_match.group(0)
            text = text[len(opt_prefix):]

        patterns = [
            r"\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*(?:-->|->|–|-)\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?",
            r"\b(?:at|on|in|around|timestamp|timecode)\s*\[\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\]",
            r"\b(?:at|on|in|around|timestamp|timecode)\s*\(\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\)",
            r"\[\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\]",
            r"\(\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\)",
            r"\<\s*\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?\s*\>",
            r"\b\d{1,2}:\d{2}:\d{2}(?:[\.,]\d{1,3})?\b",
            r"\b(?:at|timestamp|timecode)\s+\[?\d{1,2}:\d{2}(?::\d{2})?\]?\b",
            r"^\s*(?:at\s+|timestamp\s*:?\s*)?\d{1,2}:\d{2}(?::\d{2})?\s*[-–:]?\s*",
            r"(?<=\s)\d{1,2}:\d{2}(?=\s|[-–:,\.]|$)",
            r"^\s*\d{1,2}:\d{2}(?=\s|[-–:,\.]|$)",
        ]

        res = text
        for pat in patterns:
            res = re.sub(pat, " ", res, flags=re.MULTILINE | re.IGNORECASE)

        res = re.sub(
            r"^\s*(?:[A-Z][A-Za-z\.\s]{1,25}|Speaker\s*\d+|Prof(?:essor)?\.?\s*[A-Z][a-z]+|Instructor|Student\s*\d?)\s*:\s*",
            "",
            res,
            flags=re.IGNORECASE
        )
        res = re.sub(r"\b(?:at|on|in|around)\s*([,.:;?!])", r"\1", res, flags=re.IGNORECASE)
        res = re.sub(r"[ \t]+", " ", res)
        res = re.sub(r"\s+([,.:;?!])", r"\1", res)
        res = re.sub(r"^\s*[,;:\-\.]\s*", "", res)
        res = res.strip()

        if res and res[0].islower():
            res = res[0].upper() + res[1:]

        return f"{opt_prefix}{res}".strip()

    @classmethod
    def sanitize_notes_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitizes all fields of the study notes dictionary to guarantee
        that no timestamps appear anywhere in the output.
        """
        if not isinstance(data, dict):
            return data

        data["title"] = cls.strip_timestamps_from_text(data.get("title", ""))
        data["overview"] = cls.strip_timestamps_from_text(data.get("overview", ""))
        data["summary"] = cls.strip_timestamps_from_text(data.get("summary", ""))

        cleaned_sections = []
        for sec in data.get("sections", []):
            if isinstance(sec, dict):
                heading = cls.strip_timestamps_from_text(sec.get("heading", ""))
                key_points = [
                    cls.strip_timestamps_from_text(kp)
                    for kp in sec.get("key_points", [])
                    if cls.strip_timestamps_from_text(kp)
                ]

                definitions = []
                for d in sec.get("definitions", []):
                    if isinstance(d, dict):
                        d_term = cls.strip_timestamps_from_text(d.get("term", ""))
                        d_meaning = cls.strip_timestamps_from_text(d.get("meaning", ""))
                        if d_term:
                            definitions.append({"term": d_term, "meaning": d_meaning})

                examples = [
                    cls.strip_timestamps_from_text(ex)
                    for ex in sec.get("examples", [])
                    if cls.strip_timestamps_from_text(ex)
                ]

                cleaned_sections.append({
                    "heading": heading or "Key Concept",
                    "key_points": key_points if key_points else ["Key point based on lecture."],
                    "definitions": definitions,
                    "examples": examples
                })
        data["sections"] = cleaned_sections

        cleaned_formulas = []
        for f in data.get("formulas", []):
            if isinstance(f, dict):
                cleaned_formulas.append({
                    "name": cls.strip_timestamps_from_text(f.get("name", "Formula")),
                    "formula": cls.strip_timestamps_from_text(f.get("formula", "")),
                    "explanation": cls.strip_timestamps_from_text(f.get("explanation", ""))
                })
            elif isinstance(f, str):
                cf = cls.strip_timestamps_from_text(f)
                if cf:
                    cleaned_formulas.append(cf)
        data["formulas"] = cleaned_formulas

        cleaned_glossary = []
        for g in data.get("glossary", []):
            if isinstance(g, dict):
                g_term = cls.strip_timestamps_from_text(g.get("term", ""))
                g_meaning = cls.strip_timestamps_from_text(g.get("meaning", g.get("definition", "")))
                if g_term:
                    cleaned_glossary.append({"term": g_term, "meaning": g_meaning})
            elif isinstance(g, str):
                cg = cls.strip_timestamps_from_text(g)
                if cg:
                    cleaned_glossary.append(cg)
        data["glossary"] = cleaned_glossary

        cleaned_revision = []
        for rq in data.get("revision_questions", []):
            if isinstance(rq, dict):
                q = cls.strip_timestamps_from_text(rq.get("question", ""))
                a = cls.strip_timestamps_from_text(rq.get("answer", ""))
                if q:
                    cleaned_revision.append({"question": q, "answer": a})
        data["revision_questions"] = cleaned_revision

        cleaned_mcqs = []
        for mcq in data.get("mcqs", []):
            if isinstance(mcq, dict):
                q = cls.strip_timestamps_from_text(mcq.get("question", ""))
                opts = [cls.strip_timestamps_from_text(opt) for opt in mcq.get("options", [])]
                ans = cls.strip_timestamps_from_text(mcq.get("correct_answer", ""))
                exp = cls.strip_timestamps_from_text(mcq.get("explanation", ""))
                if q and opts:
                    cleaned_mcqs.append({
                        "question": q,
                        "options": opts,
                        "correct_answer": ans,
                        "explanation": exp
                    })
        data["mcqs"] = cleaned_mcqs

        return data

    def generate_notes(
        self,
        transcript: str,
        subject: str = "General",
        detail_level: str = "medium",
        language: str = "english",
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates structured notes from transcript content in English, Hindi, or Both (Bilingual).

        Args:
            transcript: Cleaned lecture transcript text.
            subject: Academic subject (e.g., Computer Science, Physics).
            detail_level: 'short', 'medium', or 'detailed'.
            language: 'english', 'hindi', or 'both' (bilingual).
            segments: Optional pre-computed topic segments.

        Returns:
            Dictionary matching the required JSON schema with generation metadata.
        """
        if not transcript or not transcript.strip():
            raise ValueError("Transcript text cannot be empty.")

        language = (language or "english").lower().strip()
        if language not in ("english", "hindi", "both", "bilingual"):
            language = "english"

        clean_input = self.strip_timestamps_from_text(transcript)

        # Attempt Gemini 3.5 Flash generation if client is available
        if self.client:
            try:
                result = self._generate_with_gemini(clean_input, subject, detail_level, language)
                result = self.sanitize_notes_dict(result)
                result["_meta"] = {
                    "engine": "Google Gemini (" + self.model + ")",
                    "detail_level": detail_level,
                    "subject": subject,
                    "language": language
                }
                return result
            except Exception as e:
                print(f"[Notice] Gemini API generation failed ({e}). Using intelligent heuristic engine.")

        # Heuristic fallback engine (supports English, Hindi, and Bilingual modes)
        result = self._generate_with_heuristics(clean_input, subject, detail_level, language, segments)
        result = self.sanitize_notes_dict(result)
        result["_meta"] = {
            "engine": "Academic Heuristic Engine (Offline / Local Mode)",
            "detail_level": detail_level,
            "subject": subject,
            "language": language,
            "notice": "Generated using built-in semantic analysis. Add GEMINI_API_KEY in .env for live Gemini 3.5 Flash generation."
        }
        return result

    def _generate_with_gemini(self, transcript: str, subject: str, detail_level: str, language: str) -> Dict[str, Any]:
        """Calls Google Gemini 3.5 Flash to generate strictly structured JSON notes in requested language."""
        from google.genai import types

        depth_instructions = {
            "short": "Provide a quick, concise review. 2-3 key sections, 3 revision Q&As, and 3 MCQs.",
            "medium": "Provide balanced, thorough lecture study notes. 3-5 sections with clear key points, definitions, examples, 5 revision Q&As, and 5 MCQs.",
            "detailed": "Provide comprehensive, in-depth academic study notes. 5-8 detailed sections with exhaustive key points, clear definitions, illustrative examples, equations/formulas, full glossary, 8 revision Q&As, and 8 MCQs."
        }

        lang_instructions = {
            "english": (
                "OUTPUT LANGUAGE: ENGLISH.\n"
                "Generate all study notes, definitions, revision questions, and MCQs in standard, academic English."
            ),
            "hindi": (
                "OUTPUT LANGUAGE: HINDI (हिंदी - देवनागरी लिपि).\n"
                "Generate all study notes strictly in clear, accessible, and grammatically correct Hindi using Devanagari script.\n"
                "All titles, overviews, section headings, key points, definitions, examples, formulas explanations, glossary terms, summary, revision questions, and MCQs MUST be written in Hindi.\n"
                "Technical terms may include their English name in parentheses, e.g. 'वर्चुअल मेमोरी (Virtual Memory)'."
            ),
            "both": (
                "OUTPUT LANGUAGE: BILINGUAL (English + Hindi / दोनों भाषाएँ).\n"
                "Provide comprehensive bilingual study notes combining both English and Hindi:\n"
                "1. Title: Bilingual format (e.g. 'Virtual Memory and Paging / वर्चुअल मेमोरी और पेजिंग')\n"
                "2. Overview: English overview followed by its Hindi explanation (e.g. 'English text... / [हिन्दी]: ...')\n"
                "3. Sections: Headings in English with Hindi translation. Key points with English bullet and Hindi translation/explanation.\n"
                "4. Definitions: Technical terms with both English and Hindi definitions (e.g. 'Page Fault (पेज फॉल्ट)').\n"
                "5. Formulas: Formula with bilingual explanation in English and Hindi.\n"
                "6. Glossary: Terms with definitions in both languages.\n"
                "7. Revision Questions: Questions and answers in BOTH English and Hindi so students can revise in either language.\n"
                "8. Practice Quizzes (MCQs): Questions and options in both English and Hindi with bilingual explanations!"
            )
        }
        if language == "bilingual":
            language = "both"

        chosen_lang_guide = lang_instructions.get(language, lang_instructions["english"])

        system_prompt = (
            "You are a distinguished university professor and academic note-taking expert fluent in both Hindi and English.\n"
            f"{chosen_lang_guide}\n\n"
            "STRICT RULES:\n"
            "1. Base all facts, definitions, and claims solely on the provided transcript. Do NOT fabricate or invent facts.\n"
            "2. If formulas or equations appear in the lecture, format them cleanly in the 'formulas' array.\n"
            "3. Return ONLY valid JSON adhering strictly to the requested schema. No conversational filler or markdown fences outside the JSON.\n"
            "4. ABSOLUTE TIMESTAMP REMOVAL: You must NEVER include timestamps (e.g. [00:12:45], (12:34), 00:05), time offsets, or time codes anywhere in the generated notes, section headings, key points, definitions, examples, formulas, glossary, summary, revision questions, answers, or multiple-choice questions (MCQs). Filter out all timestamps completely."
        )

        user_prompt = f"""
Subject: {subject}
Desired Detail Level: {detail_level.upper()} ({depth_instructions.get(detail_level, '')})
Language Mode: {language.upper()}

TRANSCRIPT CONTENT:
\"\"\"
{transcript[:30000]}
\"\"\"

CRITICAL REQUIREMENT: Do NOT include any timestamps (such as [00:01:23] or 12:45) in any field of the output—strip them out completely from all titles, overviews, section headings, key points, definitions, examples, summaries, revision questions, answers, and MCQs.
Generate the complete structured notes adhering strictly to the required schema.
"""

        last_err = None
        for attempt in range(4):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=LectureNotes,
                        temperature=0.2
                    )
                )
                raw_json_str = response.text or "{}"
                data = json.loads(raw_json_str)
                sanitized = self.sanitize_notes_dict(data)
                validated = LectureNotes.model_validate(sanitized)
                return validated.model_dump()
            except Exception as e:
                last_err = e
                err_str = str(e)
                if attempt < 3 and ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str):
                    time.sleep(2 * (attempt + 1))
                    continue
                raise last_err

    def _generate_with_heuristics(
        self,
        transcript: str,
        subject: str,
        detail_level: str,
        language: str = "english",
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Intelligent rule-based analyzer that constructs rich academic notes in English, Hindi,
        or Both (Bilingual), completely stripped of timestamps.
        """
        cleaned_source = self.strip_timestamps_from_text(transcript)
        paragraphs = [p.strip() for p in cleaned_source.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [cleaned_source.strip()]

        full_text = " ".join(paragraphs)

        is_hindi = language == "hindi"
        is_both = language in ("both", "bilingual")

        # 1. Infer Title
        raw_core_title = ""
        for p in paragraphs[:3]:
            title_match = re.search(
                r"(?:today we['’]?re going to (?:talk about|discuss|cover|dive into)|welcome to|this lecture is about|we will explore)\s+([^.,;\n]+)",
                p,
                re.IGNORECASE
            )
            if title_match:
                raw_core_title = self.strip_timestamps_from_text(title_match.group(1).strip()).title()
                break

        if not raw_core_title:
            for p in paragraphs:
                sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if len(s.strip()) > 10]
                for s in sents:
                    clean_s = self.strip_timestamps_from_text(s)
                    if not re.match(r"^(?:Good morning|Hello|Welcome|Hi everyone)", clean_s, re.IGNORECASE):
                        words = clean_s.split()[:5]
                        raw_core_title = " ".join(words).rstrip(",;:")
                        break
                if raw_core_title:
                    break

        if not raw_core_title:
            raw_core_title = f"{subject} Core Concepts"

        # Construct language-specific Title
        hindi_subject = self.HINDI_CONCEPT_MAP.get(subject.lower(), f"{subject} (अध्ययन)")
        hindi_core_title = self._translate_phrase_to_hindi(raw_core_title)

        if is_hindi:
            title = f"{hindi_subject}: {hindi_core_title}"
        elif is_both:
            title = f"{subject}: {raw_core_title} / {hindi_subject}: {hindi_core_title}"
        else:
            title = f"{subject}: {raw_core_title}"

        title = self.strip_timestamps_from_text(title)

        # 2. Extract Overview
        overview_en = ""
        for p in paragraphs[:2]:
            clean_p = self.strip_timestamps_from_text(p)
            if len(clean_p.split()) > 15:
                overview_en = clean_p
                break
        if not overview_en and paragraphs:
            overview_en = self.strip_timestamps_from_text(paragraphs[0])

        if len(overview_en.split()) > 60:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", overview_en) if s.strip()]
            overview_en = " ".join(sentences[:2]) if len(sentences) >= 2 else sentences[0]

        overview_hi = f"यह व्याख्यान {hindi_subject} के प्रमुख सिद्धांतों, महत्वपूर्ण परिभाषाओं और व्यावहारिक उदाहरणों का विस्तृत और परीक्षा-उपयोगी अध्ययन प्रस्तुत करता है।"

        if is_hindi:
            overview = overview_hi
        elif is_both:
            overview = f"{overview_en}\n\n[हिन्दी सारांश]: {overview_hi}"
        else:
            overview = overview_en

        overview = self.strip_timestamps_from_text(overview)

        # 3. Extract Definitions
        definitions_found: List[Dict[str, str]] = []
        definition_patterns = [
            r"\b([A-Z][a-zA-Z\s]{2,25})\s+is\s+(?:defined\s+as|known\s+as|called|referred\s+to\s+as)\s+([^.!?]+[.!?])",
            r"\b([A-Z][a-zA-Z\s]{2,25})\s+refers\s+to\s+([^.!?]+[.!?])",
            r"\b([A-Za-z\s]{3,25})\s+is\s+(?:essentially|basically|fundamentally)?\s*(?:a|an|the)\s+([^.!?]+[.!?])"
        ]

        for pat in definition_patterns:
            for match in re.finditer(pat, full_text):
                term_en = self.strip_timestamps_from_text(match.group(1).strip().capitalize())
                meaning_en = self.strip_timestamps_from_text(match.group(2).strip())
                if len(term_en.split()) <= 4 and not any(d["term"].lower() == term_en.lower() for d in definitions_found):
                    if term_en and meaning_en:
                        term_hi = self.HINDI_CONCEPT_MAP.get(term_en.lower(), f"{term_en}")
                        meaning_hi = f"व्याख्यान के अनुसार यह {hindi_subject} की एक महत्वपूर्ण संकल्पना है जो प्रणाली की कार्यप्रणाली को परिभाषित करती है।"

                        if is_hindi:
                            definitions_found.append({"term": term_hi, "meaning": meaning_hi})
                        elif is_both:
                            definitions_found.append({
                                "term": f"{term_en} ({term_hi})",
                                "meaning": f"{meaning_en} / [हिन्दी अर्थ]: {meaning_hi}"
                            })
                        else:
                            definitions_found.append({"term": term_en, "meaning": meaning_en})

                if len(definitions_found) >= 10:
                    break

        # 4. Extract Formulas / Equations
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
                        clean_formula = self.strip_timestamps_from_text(matched_str)
                        if is_hindi:
                            formulas_found.append({
                                "name": "गणितीय / सैद्धांतिक सूत्र (Formula)",
                                "formula": clean_formula,
                                "explanation": f"व्याख्यान में प्रस्तुत मुख्य संबंध: '{clean_formula}'"
                            })
                        elif is_both:
                            formulas_found.append({
                                "name": "Mathematical Relation / गणितीय सूत्र",
                                "formula": clean_formula,
                                "explanation": f"Expression from lecture: '{clean_formula}' / व्याख्यान का सूत्र संबंध"
                            })
                        else:
                            formulas_found.append({
                                "name": "Mathematical / Algorithmic Relation",
                                "formula": clean_formula,
                                "explanation": f"Expression extracted directly from the lecture: '{clean_formula}'"
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

            first_sentence = self.strip_timestamps_from_text(chunk[0].split(".")[0].strip())
            heading_words = [w for w in first_sentence.split() if w.lower() not in {"now", "so", "today", "well", "let's"}]
            heading_en = " ".join(heading_words[:5]).title() or f"Key Topic {len(sections) + 1}"
            heading_hi = f"महत्वपूर्ण विषय {len(sections) + 1}: {self._translate_phrase_to_hindi(heading_en)}"

            if is_hindi:
                heading = heading_hi
            elif is_both:
                heading = f"{heading_en} / {heading_hi}"
            else:
                heading = heading_en

            heading = self.strip_timestamps_from_text(heading)

            key_points = []
            examples = []
            sec_definitions = []

            for p in chunk:
                sents = [self.strip_timestamps_from_text(s.strip()) for s in re.split(r"(?<=[.!?])\s+", p) if len(s.strip()) > 15]
                for s in sents:
                    if re.search(r"\b(?:for example|for instance|such as|consider the case|e\.g\.)\b", s, re.IGNORECASE):
                        if len(examples) < 2:
                            if is_hindi:
                                examples.append(f"उदाहरण: व्याख्यान में प्रस्तुत व्यावहारिक संदर्भ - {s}")
                            elif is_both:
                                examples.append(f"{s} / [हिन्दी उदाहरण]: व्याख्यान का व्यावहारिक संदर्भ")
                            else:
                                examples.append(s)
                    elif len(key_points) < 4 and len(s.split()) >= 6:
                        if is_hindi:
                            key_points.append(f"मुख्य संकल्पना: व्याख्यान के अनुसार, {s}")
                        elif is_both:
                            key_points.append(f"{s} / [मुख्य बिंदु]: {s[:60]}...")
                        else:
                            key_points.append(s)

            for d in definitions_found:
                if len(sec_definitions) < 2 and d not in sec_definitions:
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
                "heading": "मुख्य अध्ययन सामग्री / Core Lecture Content" if is_both else ("मुख्य अध्ययन सामग्री" if is_hindi else "Core Lecture Content"),
                "key_points": ["Key lecture material reviewed and synthesized."],
                "definitions": definitions_found[:2],
                "examples": []
            })

        # 6. Summary
        last_p = self.strip_timestamps_from_text(paragraphs[-1])
        summary_en = last_p if len(last_p.split()) < 80 else " ".join(re.split(r"(?<=[.!?])\s+", last_p)[:3])
        if not summary_en or len(summary_en.split()) < 15:
            summary_en = f"This lecture provided a comprehensive examination of {subject.lower()} fundamentals, highlighting core principles, real-world examples, and academic frameworks."

        summary_hi = f"इस व्याख्यान ने {hindi_subject} के मूलभूत सिद्धांतों, वास्तविक अनुप्रयोगों और परीक्षा-उपयोगी अवधारणाओं का संपूर्ण एवं सुव्यवस्थित निष्कर्ष प्रस्तुत किया है।"

        if is_hindi:
            summary = summary_hi
        elif is_both:
            summary = f"{summary_en}\n\n[निष्कर्ष सारांश]: {summary_hi}"
        else:
            summary = summary_en

        summary = self.strip_timestamps_from_text(summary)

        # 7. Glossary
        glossary = []
        for d in definitions_found:
            glossary.append({"term": d["term"], "meaning": d["meaning"]})

        # 8. Revision Questions & Practice Quizzes (MCQs)
        revision_count = 3 if detail_level == "short" else (5 if detail_level == "medium" else 7)
        revision_questions = []
        mcqs = []

        all_sentences = [
            self.strip_timestamps_from_text(s.strip())
            for s in re.split(r"(?<=[.!?])\s+", full_text)
            if len(s.split()) >= 8 and not re.match(r"^(?:Good morning|Hello|Welcome|Hi everyone)", s.strip(), re.IGNORECASE)
        ]

        for i in range(min(revision_count, len(all_sentences))):
            target_sent = all_sentences[i * max(1, len(all_sentences) // max(1, revision_count))]
            words = target_sent.split()
            first_clause = " ".join(words[:5])

            if is_hindi:
                ques = f"व्याख्यान के अनुसार, '{first_clause}...' का क्या मुख्य महत्व या कार्यप्रणाली है?"
                ans = f"व्याख्यान के अनुसार: {target_sent}"
                mcq_q = f"{hindi_subject} के संदर्भ में, निम्नलिखित में से कौन सा कथन सबसे सटीक है?"
                correct_opt = f"A) {target_sent[:80]}..." if len(target_sent) > 80 else f"A) {target_sent}"
                opt_b = "B) यह अवधारणा पाठ्यक्रम के मुख्य सिद्धांतों से पूर्णतः असंबद्ध है।"
                opt_c = "C) इस सिद्धांत को आधुनिक प्रयोगों द्वारा अप्रचलित सिद्ध किया जा चुका है।"
                opt_d = "D) व्याख्यान के अनुसार इसका कोई व्यावहारिक अथवा शैक्षणिक उपयोग नहीं है।"
                exp = f"व्याख्यान में स्पष्ट रूप से बताया गया है: '{target_sent}'"
            elif is_both:
                ques = f"What is the significance of '{first_clause}...'? / व्याख्यान के अनुसार इसका क्या महत्व है?"
                ans = f"{target_sent}\n[हिन्दी उत्तर]: व्याख्यान के अनुसार यह विषय की मुख्य संकल्पना को सिद्ध करता है।"
                mcq_q = f"Which statement best reflects the lecture discussion? / व्याख्यान के अनुसार कौन सा कथन सही है?"
                correct_opt = f"A) {target_sent[:60]}... / यह कथन सही है"
                opt_b = "B) It is unrelated to core principles. / यह असंबद्ध है।"
                opt_c = "C) The concept was proven obsolete. / यह अप्रचलित है।"
                opt_d = "D) No practical applications exist. / इसका कोई अनुप्रयोग नहीं है।"
                exp = f"As highlighted in the lecture: '{target_sent}' / व्याख्यान में इसका स्पष्ट उल्लेख है।"
            else:
                ques = f"According to the lecture, what is the significance of: '{first_clause}...'?"
                ans = target_sent
                mcq_q = f"Which statement best reflects the discussion regarding {subject} in this lecture?"
                correct_opt = f"A) {target_sent[:70]}..." if len(target_sent) > 70 else f"A) {target_sent}"
                opt_b = "B) It is completely unrelated to the core principles presented in the course."
                opt_c = "C) The concept was proven obsolete and replaced entirely by manual methods."
                opt_d = "D) The lecture demonstrated that no practical applications currently exist."
                exp = f"As highlighted directly in the lecture transcript: '{target_sent}'"

            revision_questions.append({
                "question": ques,
                "answer": ans
            })

            mcqs.append({
                "question": mcq_q,
                "options": [correct_opt, opt_b, opt_c, opt_d],
                "correct_answer": correct_opt,
                "explanation": exp
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

        sanitized = self.sanitize_notes_dict(result)
        validated = LectureNotes.model_validate(sanitized)
        return validated.model_dump()

    @classmethod
    def _translate_phrase_to_hindi(cls, phrase: str) -> str:
        """Translates or provides Hindi equivalent for known academic topics."""
        lower = phrase.lower()
        for k, v in cls.HINDI_CONCEPT_MAP.items():
            if k in lower:
                return v
        return f"{phrase} (मुख्य अवधारणा)"
