"""
Flask application factory and global component initialization.
Loads vector stores, retriever, reranker, answer generator, and registers blueprints.
"""

import sys
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from utils.file_utils import stream_jsonl
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    SUMMARY_INDEX_PATH, FULLTEXT_INDEX_PATH
)
from utils.logger import configure_root_logger, get_logger
from embedding.vector_store import SummaryVectorStore, FulltextVectorStore
from embedding.embedder import GeminiEmbedder
from retrieval.retriever import Retriever
from retrieval.reranker import Reranker
from generation.answer_generator import AnswerGenerator

# Configure root logger once
configure_root_logger(log_file=Path("logs/api.log"), level=20)  # INFO
logger = get_logger(__name__)


def create_app() -> Flask:
    """
    Application factory for Flask.
    Loads all global components and registers blueprints.
    """
    app = Flask(__name__)
    
    # Enable CORS for frontend (Cloudflare)
    CORS(app, origins=["*"])  # Sesuaikan dengan domain frontend nanti
    
    # ---------------- Load Global Components ----------------
    try:
        logger.info("Initializing global components...")
        
        # Embedder
        embedder = GeminiEmbedder()
        logger.info("GeminiEmbedder initialized")
        
        # For testing/mocking, just use default dimension to bypass API requirements
        from config.settings import EMBEDDING_DIM
        dimension = EMBEDDING_DIM
        logger.info(f"Embedding dimension (mocked/default): {dimension}")
        
        # Vector stores
        summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dimension)
        logger.info(f"Summary store loaded from {SUMMARY_INDEX_PATH}, size={summary_store.index.ntotal}")
        
        fulltext_store = FulltextVectorStore(FULLTEXT_INDEX_PATH, dimension=dimension)
        logger.info(f"Fulltext store loaded from {FULLTEXT_INDEX_PATH}, size={fulltext_store.index.ntotal}")
        
        # Retriever
        retriever = Retriever(summary_store, fulltext_store)
        
        # Reranker (Jina AI)
        reranker = Reranker()
        
        # Answer generator
        answer_generator = AnswerGenerator()
        
        # Store components in app config (or app.extensions) for use in routes
        app.config['embedder'] = embedder
        app.config['retriever'] = retriever
        app.config['reranker'] = reranker
        app.config['answer_generator'] = answer_generator
        
        logger.info("All global components loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize global components: {e}", exc_info=True)
        raise
    
    # ---------------- Register Blueprints ----------------
    from api.routes.recommend import recommend_bp
    from api.routes.deep import deep_bp
    from api.routes.admin import admin_bp
    
    app.register_blueprint(recommend_bp, url_prefix='/api')
    app.register_blueprint(deep_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    # Alias routes without /api to avoid 404 when frontend hits root paths
    app.register_blueprint(recommend_bp, name="recommend_root")
    app.register_blueprint(deep_bp, name="deep_root")
    app.register_blueprint(admin_bp, name="admin_root")
    
    # ---------------- Health Check Endpoint ----------------
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy", "message": "RAG system is running"}), 200

    @app.route('/api/health', methods=['GET'])
    def health_check_api():
        return jsonify({"status": "healthy", "message": "RAG system is running"}), 200
    
    # ---------------- Global Error Handlers ----------------
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    book_metadata_map = {}
    content_books_path = Path("data/metadata/content_books.jsonl")
    if content_books_path.exists():
        try:
            for book in stream_jsonl(content_books_path):
                book_id = book.get('book_id')
                if book_id:
                    book_metadata_map[book_id] = book
            logger.info(f"Loaded {len(book_metadata_map)} book metadata entries from {content_books_path}")
        except Exception as e:
            logger.error(f"Failed to load book metadata: {e}")
    else:
        logger.warning(f"Content books file not found: {content_books_path}")

    app.config['book_metadata_map'] = book_metadata_map
    
    return app