"""
Smart Notes Generator - Flask Application Entrypoint.
Provides RESTful APIs for transcript cleaning, topic segmentation,
AI-powered study notes generation, audio transcription, document parsing,
SQLite persistence, and PDF/Markdown/TXT exports.
"""

import os
import io
import sys
import json
import time
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file, make_response
from werkzeug.utils import secure_filename

# Ensure UTF-8 output encoding for console logs
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import Config
from database import NotesDatabase
from services.cleaner import TranscriptCleaner
from services.segmenter import TopicSegmenter
from services.document_parser import DocumentParser
from services.ai_generator import AINotesGenerator
from services.transcriber import AudioTranscriber
from services.exporter import NotesExporter

# Initialize Flask application
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

# Initialize database and services
db = NotesDatabase(Config.DATABASE_PATH)
ai_generator = AINotesGenerator(api_key=Config.GEMINI_API_KEY, model=Config.GEMINI_MODEL)
audio_transcriber = AudioTranscriber(api_key=Config.GEMINI_API_KEY, model=Config.GEMINI_MODEL)


# ==========================================
# Frontend Page Route
# ==========================================

@app.route("/")
def index():
    """Renders the main single-page web application."""
    return render_template("index.html")


# ==========================================
# REST API Endpoints
# ==========================================

@app.route("/api/config-status", methods=["GET"])
def config_status():
    """Returns application configuration status and active AI engines."""
    has_gemini = bool(Config.GEMINI_API_KEY)
    return jsonify({
        "gemini_configured": has_gemini,
        "openai_configured": has_gemini,
        "active_llm_model": Config.GEMINI_MODEL if has_gemini else "Academic Heuristic Engine (Offline)",
        "active_transcriber_model": Config.GEMINI_MODEL if has_gemini else "Gemini Demo Engine (Offline)",
        "active_whisper_model": Config.GEMINI_MODEL if has_gemini else "Gemini Demo Engine (Offline)",
        "detail_levels": Config.DETAIL_LEVELS,
        "max_upload_mb": Config.MAX_CONTENT_LENGTH // (1024 * 1024)
    })


@app.route("/api/test-connection", methods=["GET", "POST"])
def test_connection():
    """Tests live connectivity to Gemini 3.5 Flash API and reports configuration status or exact errors."""
    data = request.get_json(silent=True) or {}
    test_key = (data.get("api_key") or Config.GEMINI_API_KEY).strip()

    if not test_key:
        return jsonify({
            "status": "not_configured",
            "configured": False,
            "model": Config.GEMINI_MODEL,
            "error": "GEMINI_API_KEY is not set in your .env file. The application is running in local Academic Heuristic Mode.",
            "suggestion": "To enable Gemini 3.5 Flash, open the .env file in the project root, set GEMINI_API_KEY=your_key, and restart the server."
        }), 200

    try:
        from google import genai
        client = genai.Client(api_key=test_key)
        start_time = time.time()
        # Ping model with a short prompt
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents="Respond with 'API_ONLINE'.",
        )
        latency_ms = round((time.time() - start_time) * 1000)
        return jsonify({
            "status": "connected",
            "configured": True,
            "model": Config.GEMINI_MODEL,
            "latency_ms": latency_ms,
            "message": f"Successfully connected to Google Gemini ({Config.GEMINI_MODEL})! Model is online and ready.",
            "sample_response": (response.text or "").strip()
        }), 200
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "status": "error",
            "configured": True,
            "model": Config.GEMINI_MODEL,
            "error": error_msg,
            "error_type": type(e).__name__,
            "suggestion": "Please verify your Gemini API key validity, billing status, or network connection."
        }), 200


@app.route("/api/samples", methods=["GET"])
def get_sample_transcripts():
    """Returns pre-loaded sample lecture transcripts for 1-click testing."""
    samples = []
    sample_dir = Config.SAMPLES_FOLDER

    if sample_dir.exists():
        for file_path in sample_dir.glob("*.txt"):
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                subject = "General"
                name = file_path.stem.replace("_", " ").title()

                if "computer_science" in file_path.name:
                    subject = "Computer Science"
                    title = "Virtual Memory & Paging (CS 301)"
                elif "physics" in file_path.name:
                    subject = "Physics"
                    title = "Quantum Mechanics & Uncertainty Principle"
                elif "biology" in file_path.name:
                    subject = "Biology"
                    title = "DNA Replication & Central Dogma"
                else:
                    title = name

                samples.append({
                    "id": file_path.stem,
                    "title": title,
                    "subject": subject,
                    "words": len(content.split()),
                    "content": content
                })
            except Exception as e:
                print(f"[Error] Failed to read sample {file_path}: {e}")

    return jsonify({"samples": samples})


