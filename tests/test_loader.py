"""Tests for document loading."""

from pathlib import Path

import pytest

from src.modules.rag.loader import (
    DocumentLoadError,
    list_documents,
    load_document,
)


class TestLoadDocument:
    """Tests for load_document function."""

    def test_load_markdown_file(self, tmp_path: Path):
        """Should load markdown file content."""
        doc_path = tmp_path / "test.md"
        doc_path.write_text("# Hello\n\nThis is content.")

        result = load_document(doc_path)

        assert result.content == "# Hello\n\nThis is content."
        assert result.source == "test.md"
        assert result.file_path == doc_path

    def test_load_text_file(self, tmp_path: Path):
        """Should load text file content."""
        doc_path = tmp_path / "test.txt"
        doc_path.write_text("Plain text content.")

        result = load_document(doc_path)

        assert result.content == "Plain text content."
        assert result.source == "test.txt"

    def test_load_markdown_extracts_title_from_h1(self, tmp_path: Path):
        """Should extract title from first H1 heading in markdown."""
        doc_path = tmp_path / "policy.md"
        doc_path.write_text("# Volunteer Handbook\n\nWelcome to the shelter!")

        result = load_document(doc_path)

        assert result.title == "Volunteer Handbook"
        assert result.document_type == "markdown"

    def test_load_markdown_title_fallback_to_filename(self, tmp_path: Path):
        """Should fall back to filename when no H1 heading."""
        doc_path = tmp_path / "notes.md"
        doc_path.write_text("## Section One\n\nNo H1 here.")

        result = load_document(doc_path)

        assert result.title == "notes"  # filename without extension
        assert result.document_type == "markdown"

    def test_load_text_file_uses_filename_as_title(self, tmp_path: Path):
        """Should use filename as title for text files."""
        doc_path = tmp_path / "procedures.txt"
        doc_path.write_text("Step 1: Check in at front desk.")

        result = load_document(doc_path)

        assert result.title == "procedures"  # filename without extension
        assert result.document_type == "text"

    def test_load_markdown_extracts_first_h1_only(self, tmp_path: Path):
        """Should extract only the first H1 heading."""
        doc_path = tmp_path / "multi.md"
        doc_path.write_text("# First Title\n\n# Second Title\n\nContent.")

        result = load_document(doc_path)

        assert result.title == "First Title"

    def test_load_markdown_title_strips_whitespace(self, tmp_path: Path):
        """Should strip whitespace from extracted title."""
        doc_path = tmp_path / "spaced.md"
        doc_path.write_text("#   Spaced Title   \n\nContent.")

        result = load_document(doc_path)

        assert result.title == "Spaced Title"

    def test_load_nonexistent_file_raises(self, tmp_path: Path):
        """Should raise error for nonexistent file."""
        doc_path = tmp_path / "missing.md"

        with pytest.raises(DocumentLoadError) as exc_info:
            load_document(doc_path)

        assert "File not found" in str(exc_info.value)

    def test_load_unsupported_format_raises(self, tmp_path: Path):
        """Should raise error for unsupported format."""
        doc_path = tmp_path / "test.pdf"
        doc_path.write_text("fake pdf content")

        with pytest.raises(DocumentLoadError) as exc_info:
            load_document(doc_path)

        assert "Unsupported file format" in str(exc_info.value)

    def test_load_preserves_unicode(self, tmp_path: Path):
        """Should preserve unicode characters."""
        doc_path = tmp_path / "unicode.md"
        doc_path.write_text("Hello 世界! 🐕", encoding="utf-8")

        result = load_document(doc_path)

        assert result.content == "Hello 世界! 🐕"


class TestListDocuments:
    """Tests for list_documents function."""

    def test_list_empty_directory(self, tmp_path: Path):
        """Should return empty list for empty directory."""
        result = list_documents(tmp_path)

        assert result == []

    def test_list_nonexistent_directory(self, tmp_path: Path):
        """Should return empty list for nonexistent directory."""
        result = list_documents(tmp_path / "missing")

        assert result == []

    def test_list_markdown_files(self, tmp_path: Path):
        """Should list markdown files."""
        (tmp_path / "doc1.md").write_text("content")
        (tmp_path / "doc2.md").write_text("content")

        result = list_documents(tmp_path)

        assert len(result) == 2
        assert all(p.suffix == ".md" for p in result)

    def test_list_text_files(self, tmp_path: Path):
        """Should list text files."""
        (tmp_path / "doc1.txt").write_text("content")
        (tmp_path / "doc2.txt").write_text("content")

        result = list_documents(tmp_path)

        assert len(result) == 2
        assert all(p.suffix == ".txt" for p in result)

    def test_list_mixed_formats(self, tmp_path: Path):
        """Should list both markdown and text files."""
        (tmp_path / "doc1.md").write_text("content")
        (tmp_path / "doc2.txt").write_text("content")

        result = list_documents(tmp_path)

        assert len(result) == 2

    def test_list_ignores_unsupported_formats(self, tmp_path: Path):
        """Should ignore unsupported file formats."""
        (tmp_path / "doc.md").write_text("content")
        (tmp_path / "doc.pdf").write_text("content")
        (tmp_path / "doc.docx").write_text("content")

        result = list_documents(tmp_path)

        assert len(result) == 1
        assert result[0].name == "doc.md"

    def test_list_returns_sorted(self, tmp_path: Path):
        """Should return files sorted by name."""
        (tmp_path / "charlie.md").write_text("content")
        (tmp_path / "alpha.md").write_text("content")
        (tmp_path / "bravo.md").write_text("content")

        result = list_documents(tmp_path)

        names = [p.name for p in result]
        assert names == ["alpha.md", "bravo.md", "charlie.md"]
