"""
Ingestion pipeline untuk memproses semua buku dari metadata, melakukan:
- parsing PDF → teks bersih
- chunking untuk fulltext
- summarization
- embedding (summary & chunks)
- build FAISS indexes (summary & fulltext)
Hasil akhir disimpan di data/faiss/
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import traceback

# Tambahkan root proyek ke path jika perlu
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, 
    DATA_DIR, METADATA_FILE, FAISS_DIR, 
    SUMMARY_INDEX_PATH, FULLTEXT_INDEX_PATH
)
from utils.logger import configure_root_logger, get_logger
from parsing.pdf_parser import parse_pdf_to_text
from parsing.pdf_cleaner import clean_text
from chunking.text_chunker import chunk_document
from summarization.book_summarizer import summarize_book
from embedding.embedder import GeminiEmbedder
from embedding.vector_store import SummaryVectorStore, FulltextVectorStore

# Konfigurasi logging
configure_root_logger(log_file=Path("logs/ingest.log"), level=20) # logging.INFO == 20
logger = get_logger(__name__)


def load_books_metadata() -> List[Dict[str, Any]]:
    """Load list of books from metadata file."""
    if not METADATA_FILE.exists():
        raise FileNotFoundError(f"Metadata file not found: {METADATA_FILE}")
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        books = json.load(f)
    logger.info(f"Loaded {len(books)} books from metadata")
    return books


def process_book(
    book: Dict[str, Any],
    embedder: GeminiEmbedder,
    interactive: bool = False,
    override_summary: str = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Process a single book: parse, clean, chunk, summarize, embed.
    
    Args:
        book: Metadata of the book.
        embedder: Instance of GeminiEmbedder.
        interactive: If True, asks user to confirm or edit the summary.
        override_summary: If provided, skips LLM summarization and uses this text.
        
    Returns:
        Tuple of (summary_vector_metadata, list_of_chunk_metadatas_with_vectors)
        Each metadata dict includes the generated vector.
    """
    book_id = book.get("book_id")
    title = book.get("judul_buku", book.get("title", "Unknown"))
    pdf_path = book.get("pdf_path", book.get("link_pdf"))
    
    if not pdf_path or not Path(pdf_path).exists():
        logger.error(f"Book {book_id} - PDF not found: {pdf_path}")
        raise FileNotFoundError(f"PDF missing for {book_id}")
    
    logger.info(f"Processing book: {title} ({book_id})")
    
    # 1. Parse PDF
    raw_text = parse_pdf_to_text(pdf_path)
    if not raw_text:
        raise ValueError("Parsed text is empty")
    
    # 2. Clean text
    clean_text_content = clean_text(raw_text)
    if not clean_text_content:
        raise ValueError("Cleaned text is empty")
    
    # 3. Summarize (API call or override)
    if override_summary:
        summary_text = override_summary
        logger.info("Using overridden summary.")
    else:
        summary_text = summarize_book(metadata=book, combined_text=clean_text_content)
        if not summary_text:
            raise ValueError("Summary generation failed")
            
    # Admin Interactive review
    if interactive and not override_summary:
        print("\n" + "="*50)
        print("HASIL RINGKASAN MODEL:")
        print("="*50)
        print(summary_text)
        print("="*50)
        user_input = input("Apakah Anda ingin memakai ringkasan ini? (y/n): ")
        if user_input.lower() != 'y':
            print("Ketikkan ringkasan baru Anda (tekan Enter 2x untuk selesai):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            new_summary = "\n".join(lines).strip()
            if new_summary:
                summary_text = new_summary
                logger.info("Summary manually updated by admin.")
    
    # 4. Chunk full text
    chunks = chunk_document(
        text=clean_text_content,
        method="character",
        book_id=book_id,
        title=title
    )
    if not chunks:
        raise ValueError("No chunks created")
    logger.info(f"Created {len(chunks)} chunks for book {book_id}")
    
    # 5. Generate embeddings
    # Summary embedding (gabungan string)
    format_doc = {"metadata": book, "summary_text": summary_text}
    enhanced_summary_text = embedder._build_enhanced_text(format_doc)
    summary_vector = embedder.embed_text(enhanced_summary_text, task_type="RETRIEVAL_DOCUMENT")
    
    # Chunk embeddings (batch for efficiency)
    chunk_texts = [chunk["text"] for chunk in chunks]
    chunk_vectors = embedder.embed_texts(chunk_texts, task_type="RETRIEVAL_DOCUMENT") 

    # 6. Prepare metadata for vector stores
    # Summary metadata
    summary_meta = {
        "book_id": book_id,
        "judul_buku": title,
        "title": title,
        "text": summary_text,
        "type": "summary",
        "jenjang": book.get("jenjang"),
        "kelas": book.get("kelas"),
        "mata_pelajaran": book.get("mata_pelajaran"),
    }
    # Save the updated summary_text back to book metadata
    book["summary_text"] = summary_text
    
    # Add vector to metadata for later collection
    summary_meta["vector"] = summary_vector
    
    # Chunks metadata (each with its vector)
    chunk_metas = []
    for i, (chunk, vec) in enumerate(zip(chunks, chunk_vectors)):
        meta = {
            "book_id": book_id,
            "judul_buku": title,
            "title": title,
            "chunk_text": chunk["text"],
            "chunk_index": chunk.get("index", i),
            "start_char": chunk.get("start"),
            "end_char": chunk.get("end"),
            "type": "fulltext",
        }
        # Include page if exists in chunk metadata
        if "page" in chunk:
            meta["page"] = chunk["page"]
        meta["vector"] = vec
        chunk_metas.append(meta)
    
    logger.info(f"Completed book {book_id}: summary + {len(chunk_metas)} chunks")
    return summary_meta, chunk_metas


def build_and_save_indexes(
    all_summary_metas: List[Dict[str, Any]],
    all_chunk_metas: List[Dict[str, Any]],
    dimension: int
):
    """
    Build FAISS indexes from collected vectors/metadata and save to disk.
    """
    logger.info(f"Building summary index from {len(all_summary_metas)} vectors")
    summary_vectors = [m["vector"] for m in all_summary_metas]
    summary_metadatas = [{k: v for k, v in m.items() if k != "vector"} for m in all_summary_metas]
    
    summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dimension)
    # Use internal method to add all at once (to avoid multiple saves)
    summary_store.add_vectors(summary_vectors, summary_metadatas)
    summary_store._save()  # ensure save
    logger.info(f"Summary index saved to {SUMMARY_INDEX_PATH}")
    
    logger.info(f"Building fulltext index from {len(all_chunk_metas)} vectors")
    chunk_vectors = [m["vector"] for m in all_chunk_metas]
    chunk_metadatas = [{k: v for k, v in m.items() if k != "vector"} for m in all_chunk_metas]
    
    fulltext_store = FulltextVectorStore(FULLTEXT_INDEX_PATH, dimension=dimension)
    fulltext_store.add_vectors(chunk_vectors, chunk_metadatas)
    fulltext_store._save()
    logger.info(f"Fulltext index saved to {FULLTEXT_INDEX_PATH}")


