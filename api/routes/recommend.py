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
        
        # Extract metadata filters from request payload if present
        filter_jenjang = data.get('filter_jenjang', None)
        filter_kelas = data.get('filter_kelas', None)
        filter_mapel = data.get('filter_mapel', None)

        # 1. Embed query
        query_vector = embedder.embed_text(user_query)
        if not query_vector:
            logger.error("Failed to embed query")
            return jsonify({"status": "error", "error": "Embedding failed"}), 500
        
        # 2. Retrieve top-k summaries (top_k parameter is internal to retriever now but we call search_summary)
        summary_results = retriever.search_summary(
            query=user_query,
            query_vector=query_vector,
            filter_jenjang=filter_jenjang,
            filter_kelas=filter_kelas,
            filter_mapel=filter_mapel
        )
        
        if not summary_results:
            logger.warning("No summary results found")
            return jsonify({
                "status": "success",
                "query": user_query,
                "recommendations": [],
                "answer": "Maaf ya teman, aku tidak menemukan buku pelajaran yang cocok dengan kriteria filter tersebut. Yuk, coba sesuaikan filternya atau tanyakan topik pelajaran yang lain! 📚✨"
            }), 200
        
        # 3. Rerank results
        reranked_results = reranker.rerank_results(
            query=user_query,
            retrieval_results=summary_results,
            text_field='summary_text'
        )
        
        # 4. Dynamically filter by relevance score threshold instead of hard slicing top 5
        RELEVANCE_THRESHOLD = 0.60
        valid_recommendations = [
            {
                "book_id": item["book_id"],
                "title": item["title"],
                "author": item.get("author", "Anonim"),
                "jenjang": item.get("metadata", {}).get("jenjang", "Umum"),
                "kelas": item.get("metadata", {}).get("kelas", []),
                "mata_pelajaran": item.get("metadata", {}).get("mata_pelajaran", "Umum"),
                "summary": item["summary_text"],
                "cover_image": item.get("metadata", {}).get("link_sampul", ""),
                "similarity_score": float(item["score"]),
                "relevance_score": float(item.get("rerank_score", item.get("score", 0)))
            }
            for item in reranked_results if item.get("rerank_score", item.get("score", 0)) >= RELEVANCE_THRESHOLD
        ]
        
        # 5. Generate pure narrative chat response without repetitive list formatting
        if valid_recommendations:
            llm_answer = answer_generator.generate_recommendation(
                user_query=user_query,
                retrieved_books=valid_recommendations
            )
        else:
            llm_answer = "Aku menemukan beberapa materi terkait di perpustakaan, tetapi tingkat kecocokannya masih di bawah standar optimal belajar kamu. Coba berikan pertanyaan yang lebih spesifik ya, Sobat Belajar! 😊✨"
        
        logger.info(f"Returning {len(valid_recommendations)} recommendations")
        return jsonify({
            "status": "success",
            "query": user_query,
            "recommendations": valid_recommendations,
            "answer": llm_answer
        }), 200
        
    except Exception as e:
        logger.error(f"Internal server error inside /recommend route: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "error": "Internal server error execution failure"}), 500