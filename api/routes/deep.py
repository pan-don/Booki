"""
Endpoint for deep dive questions into selected books.
Retrieves chunks from fulltext FAISS with book_id filter, reranks, and generates detailed answer.
"""

from flask import Blueprint, request, jsonify, current_app
from typing import List, Dict, Any
import logging

from utils.logger import get_logger

logger = get_logger(__name__)
deep_bp = Blueprint('deep', __name__)


@deep_bp.route('/deep', methods=['POST'])
def deep_dive():
    """
    Receive selected book_ids and a question, return detailed answer from book content.
    Expected JSON: {"book_ids": ["book_123", "book_456"], "question": "Apa rumus gaya sentripetal?"}
    """
    try:
        data = request.get_json()
        if not data or 'book_ids' not in data or 'question' not in data:
            return jsonify({"error": "Missing 'book_ids' or 'question' field"}), 400
        
        book_ids = data['book_ids']
        question = data['question'].strip()
        
        # Validate book_ids: 1 to 5 books
        if not isinstance(book_ids, list) or len(book_ids) < 1 or len(book_ids) > 5:
            return jsonify({"error": "book_ids must be a list with 1 to 5 items"}), 400
        
        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400
        
        logger.info(f"Deep dive question: {question} | Books: {book_ids}")
        
        # Get global components
        embedder = current_app.config['embedder']
        retriever = current_app.config['retriever']
        reranker = current_app.config['reranker']
        answer_generator = current_app.config['answer_generator']
        
        # Optional: get book metadata map (if loaded in app.config)
        book_metadata_map = current_app.config.get('book_metadata_map', {})
        
        # 1. Embed question
        query_vector = embedder.embed_text(question)
        if not query_vector:
            logger.error("Failed to embed question")
            return jsonify({"error": "Embedding failed"}), 500
        
        # 2. Retrieve chunks only from selected book_ids (top 20 per query)
        RETRIEVAL_K = 20
        chunk_results = retriever.search_fulltext_by_book_ids(
            query=question,
            query_vector=query_vector,
            book_ids=book_ids,
            top_k=RETRIEVAL_K
        )
        
        if not chunk_results:
            # No relevant chunks found
            book_titles = [book_metadata_map.get(bid, {}).get('title', bid) for bid in book_ids]
            answer = f"Wah, saya belum menemukan informasi tentang pertanyaanmu di dalam buku {', '.join(book_titles)}. Coba tanyakan hal lain atau pilih buku yang berbeda ya! 😊"
            return jsonify({
                "answer": answer,
                "sources": []
            }), 200
        
        # 3. Rerank chunks (top 5)
        RERANK_TOP_N = 5
        reranked_chunks = reranker.rerank_results(
            query=question,
            retrieval_results=chunk_results,
            text_field='chunk_text',
            top_n=RERANK_TOP_N
        )
        
        # 4. Prepare selected books metadata for answer generator
        selected_books = []
        for bid in book_ids:
            if bid in book_metadata_map:
                selected_books.append(book_metadata_map[bid])
            else:
                # Fallback: create minimal metadata from first chunk if available
                for chunk in reranked_chunks:
                    if chunk.get('book_id') == bid:
                        selected_books.append({
                            'book_id': bid,
                            'title': chunk.get('title', bid),
                        })
                        break
                else:
                    selected_books.append({'book_id': bid, 'title': bid})
        
        # 5. Generate detailed answer
        answer = answer_generator.generate_deep_answer(
            user_question=question,
            selected_books=selected_books,
            retrieved_chunks=reranked_chunks
        )
        
        # 6. Prepare sources (chunks) for response
        sources = []
        for chunk in reranked_chunks:
            source = {
                "book_id": chunk.get('book_id'),
                "title": chunk.get('title'),
                "chunk_text": chunk.get('chunk_text')[:500],  # potongan
                "chunk_index": chunk.get('chunk_index'),
                "page": chunk.get('page'),
                "relevance_score": chunk.get('rerank_score', chunk.get('score', 0))
            }
            sources.append(source)
        
        logger.info(f"Deep dive answer generated with {len(sources)} sources")
        return jsonify({
            "answer": answer,
            "sources": sources
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /deep: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500