def add_new_book(book_data: Dict[str, Any], interactive: bool = True, override_summary: str = None) -> bool:
    """
    Public admin API for adding a single new book.
    Saves to METADATA_FILE and updates both vector stores.
    """
    if "book_id" not in book_data:
        import uuid
        book_data["book_id"] = str(uuid.uuid4())[:16]
        
    # Phase 1 Alignment: Must inject embedding key manager explicitly
    from utils.api_key_manager import create_gemini_embedding_key_manager
    embedding_key_manager = create_gemini_embedding_key_manager()
    embedder = GeminiEmbedder(key_manager=embedding_key_manager)

    # Dummy to initialize client/dimension
    dimension = len(embedder.embed_text("test"))
    
    try:
        summary_meta, chunk_metas = process_book(book_data, embedder, interactive=interactive, override_summary=override_summary)
        
        # Build and save single book indices
        summary_vectors = [summary_meta.pop("vector")]
        summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dimension)
        summary_store.add_vectors(summary_vectors, [summary_meta])
        summary_store._save()
        
        chunk_vectors = [m.pop("vector") for m in chunk_metas]
        fulltext_store = FulltextVectorStore(FULLTEXT_INDEX_PATH, dimension=dimension)
        fulltext_store.add_vectors(chunk_vectors, chunk_metas)
        fulltext_store._save()
        
        # Append to metadata json
        books = []
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                books = json.load(f)
        books.append(book_data)
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(books, f, indent=4)
            
        logger.info(f"Successfully added new book {book_data['book_id']} to system.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add new book: {e}\n{traceback.format_exc()}")
        return False


def main():
    """Main ingestion pipeline."""
    import argparse
    parser = argparse.ArgumentParser(description="Add books to RAG pipeline.")
    parser.add_argument("--interactive", action="store_true", help="Interactive admin mode")
    parser.add_argument("--id", type=str, help="Add single book ID (must be in JSON)")
    parser.add_argument("--bulk", action="store_true", help="Bulk process all missing from books.json")
    args = parser.parse_args()
    
    if not args.bulk and not args.id:
        logger.info("Use --bulk to run all from JSON or --id <book_id> to add a specific book.")
        return
        
    logger.info("Starting ingestion pipeline")
    
    # Load metadata
    try:
        books = load_books_metadata()
    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        return
        
    if args.id:
        book = next((b for b in books if b.get('book_id') == args.id), None)
        if not book:
            logger.error(f"Book {args.id} not found in metadata file.")
            return
        add_new_book(book, interactive=args.interactive)
        return
    
    # Phase 1 Alignment: Initialize embedder strictly from embedding pool
    from utils.api_key_manager import create_gemini_embedding_key_manager
    embedding_key_manager = create_gemini_embedding_key_manager()
    embedder = GeminiEmbedder(key_manager=embedding_key_manager)
    
    # Get embedding dimension from first embed (or from model)
    # We'll determine dimension by embedding a dummy text
    dummy_vector = embedder.embed_text("test")
    dimension = len(dummy_vector)
    logger.info(f"Embedding dimension: {dimension}")
    
    all_summary_metas = []
    all_chunk_metas = []
    failed_books = []
    
    for book in books:
        try:
            summary_meta, chunk_metas = process_book(book, embedder)
            all_summary_metas.append(summary_meta)
            all_chunk_metas.extend(chunk_metas)
        except Exception as e:
            book_id = book.get("book_id", "unknown")
            logger.error(f"Failed to process book {book_id}: {e}\n{traceback.format_exc()}")
            failed_books.append(book_id)
            continue  # proceed with next book
    
    if not all_summary_metas:
        logger.error("No books successfully processed. Exiting.")
        return
    
    # Build and save indexes
    try:
        build_and_save_indexes(all_summary_metas, all_chunk_metas, dimension)
        logger.info(f"Ingestion completed. Success: {len(all_summary_metas)} books, chunks: {len(all_chunk_metas)}. Failed: {len(failed_books)}")
        if failed_books:
            logger.warning(f"Failed books: {failed_books}")
    except Exception as e:
        logger.error(f"Failed to build/save indexes: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()