"""
Script for deleting a book from metadata and vector stores.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import METADATA_FILE, SUMMARY_INDEX_PATH, FULLTEXT_INDEX_PATH, EMBEDDING_MODEL
from utils.logger import configure_root_logger, get_logger
from embedding.vector_store import SummaryVectorStore, FulltextVectorStore
from embedding.embedder import GeminiEmbedder

configure_root_logger(log_file=Path("logs/delete_book.log"), level=20)
logger = get_logger(__name__)

def delete_book(book_id: str) -> bool:
    """Deletes a book from the books.json file and FAISS vector stores using soft delete."""
    # 1. Remove from metadata
    if not METADATA_FILE.exists():
        logger.error(f"Metadata file not found: {METADATA_FILE}")
        return False
        
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        books = json.load(f)
        
    initial_count = len(books)
    books = [b for b in books if b.get('book_id') != book_id]
    
    if len(books) == initial_count:
        logger.warning(f"Book {book_id} not found in {METADATA_FILE}.")
    else:
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(books, f, indent=4)
        logger.info(f"Removed metadata for book {book_id}")
        
    try:
        # Determine dimension and load vector stores
        from utils.api_key_manager import create_gemini_embedding_key_manager
        embedding_key_manager = create_gemini_embedding_key_manager()
        embedder = GeminiEmbedder(key_manager=embedding_key_manager)
        dimension = len(embedder.embed_text("test"))
        
        # Soft delete from Summary Index
        if SUMMARY_INDEX_PATH.exists():
            summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dimension)
            deleted_summaries = summary_store.delete_by_book_id(book_id)
            logger.info(f"Soft deleted {deleted_summaries} vectors from Summary index for {book_id}")
            
        # Soft delete from Fulltext Index
        if FULLTEXT_INDEX_PATH.exists():
            fulltext_store = FulltextVectorStore(FULLTEXT_INDEX_PATH, dimension=dimension)
            deleted_chunks = fulltext_store.delete_by_book_id(book_id)
            logger.info(f"Soft deleted {deleted_chunks} vectors from Fulltext index for {book_id}")
            
    except Exception as e:
        logger.error(f"Error during vector deletion for {book_id}: {e}")
        return False
        
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_book.py <book_id>")
        sys.exit(1)
        
    book_id = sys.argv[1]
    success = delete_book(book_id)
    if success:
        print(f"Successfully deleted {book_id}")
    else:
        print(f"Failed to delete {book_id}")
