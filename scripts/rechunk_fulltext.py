"""
Migration Script Phase 1: Data Layer Optimization (Rechunking and Re-embedding)
This script reads the raw dataset (sibi_books.jsonl), extracts full text,
rechunks the text using updated parameters (2048 size, 250 overlap, 500 min chunk len),
and re-embeds using the gemini-embedding-2 model.

The result is saved directly as 'chunks_index.faiss' to support a granular Jina API integration.
"""

import sys
import json
import traceback
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DATA_DIR, FAISS_DIR, EMBEDDING_DIM
from utils.logger import configure_root_logger, get_logger
from chunking.text_chunker import chunk_document
from embedding.embedder import GeminiEmbedder
from embedding.vector_store import FulltextVectorStore

# Paths
INPUT_JSONL = DATA_DIR / "raw" / "sibi_books.jsonl"
NEW_FAISS_INDEX = FAISS_DIR / "chunks_index_new.faiss"
TARGET_FAISS_INDEX = FAISS_DIR / "chunks_index.faiss"
TARGET_META_PKL = FAISS_DIR / "chunks_index.meta.pkl"

configure_root_logger(log_file=Path("logs/rechunk_migration.log"), level=20)
logger = get_logger(__name__)


def migrate_chunks():
    """Reads raw JSONL, rechunks full text, embeds vectors, and creates a new FAISS index."""
    if not INPUT_JSONL.exists():
        logger.error(f"Input file not found: {INPUT_JSONL}")
        return

    embedder = GeminiEmbedder(output_dim=EMBEDDING_DIM)

    # Check embedding dimension
    try:
        dummy_vector = embedder.embed_text("test")
        dimension = len(dummy_vector)
    except Exception as e:
        logger.error(f"Failed to initialize embedding model: {e}")
        return

    logger.info(f"Using embedding dimension: {dimension}")

    # Initialize the new vector store mapping to chunks_index_new.faiss
    # It will create chunks_index_new.faiss and chunks_index_new.meta.pkl implicitly
    new_store = FulltextVectorStore(NEW_FAISS_INDEX, dimension=dimension)

    total_books = 0
    total_chunks_processed = 0

    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                book_data = json.loads(line)
                book_id = book_data.get("id")
                metadata = book_data.get("metadata", {})
                full_text = book_data.get("full_text")
                title = metadata.get("judul_buku", "Unknown")

                if not full_text:
                    logger.warning(f"No full_text found for book {book_id}, skipping.")
                    continue

                logger.info(f"Processing book {book_id}: {title}")

                # Step 1: Execute granular chunking
                chunks = chunk_document(
                    text=full_text,
                    method="character",
                    book_id=book_id,
                    title=title
                )

                if not chunks:
                    logger.warning(f"No chunks produced for book {book_id}.")
                    continue

                # We batch embed the chunks to mitigate rate-limits.
                # GeminiEmbedder's embed_texts method processes in sequence and has built-in delays.
                # We can do it in smaller batches to avoid high memory spikes.
                BATCH_SIZE = 100
                chunk_texts = [chunk["text"] for chunk in chunks]

                for i in range(0, len(chunk_texts), BATCH_SIZE):
                    batch_texts = chunk_texts[i:i + BATCH_SIZE]
                    batch_chunks = chunks[i:i + BATCH_SIZE]

                    batch_vectors = embedder.embed_texts(batch_texts, task_type="RETRIEVAL_DOCUMENT")

                    if len(batch_vectors) != len(batch_chunks):
                        logger.error(f"Mismatch in vectors and chunks for book {book_id} batch {i}")
                        continue

                    # Build full metadata dicts for vector store
                    metadatas = []
                    for chunk, vec in zip(batch_chunks, batch_vectors):
                        meta = {
                            "book_id": book_id,
                            "judul_buku": title,
                            "title": title,
                            "chunk_text": chunk["text"],
                            "chunk_index": chunk.get("index"),
                            "start_char": chunk.get("start"),
                            "end_char": chunk.get("end"),
                            "type": "fulltext",
                        }
                        if "page" in chunk:
                            meta["page"] = chunk["page"]
                        metadatas.append(meta)

                    # Add vectors to the new store
                    new_store.add_vectors(batch_vectors, metadatas)

                total_chunks_processed += len(chunks)
                total_books += 1

                # Save intermediate state periodically
                if total_books % 10 == 0:
                    new_store._save()
                    logger.info(f"Intermediate save: {total_books} books, {total_chunks_processed} chunks.")

            except Exception as e:
                logger.error(f"Failed to process line in jsonl: {e}\n{traceback.format_exc()}")
                continue

    # Final save of the new index
    new_store._save()
    logger.info(f"Migration completed for {total_books} books, {total_chunks_processed} total chunks generated.")

    # Step 2: Atomic Swap
    logger.info("Executing atomic swap of FAISS index files.")

    new_meta_pkl = NEW_FAISS_INDEX.with_suffix(".meta.pkl")

    if NEW_FAISS_INDEX.exists() and new_meta_pkl.exists():
        # Backup existing
        if TARGET_FAISS_INDEX.exists():
            backup_faiss = TARGET_FAISS_INDEX.with_suffix(".faiss.bak")
            shutil.move(TARGET_FAISS_INDEX, backup_faiss)
            logger.info(f"Backed up old faiss to {backup_faiss}")

        if TARGET_META_PKL.exists():
            backup_meta = TARGET_META_PKL.with_suffix(".meta.pkl.bak")
            shutil.move(TARGET_META_PKL, backup_meta)
            logger.info(f"Backed up old meta to {backup_meta}")

        # Swap new to target
        shutil.move(NEW_FAISS_INDEX, TARGET_FAISS_INDEX)
        shutil.move(new_meta_pkl, TARGET_META_PKL)
        logger.info(f"Atomic swap successful. New indices are now live at {TARGET_FAISS_INDEX}")
    else:
        logger.error("New index files not found. Atomic swap aborted.")


if __name__ == "__main__":
    logger.info("Starting Data Layer Optimization (Migration Script)")
    migrate_chunks()
