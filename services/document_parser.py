"""
Document Parser Service.
Extracts clean plain text from uploaded files: TXT, MD, PDF, and DOCX.
Handles character encoding fallbacks and page extraction errors gracefully.
"""

from pathlib import Path
from typing import Union, BinaryIO
import io


class DocumentParser:
    """Parses text documents of various formats into unified text transcripts."""

    @classmethod
    def parse_file(cls, file_obj: Union[str, Path, BinaryIO], filename: str) -> str:
        """
        Parses text from a file path or file-like stream.

        Args:
            file_obj: Path string, Path object, or file-like binary stream.
            filename: Original filename to inspect the extension.

        Returns:
            Extracted string content.

        Raises:
            ValueError: If file format is unsupported or file is empty.
        """
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if extension in {"txt", "md"}:
            return cls._parse_text(file_obj)
        elif extension == "pdf":
            return cls._parse_pdf(file_obj)
        elif extension in {"docx", "doc"}:
            return cls._parse_docx(file_obj)
        else:
            raise ValueError(
                f"Unsupported file format '.{extension}'. Supported formats are: TXT, MD, PDF, and DOCX."
            )

    @classmethod
    def _parse_text(cls, file_obj: Union[str, Path, BinaryIO]) -> str:
        """Reads plain text / markdown files with multiple encoding fallbacks."""
        if isinstance(file_obj, (str, Path)):
            with open(file_obj, "rb") as f:
                raw_bytes = f.read()
        else:
            raw_bytes = file_obj.read()
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                return raw_bytes.decode(enc).strip()
            except (UnicodeDecodeError, AttributeError):
                continue

        return raw_bytes.decode("utf-8", errors="replace").strip()

    @classmethod
    def _parse_pdf(cls, file_obj: Union[str, Path, BinaryIO]) -> str:
        """Extracts text from PDF documents using pypdf."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("pypdf library is required for PDF parsing.")

        if isinstance(file_obj, (str, Path)):
            reader = PdfReader(str(file_obj))
        else:
            if hasattr(file_obj, "read"):
                stream = io.BytesIO(file_obj.read())
                if hasattr(file_obj, "seek"):
                    file_obj.seek(0)
                reader = PdfReader(stream)
            else:
                reader = PdfReader(file_obj)

        pages_text = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages_text.append(text)

        full_text = "\n\n".join(pages_text).strip()
        if not full_text:
            raise ValueError("The provided PDF does not contain extractable text (it may be a scanned image).")
        return full_text

    @classmethod
    def _parse_docx(cls, file_obj: Union[str, Path, BinaryIO]) -> str:
        """Extracts text from DOCX documents using python-docx."""
        try:
            from docx import Document
        except ImportError:
            raise RuntimeError("python-docx library is required for DOCX parsing.")

        if isinstance(file_obj, (str, Path)):
            doc = Document(str(file_obj))
        else:
            stream = io.BytesIO(file_obj.read())
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            doc = Document(stream)

        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs).strip()
        if not full_text:
            raise ValueError("The DOCX document is empty or contains no readable paragraphs.")
        return full_text
