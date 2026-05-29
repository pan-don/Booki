"""
Vector Memory Vacuuming Scheduler

Scans sibi_books.jsonl for active book IDs, extracts raw vectors directly
from unoptimized FAISS stores, and saves compressed production indices.
"""

import sys
import shutil
from pathlib import Path
import json

# Set project root path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from embedding.vector_store import SummaryVectorStore, FulltextVectorStore
from utils.logger import configure_root_logger, get_logger

configure_root_logger(log_file=Path("logs/vacuum_vectorstore.log"), level=20)
logger = get_logger(__name__)

def consolidate_indices():
    """
    Scans sibi_books.jsonl for active book IDs, extracts raw vectors directly
    from unoptimized FAISS stores, and saves compressed production indices.
    """
    sibi_manifest_path = Path("data/raw/sibi_books.jsonl")
    faiss_dir = Path("data/faiss")

    if not sibi_manifest_path.exists():
        logger.error(f"Manifest file not found: {sibi_manifest_path}")
        return

    # 1. Parse active book IDs from the source of truth manifest
    active_book_ids = set()
    with open(sibi_manifest_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    book_data = json.loads(line)
                    active_book_ids.add(book_data['id'])
                except Exception as e:
                    logger.error(f"Failed to parse line in manifest: {e}")

    logger.info(f"Loaded {len(active_book_ids)} active book IDs from manifest.")

    old_summary_path = faiss_dir / "rec_index.faiss"
    old_fulltext_path = faiss_dir / "chunks_index.faiss"

    if not old_summary_path.exists() or not old_fulltext_path.exists():
        logger.error("Old FAISS index files not found in data/faiss/")
        return

    # 2. Instantiate old unoptimized indices
    old_summary_store = SummaryVectorStore(old_summary_path, dimension=3072)
    old_fulltext_store = FulltextVectorStore(old_fulltext_path, dimension=3072)

    # 3. Instantiate fresh, completely empty index containers
    new_summary_path = faiss_dir / "rec_index_vacuumed.faiss"
    new_fulltext_path = faiss_dir / "chunks_index_vacuumed.faiss"

    # We clear out potential existing files
    for p in [new_summary_path, new_fulltext_path, new_summary_path.with_suffix('.meta.pkl'), new_fulltext_path.with_suffix('.meta.pkl')]:
        if p.exists():
            p.unlink()

    new_summary_store = SummaryVectorStore(new_summary_path, dimension=3072)
    new_fulltext_store = FulltextVectorStore(new_fulltext_path, dimension=3072)

    # 4. Extract and migrate Summary Vectors directly (Zero API Cost)
    summary_migrated = 0
    batch_vectors = []
    batch_metas = []
    for internal_id, meta in old_summary_store.id_to_meta.items():
        if meta.get('book_id') in active_book_ids:
            raw_vector = old_summary_store.index.reconstruct(int(internal_id)).tolist()
            batch_vectors.append(raw_vector)
            batch_metas.append(meta)
            summary_migrated += 1

    if batch_vectors:
        new_summary_store.add_vectors(batch_vectors, batch_metas)

    logger.info(f"Migrated {summary_migrated} active summary vectors.")
    new_summary_store._save()

    # 5. Extract and migrate Fulltext Chunk Vectors directly (Zero API Cost)
    fulltext_migrated = 0
    batch_chunk_vectors = []
    batch_chunk_metas = []
    for internal_id, chunk_meta in old_fulltext_store.id_to_meta.items():
        if chunk_meta.get('book_id') in active_book_ids:
            raw_chunk_vector = old_fulltext_store.index.reconstruct(int(internal_id)).tolist()
            batch_chunk_vectors.append(raw_chunk_vector)
            batch_chunk_metas.append(chunk_meta)
            fulltext_migrated += 1

    if batch_chunk_vectors:
        new_fulltext_store.add_vectors(batch_chunk_vectors, batch_chunk_metas)

    logger.info(f"Migrated {fulltext_migrated} active fulltext chunk vectors.")
    new_fulltext_store._save()

    # 6. Save and overwrite older unoptimized file matrices safely
    logger.info("Executing atomic swap of vacuumed FAISS index files.")

    if new_summary_path.exists() and new_summary_path.with_suffix('.meta.pkl').exists() and new_fulltext_path.exists() and new_fulltext_path.with_suffix('.meta.pkl').exists():

        # Backup existing
        for p in [old_summary_path, old_summary_path.with_suffix('.meta.pkl'), old_fulltext_path, old_fulltext_path.with_suffix('.meta.pkl')]:
            backup_p = p.with_suffix(p.suffix + '.bak')
            shutil.move(p, backup_p)

        # Swap new to target
        shutil.move(new_summary_path, old_summary_path)
        shutil.move(new_summary_path.with_suffix('.meta.pkl'), old_summary_path.with_suffix('.meta.pkl'))
        shutil.move(new_fulltext_path, old_fulltext_path)
        shutil.move(new_fulltext_path.with_suffix('.meta.pkl'), old_fulltext_path.with_suffix('.meta.pkl'))

        logger.info("Index consolidation completed successfully.")
    else:
        logger.error("New vacuumed index files are missing. Atomic swap aborted.")


if __name__ == "__main__":
    consolidate_indices()
