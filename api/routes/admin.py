"""
Admin endpoints for managing the RAG system.
- Trigger full re-ingestion pipeline (calls scripts/ingest_all.py)
- Health check for admin endpoints
"""

import json
import threading
import sys
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify

# Add project root to path (ensure scripts module can be imported)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from utils.logger import get_logger

logger = get_logger(__name__)
admin_bp = Blueprint('admin', __name__)

from config.settings import METADATA_FILE, SUMMARY_INDEX_PATH, FULLTEXT_INDEX_PATH
from embedding.embedder import GeminiEmbedder
from embedding.vector_store import SummaryVectorStore, FulltextVectorStore
from utils.file_utils import read_json, write_json

try:
    from scripts.add_book import add_new_book
    ADD_BOOK_AVAILABLE = True
except ImportError as e:
    logger.error(f"Could not import add_new_book: {e}")
    ADD_BOOK_AVAILABLE = False
    add_new_book = None

try:
    from scripts.update_book import update_book_metadata
    UPDATE_BOOK_AVAILABLE = True
except ImportError as e:
    logger.error(f"Could not import update_book_metadata: {e}")
    UPDATE_BOOK_AVAILABLE = False
    update_book_metadata = None

try:
    from scripts.delete_book import delete_book
    DELETE_BOOK_AVAILABLE = True
except ImportError as e:
    logger.error(f"Could not import delete_book: {e}")
    DELETE_BOOK_AVAILABLE = False
    delete_book = None

# Import ingestion main function (with fallback)
try:
    from scripts.add_book import main as ingest_main
    INGEST_AVAILABLE = True
except ImportError as e:
    logger.error(f"Could not import ingest_all: {e}")
    INGEST_AVAILABLE = False
    ingest_main = None


def _run_ingestion():
    """
    Run the full ingestion pipeline in background.
    This function is intended to be called in a separate thread.
    """
    try:
        logger.info("Starting background ingestion pipeline...")
        if ingest_main is not None:
            ingest_main()
            logger.info("Background ingestion completed successfully")
        else:
            logger.error("Ingestion function not available")
    except Exception as e:
        logger.error(f"Background ingestion failed: {e}", exc_info=True)


def _parse_metadata_field(raw_metadata):
    if raw_metadata is None:
        return None
    if isinstance(raw_metadata, dict):
        return raw_metadata
    if isinstance(raw_metadata, str):
        raw_metadata = raw_metadata.strip()
        if not raw_metadata:
            return None
        try:
            return json.loads(raw_metadata)
        except Exception:
            return {"metadata": raw_metadata}
    return {"metadata": str(raw_metadata)}


def _load_metadata_list():
    if METADATA_FILE.exists():
        return read_json(METADATA_FILE)
    return []


def _save_metadata_list(books):
    write_json(METADATA_FILE, books, indent=4)


def _add_summary_only_book(book_data):
    embedder = GeminiEmbedder()
    dimension = len(embedder.embed_text("test"))

    summary_text = book_data.get("summary_text", "").strip()
    if not summary_text:
        raise ValueError("summary_text is required for summary-only add")

    format_doc = {"metadata": book_data, "summary_text": summary_text}
    enhanced_text = embedder._build_enhanced_text(format_doc)
    summary_vector = embedder.embed_text(enhanced_text, task_type="RETRIEVAL_DOCUMENT")

    summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dimension)
    summary_meta = {
        "book_id": book_data.get("book_id"),
        "judul_buku": book_data.get("judul_buku", book_data.get("title", "Unknown")),
        "title": book_data.get("title", book_data.get("judul_buku", "Unknown")),
        "text": summary_text,
        "type": "summary",
        "jenjang": book_data.get("jenjang"),
        "kelas": book_data.get("kelas"),
        "mata_pelajaran": book_data.get("mata_pelajaran"),
    }
    summary_store.add_vectors([summary_vector], [summary_meta])
    summary_store._save()

    books = _load_metadata_list()
    books.append(book_data)
    _save_metadata_list(books)


@admin_bp.route('/admin/ingest', methods=['POST'])
def trigger_ingest():
    """
    Trigger a full re-ingestion of all books.
    This endpoint returns immediately while ingestion runs in background.
    
    Returns:
        JSON with status 'started' or error if ingestion not available.
    """
    if not INGEST_AVAILABLE:
        logger.error("Ingestion pipeline not available")
        return jsonify({
            "status": "error",
            "message": "Ingestion pipeline is not available. Check that scripts/ingest_all.py exists and is importable."
        }), 500
    
    # Start ingestion in background thread to avoid blocking
    thread = threading.Thread(target=_run_ingestion, daemon=True)
    thread.start()
    
    logger.info("Ingestion pipeline triggered via admin API")
    return jsonify({
        "status": "started",
        "message": "Ingestion pipeline is running in background. Check logs for progress."
    }), 202