@app.route("/api/upload-file", methods=["POST"])
def upload_document():
    """
    Accepts text or document files (TXT, MD, PDF, DOCX)
    and extracts plain text.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded in request."}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "Empty filename provided."}), 400

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in Config.ALLOWED_DOCUMENT_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported file type '.{extension}'. Allowed: {', '.join(Config.ALLOWED_DOCUMENT_EXTENSIONS)}"
        }), 400

    try:
        extracted_text = DocumentParser.parse_file(file.stream, filename)
        if not extracted_text.strip():
            return jsonify({"error": "Extracted document contains no readable text."}), 400

        return jsonify({
            "filename": filename,
            "text": extracted_text,
            "word_count": len(extracted_text.split()),
            "message": f"Successfully extracted {len(extracted_text.split())} words from {filename}."
        })
    except Exception as e:
        return jsonify({"error": f"Failed to parse document: {str(e)}"}), 500


@app.route("/api/transcribe-audio", methods=["POST"])
def transcribe_audio():
    """
    Accepts audio recordings and converts them into text using
    Whisper or demonstration engine.
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided in request."}), 400

    audio_file = request.files["audio"]
    if not audio_file or audio_file.filename == "":
        return jsonify({"error": "No audio file selected."}), 400

    filename = secure_filename(audio_file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in Config.ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported audio format '.{extension}'. Supported: {', '.join(sorted(Config.ALLOWED_AUDIO_EXTENSIONS))}"
        }), 400

    try:
        # Save temporarily for processing
        save_path = Config.UPLOAD_FOLDER / filename
        audio_file.save(str(save_path))

        language = request.form.get("language", None)
        transcription_result = audio_transcriber.transcribe(save_path, filename, language=language)

        # Clean up temporary file for privacy and storage optimization
        try:
            if save_path.exists():
                os.remove(save_path)
        except Exception:
            pass

        return jsonify(transcription_result)
    except Exception as e:
        return jsonify({"error": f"Audio transcription failed: {str(e)}"}), 500


@app.route("/api/generate-notes", methods=["POST"])
def generate_notes():
    """
    Main pipeline:
    1. Validates input transcript and options
    2. Cleans verbal fillers, repetitions, and timestamps
    3. Segments topics
    4. Generates structured JSON notes via AI model / Heuristic engine
    5. Saves notes automatically to SQLite database
    """
    data = request.get_json(silent=True) or {}
    raw_transcript = (data.get("transcript") or "").strip()
    subject = (data.get("subject") or "General").strip()
    detail_level = (data.get("detail_level") or "medium").strip().lower()
    language = (data.get("language") or "both").strip().lower()
    clean_fillers = bool(data.get("clean_fillers", True))
    remove_timestamps = bool(data.get("remove_timestamps", True))
    enable_segmentation = bool(data.get("enable_segmentation", True))

    if not raw_transcript:
        return jsonify({"error": "Please provide a lecture transcript or upload content."}), 400

    if detail_level not in Config.DETAIL_LEVELS:
        detail_level = "medium"

    if language not in ("english", "hindi", "both", "bilingual"):
        language = "both"

    try:
        # Step 1: Clean Transcript (timestamps are always purged for notes, Q&A, and quizzes)
        cleaned_transcript, cleaning_stats = TranscriptCleaner.clean(
            raw_transcript,
            remove_fillers=clean_fillers,
            remove_timestamps=True
        )

        effective_transcript = cleaned_transcript if cleaned_transcript else raw_transcript

        # Step 2: Topic Segmentation
        segments = []
        if enable_segmentation:
            segments = TopicSegmenter.segment_transcript(effective_transcript)

        # Step 3: AI Notes Generation (supports English, Hindi, and Bilingual modes)
        notes = ai_generator.generate_notes(
            transcript=effective_transcript,
            subject=subject,
            detail_level=detail_level,
            language=language,
            segments=segments
        )

        title = notes.get("title", f"{subject} Lecture Notes")
        word_count = len(effective_transcript.split())

        # Step 4: Persist in SQLite Database
        note_id = db.create_note(
            title=title,
            subject=subject,
            detail_level=detail_level,
            language=language,
            raw_transcript=raw_transcript,
            cleaned_transcript=cleaned_transcript,
            structured_notes=notes,
            word_count=word_count
        )

        return jsonify({
            "note_id": note_id,
            "title": title,
            "subject": subject,
            "detail_level": detail_level,
            "language": language,
            "word_count": word_count,
            "cleaning_stats": cleaning_stats,
            "segments_count": len(segments),
            "structured_notes": notes,
            "message": "Study notes successfully generated and saved to history."
        }), 201

    except Exception as e:
        return jsonify({
            "error": f"Failed to generate study notes: {str(e)}",
            "error_type": type(e).__name__,
            "active_model": Config.GEMINI_MODEL,
            "api_configured": bool(Config.GEMINI_API_KEY)
        }), 500


