"""Structure-aware text chunking for RAG.

Chunks documents with the following priority:
1. Split on section headers (markdown ## or #)
2. Split on paragraph breaks
3. Split on sentence boundaries
4. Maintain overlap between chunks for context
"""

import re
from dataclasses import dataclass

import structlog

from src.modules.rag.schemas import Chunk

logger = structlog.get_logger()


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""

    max_size: int = 1500  # Maximum characters per chunk
    overlap: int = 800  # Characters to overlap between chunks
    min_chunk_size: int = 100  # Minimum viable chunk size


def chunk_document(
    content: str,
    source: str,
    config: ChunkingConfig | None = None,
    *,
    title: str = "",
) -> list[Chunk]:
    """Chunk a document with structure awareness.

    Splits documents respecting their structure:
    - Markdown headers create natural boundaries
    - Paragraphs are kept together when possible
    - Sentence boundaries are used for fine-grained splitting
    - Overlap preserves context across chunk boundaries

    Args:
        content: The document content to chunk.
        source: Source filename for metadata.
        config: Chunking configuration (uses defaults if not provided).
        title: Document title (first heading or filename).

    Returns:
        List of Chunk objects ready for embedding.
    """
    config = config or ChunkingConfig()

    if not content.strip():
        return []

    # Split by headers first
    sections = _split_by_headers(content)

    chunks: list[Chunk] = []
    position = 0

    for header, section_content in sections:
        section_chunks = _chunk_section(
            section_content,
            source=source,
            section=header,
            start_position=position,
            config=config,
            title=title,
        )
        chunks.extend(section_chunks)
        position += len(section_chunks)

    logger.debug(
        "document_chunked",
        source=source,
        title=title,
        chunks_created=len(chunks),
        content_length=len(content),
    )

    return chunks


def _split_by_headers(content: str) -> list[tuple[str, str]]:
    """Split content by markdown headers.

    Args:
        content: Document content.

    Returns:
        List of (header, content) tuples.
    """
    # Pattern matches markdown headers (# or ##, etc.)
    header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    sections: list[tuple[str, str]] = []
    last_end = 0
    current_header = ""

    for match in header_pattern.finditer(content):
        # Content before this header belongs to the previous section
        if last_end < match.start():
            section_content = content[last_end : match.start()].strip()
            if section_content:
                sections.append((current_header, section_content))

        # Update current header
        current_header = match.group(2).strip()
        last_end = match.end()

    # Don't forget the last section
    remaining = content[last_end:].strip()
    if remaining:
        sections.append((current_header, remaining))

    # If no headers found, return the whole content
    if not sections:
        sections = [("", content.strip())]

    return sections


def _chunk_section(
    content: str,
    source: str,
    section: str,
    start_position: int,
    config: ChunkingConfig,
    *,
    title: str = "",
) -> list[Chunk]:
    """Chunk a single section.

    Args:
        content: Section content.
        source: Source filename.
        section: Section header.
        start_position: Starting position for chunk numbering.
        config: Chunking configuration.
        title: Document title.

    Returns:
        List of chunks for this section.
    """
    if len(content) <= config.max_size:
        # Section fits in one chunk
        return [
            Chunk(
                content=f"{section}\n\n{content}" if section else content,
                source=source,
                section=section,
                position=start_position,
                title=title,
            )
        ]

    # Need to split the section
    text_chunks = _split_with_overlap(content, config)

    return [
        Chunk(
            content=f"{section}\n\n{chunk_text}" if section else chunk_text,
            source=source,
            section=section,
            position=start_position + i,
            title=title,
        )
        for i, chunk_text in enumerate(text_chunks)
    ]


def _split_with_overlap(
    text: str,
    config: ChunkingConfig,
) -> list[str]:
    """Split text into overlapping chunks.

    Uses paragraph and sentence boundaries for natural splits.

    Args:
        text: Text to split.
        config: Chunking configuration.

    Returns:
        List of text chunks.
    """
    # First, try splitting by paragraphs
    paragraphs = _split_by_paragraphs(text)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for para in paragraphs:
        para_length = len(para)

        # If single paragraph exceeds max size, split it further
        if para_length > config.max_size:
            # Flush current chunk first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            # Split the large paragraph by sentences
            sentence_chunks = _split_paragraph_by_sentences(para, config)
            chunks.extend(sentence_chunks)
            continue

        # Check if adding this paragraph exceeds the limit
        new_length = current_length + para_length + (2 if current_chunk else 0)

        if new_length > config.max_size and current_chunk:
            # Flush current chunk
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(chunk_text)

            # Start new chunk with overlap
            overlap_text = _get_overlap_text(chunk_text, config.overlap)
            if overlap_text:
                current_chunk = [overlap_text, para]
                current_length = len(overlap_text) + len(para) + 2
            else:
                current_chunk = [para]
                current_length = para_length
        else:
            current_chunk.append(para)
            current_length = new_length

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def _split_by_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs.

    Args:
        text: Text to split.

    Returns:
        List of paragraphs (non-empty strings).
    """
    # Split on multiple newlines
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _split_paragraph_by_sentences(
    paragraph: str,
    config: ChunkingConfig,
) -> list[str]:
    """Split a paragraph into sentence-based chunks.

    Args:
        paragraph: Large paragraph to split.
        config: Chunking configuration.

    Returns:
        List of sentence-based chunks.
    """
    # Simple sentence splitting (period, question mark, exclamation mark followed by space)
    sentence_pattern = re.compile(r"([.!?]+)\s+")

    sentences: list[str] = []
    last_end = 0

    for match in sentence_pattern.finditer(paragraph):
        sentence = paragraph[last_end : match.end()].strip()
        if sentence:
            sentences.append(sentence)
        last_end = match.end()

    # Add remaining text
    remaining = paragraph[last_end:].strip()
    if remaining:
        sentences.append(remaining)

    # Now group sentences into chunks
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)
        new_length = current_length + sentence_length + (1 if current_chunk else 0)

        if new_length > config.max_size and current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(chunk_text)

            # Start new chunk with overlap
            overlap_text = _get_overlap_text(chunk_text, config.overlap)
            if overlap_text:
                current_chunk = [overlap_text, sentence]
                current_length = len(overlap_text) + sentence_length + 1
            else:
                current_chunk = [sentence]
                current_length = sentence_length
        else:
            current_chunk.append(sentence)
            current_length = new_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def _get_overlap_text(text: str, overlap_size: int) -> str:
    """Get the last overlap_size characters from text, preferring sentence boundaries.

    Args:
        text: Text to get overlap from.
        overlap_size: Desired overlap size in characters.

    Returns:
        Overlap text, trying to break at sentence boundaries.
    """
    if len(text) <= overlap_size:
        return text

    # Get the raw overlap
    overlap = text[-overlap_size:]

    # Try to find a sentence start within the overlap
    sentence_start = re.search(r"[.!?]\s+", overlap)
    if sentence_start:
        return overlap[sentence_start.end() :].strip()

    # Try to find a word boundary
    word_start = overlap.find(" ")
    if word_start > 0:
        return overlap[word_start:].strip()

    return overlap.strip()