@admin_bp.route('/admin/health', methods=['GET'])
def admin_health():
    """
    Health check for admin endpoints.
    """
    return jsonify({
        "status": "ok",
        "ingest_available": INGEST_AVAILABLE
    }), 200


@admin_bp.route('/admin/status', methods=['GET'])
def admin_status():
    try:
        books = _load_metadata_list()
        embedder = GeminiEmbedder()
        dimension = len(embedder.embed_text("test"))

        summary_total = 0
        fulltext_total = 0
        summary_active = 0
        fulltext_active = 0

        if SUMMARY_INDEX_PATH.exists():
            summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dimension)
            summary_total = summary_store.index.ntotal
            summary_active = summary_store.total_active()

        if FULLTEXT_INDEX_PATH.exists():
            fulltext_store = FulltextVectorStore(FULLTEXT_INDEX_PATH, dimension=dimension)
            fulltext_total = fulltext_store.index.ntotal
            fulltext_active = fulltext_store.total_active()

        return jsonify({
            "status": "ok",
            "books_count": len(books),
            "summary_index_total": summary_total,
            "summary_index_active": summary_active,
            "fulltext_index_total": fulltext_total,
            "fulltext_index_active": fulltext_active,
            "ingest_available": INGEST_AVAILABLE
        }), 200
    except Exception as e:
        logger.error(f"Failed to get admin status: {e}", exc_info=True)
        return jsonify({"error": "Failed to get admin status"}), 500


@admin_bp.route('/admin/add', methods=['POST'])
def admin_add_book():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    summary = (data.get("summary") or "").strip()
    raw_metadata = data.get("metadata")

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not summary:
        return jsonify({"error": "Summary is required"}), 400

    metadata_dict = _parse_metadata_field(raw_metadata) or {}
    book_id = data.get("book_id") or metadata_dict.get("book_id") or str(uuid.uuid4())[:16]

    book_data = {
        "book_id": book_id,
        "judul_buku": title,
        "title": title,
        "summary_text": summary
    }
    book_data.update(metadata_dict)

    try:
        pdf_path = book_data.get("pdf_path") or book_data.get("link_pdf")
        if pdf_path and ADD_BOOK_AVAILABLE:
            success = add_new_book(book_data, interactive=False, override_summary=summary)
            if not success:
                return jsonify({"error": "Failed to add book with PDF ingestion"}), 500
            return jsonify({
                "status": "ok",
                "message": "Book added with full ingestion",
                "book_id": book_id
            }), 201

        _add_summary_only_book(book_data)
        return jsonify({
            "status": "ok",
            "message": "Book added to summary index only (no PDF provided)",
            "book_id": book_id
        }), 201
    except Exception as e:
        logger.error(f"Failed to add book: {e}", exc_info=True)
        return jsonify({"error": "Failed to add book"}), 500


@admin_bp.route('/admin/update/<book_id>', methods=['PUT'])
def admin_update_book(book_id):
    if not UPDATE_BOOK_AVAILABLE:
        return jsonify({"error": "Update function not available"}), 500

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    summary = (data.get("summary") or "").strip()
    raw_metadata = data.get("metadata")

    metadata_dict = _parse_metadata_field(raw_metadata) or {}
    new_metadata = {}
    new_metadata.update(metadata_dict)

    if title:
        new_metadata["judul_buku"] = title
        new_metadata["title"] = title
    if summary:
        new_metadata["summary_text"] = summary

    try:
        success = update_book_metadata(book_id, new_metadata)
        if not success:
            return jsonify({"error": "Failed to update book"}), 500
        return jsonify({
            "status": "ok",
            "message": "Book updated",
            "book_id": book_id
        }), 200
    except Exception as e:
        logger.error(f"Failed to update book {book_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update book"}), 500


@admin_bp.route('/admin/delete/<book_id>', methods=['DELETE'])
def admin_delete_book(book_id):
    if not DELETE_BOOK_AVAILABLE:
        return jsonify({"error": "Delete function not available"}), 500

    try:
        success = delete_book(book_id)
        if not success:
            return jsonify({"error": "Failed to delete book"}), 500
        return jsonify({
            "status": "ok",
            "message": "Book deleted",
            "book_id": book_id
        }), 200
    except Exception as e:
        logger.error(f"Failed to delete book {book_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete book"}), 500


# Optional: Endpoint to check ingestion status (if you want to track)
# For simplicity, not implemented here; could be extended with a global flag.