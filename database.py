"""
Database Operations Module.
Manages persistent SQLite storage for lecture transcripts, generated study notes,
history search, editing, and analytics.
Ensures connections are properly closed to avoid file-locking on Windows.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from contextlib import contextmanager


class NotesDatabase:
    """SQLite database manager for Smart Notes."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            from config import Config
            self.db_path = Config.DATABASE_PATH
        else:
            self.db_path = Path(db_path)

        self._init_db()

    @contextmanager
    def _connection(self):
        """Context manager that guarantees connection commit, rollback, and closure."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initializes tables and indexes if they do not exist."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    subject TEXT NOT NULL DEFAULT 'General',
                    detail_level TEXT NOT NULL DEFAULT 'medium',
                    raw_transcript TEXT NOT NULL,
                    cleaned_transcript TEXT,
                    structured_notes TEXT NOT NULL,
                    word_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_subject ON notes (subject);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_created ON notes (created_at DESC);
            """)

    def create_note(
        self,
        title: str,
        subject: str,
        detail_level: str,
        raw_transcript: str,
        cleaned_transcript: str,
        structured_notes: Dict[str, Any],
        word_count: int
    ) -> int:
        """
        Saves a newly generated note to the database.

        Returns:
            The newly inserted record's integer ID.
        """
        now = datetime.now(timezone.utc).isoformat()
        notes_json = json.dumps(structured_notes, ensure_ascii=False)

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (
                    title, subject, detail_level, raw_transcript,
                    cleaned_transcript, structured_notes, word_count,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, subject, detail_level, raw_transcript,
                cleaned_transcript, notes_json, word_count, now, now
            ))
            return cursor.lastrowid

    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single note by ID with parsed JSON."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def get_all_notes(
        self,
        search_query: Optional[str] = None,
        subject_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lists stored notes with optional search query, subject filter, and pagination.
        """
        query = "SELECT id, title, subject, detail_level, word_count, created_at, updated_at FROM notes WHERE 1=1"
        params = []

        if subject_filter and subject_filter.strip() and subject_filter.lower() != "all":
            query += " AND LOWER(subject) = LOWER(?)"
            params.append(subject_filter.strip())

        if search_query and search_query.strip():
            query += " AND (LOWER(title) LIKE LOWER(?) OR LOWER(structured_notes) LIKE LOWER(?))"
            like_term = f"%{search_query.strip()}%"
            params.extend([like_term, like_term])

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "title": r["title"],
                    "subject": r["subject"],
                    "detail_level": r["detail_level"],
                    "word_count": r["word_count"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                })
            return results

    def update_note(
        self,
        note_id: int,
        title: Optional[str] = None,
        structured_notes: Optional[Dict[str, Any]] = None,
        subject: Optional[str] = None
    ) -> bool:
        """Updates note title, subject, or structured JSON content."""
        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if title is not None:
            updates.append("title = ?")
            params.append(title.strip())

        if subject is not None:
            updates.append("subject = ?")
            params.append(subject.strip())

        if structured_notes is not None:
            updates.append("structured_notes = ?")
            params.append(json.dumps(structured_notes, ensure_ascii=False))

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(now)

        params.append(note_id)
        query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount > 0

    def delete_note(self, note_id: int) -> bool:
        """Deletes a note record by ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Calculates global library statistics."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(word_count), 0) FROM notes")
            total_notes, total_words = cursor.fetchone()

            cursor.execute("SELECT subject, COUNT(*) as count FROM notes GROUP BY subject ORDER BY count DESC")
            subjects = [{"subject": row["subject"], "count": row["count"]} for row in cursor.fetchall()]

            return {
                "total_notes": total_notes,
                "total_words_processed": total_words,
                "subjects": subjects
            }

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Converts database row to note dictionary with deserialized JSON."""
        structured = {}
        try:
            if row["structured_notes"]:
                structured = json.loads(row["structured_notes"])
        except Exception:
            structured = {}

        return {
            "id": row["id"],
            "title": row["title"],
            "subject": row["subject"],
            "detail_level": row["detail_level"],
            "raw_transcript": row["raw_transcript"],
            "cleaned_transcript": row["cleaned_transcript"],
            "structured_notes": structured,
            "word_count": row["word_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
