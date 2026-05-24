"""
Text chunking utilities for splitting long documents into overlapping chunks.
Uses character-based splitting with configurable size and overlap.
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP
from utils.logger import get_logger

logger = get_logger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks based on character count.
    
    Args:
        text: Input text to be chunked.
        chunk_size: Maximum number of characters per chunk.
        overlap: Number of characters to overlap between consecutive chunks.
        metadata: Optional base metadata to attach to each chunk (e.g., book_id, title).
        
    Returns:
        List of dictionaries, each containing:
            - 'text': str, the chunk content
            - 'start': int, starting character index in original text
            - 'end': int, ending character index (exclusive)
            - 'index': int, chunk order (0-based)
            - any additional metadata provided
    """
    if not text:
        logger.warning("Empty text provided for chunking")
        return []
    
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got {overlap}")
    if overlap >= chunk_size:
        logger.warning(f"Overlap ({overlap}) >= chunk_size ({chunk_size}), setting overlap to chunk_size-1")
        overlap = chunk_size - 1
    
    chunks = []
    start = 0
    text_len = len(text)
    chunk_index = 0
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        # If we are not at the end, try to find a natural break (space, newline) within last 20% of chunk
        if end < text_len:
            # Find last space or newline in the last 20% of the chunk to avoid cutting words
            lookback_range = min(int(chunk_size * 0.2), 200)
            for pos in range(end, max(start, end - lookback_range) - 1, -1):
                if text[pos] in (' ', '\n', '\t'):
                    end = pos + 1  # include the space? better cut after space
                    break
        
        chunk_text = text[start:end].strip()
        if chunk_text:  # avoid empty chunks
            chunk_metadata = {
                'text': chunk_text,
                'start': start,
                'end': end,
                'index': chunk_index
            }
            if metadata:
                chunk_metadata.update(metadata)
            chunks.append(chunk_metadata)
        
        # Move start for next chunk, respecting overlap
        start = start + chunk_size - overlap
        chunk_index += 1
        
        # Avoid infinite loop if no progress
        if start <= start - chunk_size + overlap:
            logger.error("Stuck in chunking loop, breaking")
            break
    
    logger.info(f"Created {len(chunks)} chunks from text of length {text_len} (size={chunk_size}, overlap={overlap})")
    return chunks


def chunk_text_sentences(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Alternative chunking method using sentence boundaries (split by '.', '!', '?').
    More natural for retrieval but slower. Use for better semantic boundaries.
    Requires nltk or simple regex. Here we provide a simple regex version.
    """
    import re
    
    # Split into sentences (naive)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    current_start = 0
    chunk_index = 0
    
    for sent in sentences:
        if len(current_chunk) + len(sent) + 1 <= chunk_size:
            if current_chunk:
                current_chunk += " " + sent
            else:
                current_chunk = sent
                current_start = text.find(sent)  # approximate
        else:
            # save current chunk
            if current_chunk:
                chunk_metadata = {
                    'text': current_chunk.strip(),
                    'start': current_start,
                    'end': current_start + len(current_chunk),  # approximate
                    'index': chunk_index
                }
                if metadata:
                    chunk_metadata.update(metadata)
                chunks.append(chunk_metadata)
                chunk_index += 1
            # start new chunk with overlap: take last part of previous chunk
            if overlap > 0 and current_chunk:
                # take last `overlap` characters of previous chunk
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + " " + sent
                current_start = max(0, current_start + len(current_chunk) - overlap)
            else:
                current_chunk = sent
                current_start = text.find(sent)
    
    # last chunk
    if current_chunk:
        chunks.append({
            'text': current_chunk.strip(),
            'start': current_start,
            'end': current_start + len(current_chunk),
            'index': chunk_index,
            **(metadata or {})
        })
    
    logger.info(f"Created {len(chunks)} sentence-based chunks")
    return chunks


# Convenience function using default settings
def chunk_document(
    text: str,
    method: str = "character",
    book_id: Optional[str] = None,
    title: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    High-level function to chunk a full document with optional book metadata.
    
    Args:
        text: Full document text.
        method: 'character' or 'sentence'.
        book_id: Identifier for the book.
        title: Book title.
    
    Returns:
        List of chunk dicts with metadata.
    """
    metadata = {}
    if book_id is not None:
        metadata['book_id'] = book_id
    if title is not None:
        metadata['title'] = title
    
    if method == "sentence":
        return chunk_text_sentences(text, metadata=metadata)
    else:
        return chunk_text(text, metadata=metadata)