@app.route("/api/notes", methods=["GET"])
def list_notes():
    """Lists saved notes with search, subject/language filter, and pagination."""
    search_query = request.args.get("q", "").strip()
    subject_filter = request.args.get("subject", "").strip()
    language_filter = request.args.get("language", "").strip()
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = max(int(request.args.get("offset", 0)), 0)

    notes = db.get_all_notes(
        search_query=search_query,
        subject_filter=subject_filter,
        language_filter=language_filter,
        limit=limit,
        offset=offset
    )
    return jsonify({"notes": notes, "count": len(notes)})


@app.route("/api/notes/<int:note_id>", methods=["GET"])
def get_single_note(note_id: int):
    """Retrieves a single note by ID with full structured JSON."""
    note = db.get_note(note_id)
    if not note:
        return jsonify({"error": f"Note with ID {note_id} not found."}), 404
    return jsonify(note)


@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id: int):
    """Updates an existing note's title, subject, or structured notes."""
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    subject = data.get("subject")
    structured_notes = data.get("structured_notes")

    success = db.update_note(note_id, title=title, structured_notes=structured_notes, subject=subject)
    if not success:
        return jsonify({"error": "Note not found or no changes made."}), 404

    updated_note = db.get_note(note_id)
    return jsonify({"message": "Note updated successfully.", "note": updated_note})


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id: int):
    """Deletes a note record from SQLite history."""
    success = db.delete_note(note_id)
    if not success:
        return jsonify({"error": f"Note with ID {note_id} not found."}), 404
    return jsonify({"message": "Note successfully deleted from history."})


@app.route("/api/notes/<int:note_id>/export", methods=["GET"])
def export_note(note_id: int):
    """
    Exports a saved note in PDF, Markdown, or TXT format.
    Query parameter: format=pdf|markdown|txt
    """
    export_format = request.args.get("format", "pdf").lower()
    note = db.get_note(note_id)
    if not note:
        return jsonify({"error": "Note not found."}), 404

    title = note.get("title", "Lecture_Notes")
    clean_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title)
    subject = note.get("subject", "General")
    structured_notes = note.get("structured_notes", {})

    if export_format == "pdf":
        try:
            pdf_bytes = NotesExporter.to_pdf_bytes(structured_notes, subject=subject)
            response = make_response(pdf_bytes)
            response.headers["Content-Type"] = "application/pdf"
            response.headers["Content-Disposition"] = f'attachment; filename="{clean_title}.pdf"'
            return response
        except Exception as e:
            return jsonify({"error": f"PDF export generation failed: {str(e)}"}), 500

    elif export_format in ("markdown", "md"):
        md_text = NotesExporter.to_markdown(structured_notes, subject=subject)
        response = make_response(md_text)
        response.headers["Content-Type"] = "text/markdown; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="{clean_title}.md"'
        return response

    elif export_format in ("txt", "text"):
        txt_text = NotesExporter.to_txt(structured_notes, subject=subject)
        response = make_response(txt_text)
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="{clean_title}.txt"'
        return response

    else:
        return jsonify({"error": f"Unsupported export format '{export_format}'. Supported: pdf, markdown, txt"}), 400


@app.route("/api/stats", methods=["GET"])
def get_library_stats():
    """Returns library analytics and processing stats."""
    return jsonify(db.get_stats())


# ==========================================
# Error Handlers
# ==========================================

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Uploaded file is too large. Maximum size is 50MB."}), 413


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Requested API endpoint not found."}), 404
    return render_template("index.html")


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal server error occurred. Please try again."}), 500


if __name__ == "__main__":
    print(f"[*] Starting Smart Notes Generator server on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
