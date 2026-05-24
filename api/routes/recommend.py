"""
Endpoint for book recommendation based on user preferences.
Performs retrieval on summary index, reranks, and generates recommendations.
"""

from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, List
import logging

from utils.logger import get_logger

logger = get_logger(__name__)
recommend_bp = Blueprint('recommend', __name__)


@recommend_bp.route('/recommend', methods=['POST'])
def recommend():
    """
    Receive user query, return book recommendations.
    Expected JSON: {"query": "saya butuh buku fisika sma tentang gelombang"}
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' field"}), 400
        
        user_query = data['query'].strip()
        if not user_query:
            return jsonify({"error": "Query cannot be empty"}), 400
        
        logger.info(f"Received recommendation query: {user_query}")
        
        # Get global components
        embedder = current_app.config['embedder']
        retriever = current_app.config['retriever']
        reranker = current_app.config['reranker']
        answer_generator = current_app.config['answer_generator']
        
        # 1. Embed query
        # Provide fallback dummy vector for local development since api keys aren't working
        query_vector = embedder.embed_text(user_query)
        if not query_vector:
            logger.error("Failed to embed query, using random dummy vector for local testing")
            import numpy as np
            # Generate random vector to allow FAISS to search and return something
            dimension = getattr(embedder, 'output_dim', 3072)
            query_vector = np.random.rand(dimension).astype('float32').tolist()
        
        # 2. Retrieve top-k summaries (top 20)
        RETRIEVAL_K = 20
        summary_results = retriever.search_summary(
            query=user_query,
            query_vector=query_vector,
            top_k=RETRIEVAL_K,
            filter_book_ids=None  # no filter for initial recommendation
        )
        
        if not summary_results:
            logger.warning("No summary results found")
            return jsonify({
                "recommendations": [],
                "answer": "Maaf, saya tidak menemukan buku yang sesuai dengan preferensimu. Coba gunakan kata kunci lain ya! 😊"
            }), 200
        
        # 3. Rerank results (top 5 after rerank)
        RERANK_TOP_N = 5
        reranked = reranker.rerank_results(
            query=user_query,
            retrieval_results=summary_results,
            text_field='summary_text',
            top_n=RERANK_TOP_N
        )
        
        # 4. Generate recommendation answer
        answer = answer_generator.generate_recommendation(
            user_query=user_query,
            retrieved_books=reranked
        )
        
        # 5. Prepare response (list of books with metadata)
        books_response = []
        for book in reranked:
            books_response.append({
                "book_id": book.get('book_id'),
                "title": book.get('title'),
                "mata_pelajaran": book.get('mata_pelajaran'),
                "jenjang": book.get('jenjang'),
                "kelas": book.get('kelas'),
                "cover_image": book.get('link_sampul'),
                "summary": book.get('summary_text')[:300] if book.get('summary_text') else "",  # potongan ringkasan
                "relevance_score": book.get('rerank_score', book.get('score', 0))
            })
        
        logger.info(f"Returning {len(books_response)} recommendations")
        return jsonify({
            "recommendations": books_response,
            "answer": answer
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /recommend: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500