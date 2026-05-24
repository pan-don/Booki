from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from utils.logger import get_logger
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP, MIN_PARAGRAPH_LEN, MIN_CHUNK_LEN

logger = get_logger(__name__)

@dataclass
class ChunkConfig:
    min_paragraph_len: int = MIN_PARAGRAPH_LEN
    chunk_size: int = CHUNK_SIZE
    chunk_overlap: int = CHUNK_OVERLAP
    min_chunk_len: int = MIN_CHUNK_LEN


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"[ \t\u00A0]+", " ", text)
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if re.match(r"^\s*(page|halaman)?\s*\d+\s*$", line, re.IGNORECASE):
            continue
        if line:
            cleaned.append(line)
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_paragraphs(text: str, min_len: int) -> List[str]:
    if not text:
        return []
    text = re.sub(r"\n{2,}", "\n\n", text)
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [p for p in paras if len(p) >= min_len]


def chunk_paragraphs(paragraphs: List[str], config: ChunkConfig) -> List[str]:
    if not paragraphs:
        return []
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if not current:
            current = [para]
            current_len = para_len
            continue

        sep_len = 2
        if current_len + sep_len + para_len <= config.chunk_size:
            current.append(para)
            current_len += sep_len + para_len
        else:
            chunk_text = "\n\n".join(current)
            if len(chunk_text) >= config.min_chunk_len:
                chunks.append(chunk_text)
            overlap_text = ""
            if config.chunk_overlap > 0 and chunks:
                prev = chunks[-1]
                overlap_text = prev[-config.chunk_overlap:] if len(prev) > config.chunk_overlap else prev
            new_current = []
            if overlap_text:
                new_current.append(overlap_text)
            new_current.append(para)
            current = new_current
            current_len = len(overlap_text) + (len(para) if overlap_text else 0) + (2 if overlap_text else 0)

    if current:
        chunk_text = "\n\n".join(current)
        if len(chunk_text) >= config.min_chunk_len:
            chunks.append(chunk_text)
    return chunks


def process_parsed_json(parsed_json_path: Path, config: ChunkConfig) -> Dict[str, Any]:
    logger.info(f"Loading parsed JSON: {parsed_json_path.name}")
    with open(parsed_json_path, "r", encoding="utf-8") as f:
        parsed = json.load(f)

    pages = parsed.get("pages", [])
    full_text = "\n\n".join([p.get("text", "") for p in pages])
    logger.debug(f"Raw text length: {len(full_text)} chars")

    full_text = clean_text(full_text)
    logger.debug(f"Cleaned text length: {len(full_text)} chars")

    paragraphs = split_paragraphs(full_text, config.min_paragraph_len)
    logger.info(f"Split into {len(paragraphs)} paragraphs")

    chunks = chunk_paragraphs(paragraphs, config)
    logger.info(f"Created {len(chunks)} chunks")

    return {
        "metadata": {
            "file_name": parsed.get("file_name", ""),
            "source": parsed.get("source", ""),
            "num_pages": parsed.get("num_pages", 0),
            "num_paragraphs": len(paragraphs),
            "num_chunks": len(chunks),
        },
        "chunks": chunks,
        "paragraphs": paragraphs,
    }
    
    
    


if __name__ == "__main__":
    # Contoh penggunaan
    # result = process_parsed_json(Path("output.json"), ChunkConfig())
    # print(result["metadata"])
    pass
