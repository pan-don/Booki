"""
Reranker module using Jina AI API.
Takes a query and a list of documents, returns reranked documents with relevance scores.
"""

import requests
from typing import List, Dict, Any, Optional
import logging

from config.settings import JINA_API_KEY, JINA_RERANK_MODEL, JINA_API_URL
from utils.api_key_manager import APIKeyManager
from utils.logger import get_logger

logger = get_logger(__name__)


class Reranker:
    """
    Reranks documents using Jina AI's reranking API.
    
    Attributes:
        api_key_manager: Manages API keys (useful if multiple keys are added later).
        model: Name of the reranker model.
        api_url: Endpoint URL for Jina rerank API.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = JINA_RERANK_MODEL,
        api_url: str = JINA_API_URL
    ):
        """
        Initialize reranker.
        
        Args:
            api_key: Jina API key (if None, uses from settings).
            model: Reranker model name.
            api_url: API endpoint URL.
        """
        key = api_key or JINA_API_KEY
        if not key:
            raise ValueError("JINA_API_KEY is not set in environment or config")
    
        self.api_key_manager = APIKeyManager([key], service_name="Jina")
        self.model = model
        self.api_url = api_url
        logger.info(f"Reranker initialized with model {model}")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on relevance to the query.
        
        Args:
            query: User query string.
            documents: List of document texts to rerank.
            top_n: Maximum number of top documents to return. If None, returns all.
        
        Returns:
            List of dictionaries sorted by relevance (highest first), each containing:
                - 'index': original index in input list
                - 'text': document text
                - 'relevance_score': float score from reranker (higher = more relevant)
        """
        if not documents:
            logger.warning("No documents provided for reranking")
            return []
    
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": top_n if top_n is not None else len(documents)
        }
        headers = {
            "Authorization": f"Bearer {self.api_key_manager.get_current_key()}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            reranked = []
            for res in results:
                idx = res["index"]
                reranked.append({
                    "index": idx,
                    "text": documents[idx],
                    "relevance_score": res.get("relevance_score", 0.0)
                })
            
            logger.info(f"Reranked {len(documents)} documents, returned {len(reranked)}")
            return reranked
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Jina rerank API request failed: {e}")
            fallback = [
                {"index": i, "text": doc, "relevance_score": 0.0}
                for i, doc in enumerate(documents)
            ]
            return fallback[:top_n] if top_n else fallback
    
    def rerank_results(
        self,
        query: str,
        retrieval_results: List[Dict[str, Any]],
        text_field: str = "summary_text",
        top_n: Optional[int] = None,
        threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to rerank results from a retriever with threshold logic.
        
        Args:
            query: User query.
            retrieval_results: List of result dicts from Retriever (must contain the text field).
            text_field: Name of the field containing the document text.
            top_n: Maximum number to return after reranking.
            threshold: Relevance score threshold (0.0 to 1.0).
        
        Returns:
            The reranked list of result dicts passing threshold (min 2 results).
        """
        if not retrieval_results:
            return []
    
        documents = [item.get(text_field, "") for item in retrieval_results]
        reranked = self.rerank(query, documents, top_n=None) # get all to filter by threshold
    
        merged = []
        for r in reranked:
            original = retrieval_results[r["index"]].copy()
            original["rerank_score"] = r["relevance_score"]
            merged.append(original)
            
        # Apply Threshold Logic
        valid_results = [m for m in merged if m["rerank_score"] >= threshold]
        
        # If no results meet the threshold, fallback to top 2
        if not valid_results:
            logger.warning(f"No results met threshold {threshold}. Falling back to top 2.")
            valid_results = merged[:2]
            
        return valid_results[:top_n] if top_n else valid_results