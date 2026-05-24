"""
Script for updating a book's description and metadata.
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import METADATA_FILE, SUMMARY_INDEX_PATH, FULLTEXT_INDEX_PATH, EMBEDDING_MODEL
from utils.logger import configure_root_logger, get_logger
from embedding.vector_store import SummaryVectorStore, FulltextVectorStore
from embedding.embedder import GeminiEmbedder
from summarization.book_summarizer import summarize_book
from parsing.pdf_cleaner import clean_text
from parsing.pdf_parser import parse_pdf_to_text

configure_root_logger(log_file=Path("logs/update_book.log"), level=20)
logger = get_logger(__name__)

def update_book_metadata(book_id: str, new_metadata: Dict[str, Any]) -> bool:
    """Updates book metadata in the books.json file and vector store metadata."""
    if not METADATA_FILE.exists():
        logger.error(f"Metadata file not found: {METADATA_FILE}")
        return False
        
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        books = json.load(f)
        
    book_index = next((i for i, b in enumerate(books) if b.get('book_id') == book_id), None)
    if book_index is None:
        logger.error(f"Book {book_id} not found in metadata.")
        return False
        
    # Update the metadata
    books[book_index].update(new_metadata)
    updated_book = books[book_index]
    
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(books, f, indent=4)
        
    logger.info(f"Updated metadata for book {book_id} in {METADATA_FILE}")
    
    # We should update the summary vector to reflect new descriptions/metadata.
    # We do NOT re-summarize, we just recreate the enhanced embedding string and update FAISS.
    try:
        # Load embedding dimension via a dummy embed
        embedder = GeminiEmbedder()
        dimension = len(embedder.embed_text("test"))
        
        summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dimension)
        summary_text = updated_book.get("summary_text")
        
        if summary_text:
            # Re-generate recommendation string: Judul + Jenjang + Kelas + Mapel + Ringkasan
            # Use embedder helper if available
            format_doc = {"metadata": updated_book, "summary_text": summary_text}
            enhanced_text = embedder._build_enhanced_text(format_doc)
            summary_vector = embedder.embed_text(enhanced_text)
            
            # Delete old summary vector
            summary_store.delete_by_book_id(book_id)
            
            # Add new summary
            summary_meta = {
                "book_id": book_id,
                "judul_buku": updated_book.get("judul_buku", updated_book.get("title", "Unknown")),
                "title": updated_book.get("judul_buku", updated_book.get("title", "Unknown")),
                "text": summary_text,
                "type": "summary",
                "jenjang": updated_book.get("jenjang"),
                "kelas": updated_book.get("kelas"),
                "mata_pelajaran": updated_book.get("mata_pelajaran"),
            }
            summary_store.add_vectors([summary_vector], [summary_meta])
            summary_store._save()
            logger.info(f"Updated summary vector for book {book_id}")
        else:
            logger.warning(f"Could not re-embed: no existing summary_text found for {book_id}")
            
    except Exception as e:
        logger.error(f"Failed to update vector store for {book_id}: {e}")
        return False
        
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_book.py <book_id> <key=value> ...")
        sys.exit(1)
        
    book_id = sys.argv[1]
    new_data = {}
    for arg in sys.argv[2:]:
        key, value = arg.split('=', 1)
        new_data[key] = value
        
    success = update_book_metadata(book_id, new_data)
    if success:
        print(f"Successfully updated {book_id}")
    else:
        print(f"Failed to update {book_id}")
