"""
Retriever module for querying FAISS vector stores.
Supports two indices: summary (per book) and fulltext (per chunk).
Returns results with scores and metadata.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from rank_bm25 import BM25Okapi

from embedding.vector_store import FAISSVectorStore
from utils.logger import get_logger

logger = get_logger(__name__)

def _tokenize(text: str) -> List[str]:
    """Helper method to tokenize text for BM25."""
    return text.lower().split()


class Retriever:
    """
    Retrieves relevant items from FAISS vector stores.
    
    Attributes:
        summary_store: FAISSVectorStore for book summaries.
        fulltext_store: FAISSVectorStore for text chunks.
    """
    
    def __init__(
        self,
        summary_store: FAISSVectorStore,
        fulltext_store: FAISSVectorStore
    ):
        """
        Initialize retriever with the two vector stores.
        
        Args:
            summary_store: Vector store containing book summaries (one vector per book).
            fulltext_store: Vector store containing text chunks.
        """
        self.summary_store = summary_store
        self.fulltext_store = fulltext_store
        logger.info("Retriever initialized")

    def _extract_filters_from_query(self, query: str) -> Dict[str, List[str]]:
        """
        Robust metadata post-filtering extractor using Indonesian keywords.
        """
        query_lower = query.lower()
        filters = {"jenjang": [], "kelas": [], "mata_pelajaran": []}
        
        # 1. Jenjang (SD/MI, SMP/MTs, SMA/MA/SMK)
        if any(w in query_lower for w in ["sd", "sekolah dasar", "mi", "madrasah ibtidaiyah"]):
            filters["jenjang"].append("SD/MI")
        if any(w in query_lower for w in ["smp", "sekolah menengah pertama", "mts", "madrasah tsanawiyah"]):
            filters["jenjang"].append("SMP/MTs")
        if any(w in query_lower for w in ["sma", "smk", "sekolah menengah atas", "sekolah menengah kejuruan", "ma", "madrasah aliyah"]):
            filters["jenjang"].append("SMA/MA/SMK/MAK")

        # 2. Kelas (1 - 12)
        for class_int, class_roman in [
            (1, "I"), (2, "II"), (3, "III"), (4, "IV"), (5, "V"), (6, "VI"),
            (7, "VII"), (8, "VIII"), (9, "IX"), (10, "X"), (11, "XI"), (12, "XII")
        ]:
            if (f"kelas {class_int}" in query_lower or 
                f"kelas {class_roman.lower()} " in query_lower or
                query_lower.endswith(f"kelas {class_roman.lower()}")):
                filters["kelas"].extend([str(class_int), class_roman])
                
        # 3. Mata Pelajaran (Contoh robust keywords bahasa Indonesia)
        mapel_keywords = {
            "matematika": ["matematika", "mtk", "hitung"],
            "ipa": ["ipa", "sains", "ilmu pengetahuan alam", "biologi", "fisika", "kimia"],
            "ips": ["ips", "ilmu pengetahuan sosial", "sejarah", "geografi", "sosiologi", "ekonomi"],
            "bahasa indonesia": ["bahasa indonesia", "b.indo", "b indo", "indonesia"],
            "bahasa inggris": ["bahasa inggris", "b.inggris", "b.ing", "b inggris", "english"],
            "pkn": ["pkn", "pancasila", "pendidikan kewarganegaraan", "ppkn"],
            "agama islam": ["agama islam", "pai", "islam", "pendidikan agama islam"],
            "agama kristen": ["agama kristen", "kristen"],
            "seni budaya": ["seni budaya", "sbk", "seni", "budaya"],
            "pjok": ["pjok", "penjas", "olahraga"],
            "prakarya": ["prakarya", "kewirausahaan", "karya"]
        }
        for mapel_std, keywords in mapel_keywords.items():
            if any(kw in query_lower for kw in keywords):
                filters["mata_pelajaran"].append(mapel_std)

        return filters

    def _apply_metadata_filters(self, results: List[Dict[str, Any]], extracted_filters: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Applies exact or partial metadata matching on retrieval results."""
        filtered_results = []
        for res in results:
            meta = res.get('metadata', {})
            
            # Match Jenjang
            req_jenjangs = extracted_filters["jenjang"]
            meta_jenjang = str(meta.get("jenjang", "")).upper()
            if req_jenjangs and not any(r_jenjang.upper() in meta_jenjang for r_jenjang in req_jenjangs):
                continue
                
            # Match Kelas
            req_kelass = extracted_filters["kelas"]
            meta_kelas = str(meta.get("kelas", "")).upper()
            meta_kelas_parts = meta_kelas.replace("/", " ").split()
            if req_kelass and not any(r_kelas.upper() in meta_kelas_parts for r_kelas in req_kelass):
                continue
                
            # Match Mapel
            req_mapels = extracted_filters["mata_pelajaran"]
            meta_mapel = str(meta.get("mata_pelajaran", "")).lower()
            if req_mapels and not any(r_mapel.lower() in meta_mapel for r_mapel in req_mapels):
                continue
                
            filtered_results.append(res)
            
        return filtered_results
    
    def _compute_hybrid_scores(self, query: str, faiss_results: List[Dict[str, Any]], alpha: float = 0.5) -> List[Dict[str, Any]]:
        """
        Combines Semantic Score (FAISS) and Keyword Score (BM25) using Weighted Sum.
        final_score = alpha * normalized_faiss_score + (1 - alpha) * normalized_bm25_score
        """
        if not faiss_results:
            return []

        # Extract texts for BM25
        texts = [res.get('summary_text', res.get('chunk_text', '')) for res in faiss_results]
        tokenized_corpus = [_tokenize(t) for t in texts]
        
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = _tokenize(query)
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Normalize scores (Min-Max scaling to 0-1 range)
        faiss_scores = [res['score'] for res in faiss_results]
        
        def _normalize(scores):
            min_s, max_s = min(scores), max(scores)
            if max_s - min_s == 0:
                return [1.0] * len(scores) if max_s > 0 else [0.0] * len(scores)
            return [(s - min_s) / (max_s - min_s) for s in scores]
            
        norm_faiss = _normalize(faiss_scores)
        norm_bm25 = _normalize(bm25_scores)
        
        hybrid_results = []
        for i, res in enumerate(faiss_results):
            hybrid_score = (alpha * norm_faiss[i]) + ((1 - alpha) * norm_bm25[i])
            hybrid_res = res.copy()
            hybrid_res['score'] = hybrid_score
            hybrid_res['faiss_score'] = faiss_scores[i]
            hybrid_res['bm25_score'] = bm25_scores[i]
            hybrid_results.append(hybrid_res)
            
        # Re-sort based on hybrid score
        hybrid_results.sort(key=lambda x: x['score'], reverse=True)
        return hybrid_results

    def search_summary(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 10,
        filter_book_ids: Optional[List[str]] = None,
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search the summary index using Hybrid Search (FAISS + BM25) and Post-filtering.
        """
        if self.summary_store.index.ntotal == 0:
            logger.warning("Summary index is empty")
            return []
        
        # We retrieve more initially (e.g. 5x top_k) from FAISS to allow effective filtering & BM25 reranking
        initial_k = top_k * 5
        ids, scores, metadatas = self.summary_store.search(
            query_vector=query_vector,
            k=initial_k,
            filter_book_ids=filter_book_ids,
            exclude_deleted=True
        )
        
        results = []
        for idx, score, meta in zip(ids, scores, metadatas):
            results.append({
                'id': idx,
                'score': float(score),
                'book_id': meta.get('book_id', 'unknown'),
                'title': meta.get('title', 'Untitled'),
                'summary_text': meta.get('text', meta.get('summary_text', '')),
                'metadata': meta  
            })
            
        # 1. BM25 + FAISS Hybrid Rescoring
        results = self._compute_hybrid_scores(query, results, alpha=alpha)
            
        # 2. Post-Filtering based on query intent
        filters = self._extract_filters_from_query(query)
        if any(filters.values()):  # If any filters extracted
            filtered_results = self._apply_metadata_filters(results, filters)
            if filtered_results:
                results = filtered_results
            else:
                logger.warning("Post-filtering dropped all results, reverting to non-filtered hybrid results")
        
        logger.debug(f"Summary search returned {len(results[:top_k])} results (top_k={top_k})")
        return results[:top_k]
    
    def search_fulltext(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 10,
        filter_book_ids: Optional[List[str]] = None,
        alpha: float = 0.6 # slightly rely more on FAISS for chunks
    ) -> List[Dict[str, Any]]:
        """
        Search the fulltext (chunk) index using Hybrid Search (FAISS + BM25).
        """
        if self.fulltext_store.index.ntotal == 0:
            logger.warning("Fulltext index is empty")
            return []
        
        initial_k = top_k * 5
        ids, scores, metadatas = self.fulltext_store.search(
            query_vector=query_vector,
            k=initial_k,
            filter_book_ids=filter_book_ids,
            exclude_deleted=True
        )
        
        results = []
        for idx, score, meta in zip(ids, scores, metadatas):
            result = {
                'id': idx,
                'score': float(score),
                'book_id': meta.get('book_id', 'unknown'),
                'chunk_text': meta.get('chunk_text', meta.get('text', '')),
                'chunk_index': meta.get('chunk_index', -1),
                'start_char': meta.get('start_char'),
                'end_char': meta.get('end_char'),
                'metadata': meta
            }
            
            if 'page' in meta:
                result['page'] = meta['page']
            results.append(result)
            
        # BM25 + FAISS Hybrid Rescoring
        results = self._compute_hybrid_scores(query, results, alpha=alpha)
        
        logger.debug(f"Fulltext search returned {len(results[:top_k])} results (top_k={top_k})")
        return results[:top_k]
    
    def search_summary_by_book_ids(
        self,
        query: str,
        query_vector: List[float],
        book_ids: List[str],
        top_k: int = 10,
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Convenience method to search summary only among specific book IDs."""
        return self.search_summary(query, query_vector, top_k=top_k, filter_book_ids=book_ids, alpha=alpha)
    
    def search_fulltext_by_book_ids(
        self,
        query: str,
        query_vector: List[float],
        book_ids: List[str],
        top_k: int = 10,
        alpha: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Convenience method to search fulltext only among specific book IDs."""
        return self.search_fulltext(query, query_vector, top_k=top_k, filter_book_ids=book_ids, alpha=alpha)