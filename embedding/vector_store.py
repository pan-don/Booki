"""
Vector store using FAISS for efficient similarity search.
Supports two indices: summary (one vector per book) and fulltext (vectors per chunk).
Manages metadata mapping (ID -> book_id, chunk_id, text, etc.) with soft delete.
"""

import os
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import logging

import faiss

from config.settings import EMBEDDING_MODEL  # for dimension detection? We'll get from first vector
from utils.logger import get_logger
from utils.file_utils import read_pickle, write_pickle

logger = get_logger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector store with metadata mapping and soft delete.
    
    Attributes:
        index: FAISS index (FlatIP or FlatL2)
        dimension: Embedding dimension (auto-set on first add)
        id_to_meta: dict mapping internal int id -> metadata dict
        next_id: int counter for next available id
        deleted_ids: set of ids marked as deleted (soft delete)
        index_path: path to save/load FAISS index
        meta_path: path to save/load metadata mapping
    """
    
    def __init__(
        self,
        index_path: Union[str, Path],
        dimension: Optional[int] = None,
        metric: str = "cosine",
        use_gpu: bool = False
    ):
        """
        Initialize FAISS vector store.
        
        Args:
            index_path: Path to save/load FAISS index file (.faiss).
            dimension: Embedding dimension (required when creating new index).
            metric: Distance metric ('cosine' or 'l2').
            use_gpu: Whether to use GPU (currently only CPU supported for HF Spaces compatibility).
        """
        self.index_path = Path(index_path)
        self.meta_path = self.index_path.with_suffix(".meta.pkl")
        self.dimension = dimension
        self.metric = metric
        self.use_gpu = use_gpu
        
        # Load or create index
        if self.index_path.exists():
            self._load()
        else:
            self._create_new_index()
        
        logger.info(f"FAISSVectorStore initialized at {index_path}, current size={self.index.ntotal}")
    
    def _create_new_index(self):
        """Create a new FAISS index."""
        if self.dimension is None:
            raise ValueError("Dimension must be provided when creating a new index")
        
        if self.metric == "cosine":
            # For cosine similarity, we can use inner product on normalized vectors
            self.index = faiss.IndexFlatIP(self.dimension)
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
        
        self.id_to_meta = {}
        self.next_id = 0
        self.deleted_ids = set()
        
        # For cosine, we'll normalize vectors before adding/searching
        logger.info(f"Created new FAISS index with dimension {self.dimension}, metric={self.metric}")
    
    def _load(self):
        """Load existing index and metadata from disk."""
        # Load FAISS index
        self.index = faiss.read_index(str(self.index_path))
        self.dimension = self.index.d
        
        # Load metadata
        if self.meta_path.exists():
            data = read_pickle(self.meta_path)
            self.id_to_meta = data.get('id_to_meta', {})
            self.next_id = data.get('next_id', 0)
            self.deleted_ids = set(data.get('deleted_ids', []))
        else:
            # No metadata, initialize empty
            self.id_to_meta = {}
            self.next_id = 0
            self.deleted_ids = set()
            logger.warning(f"Meta file {self.meta_path} not found, starting with empty metadata")
        
        # Validate consistency: number of vectors in index should match non-deleted ids
        active_count = self.index.ntotal
        meta_count = sum(1 for mid in self.id_to_meta if mid not in self.deleted_ids)
        if active_count != meta_count:
            logger.warning(f"Inconsistency: index has {active_count} vectors but metadata has {meta_count} active entries")
        logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors, {len(self.id_to_meta)} total metadata, {len(self.deleted_ids)} deleted")
    
    def _save(self):
        """Save index and metadata to disk."""
        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))
        # Save metadata
        meta_data = {
            'id_to_meta': self.id_to_meta,
            'next_id': self.next_id,
            'deleted_ids': list(self.deleted_ids)
        }
        write_pickle(self.meta_path, meta_data)
        logger.debug(f"Saved vector store to {self.index_path}")
    
    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors for cosine similarity (in-place)."""
        if self.metric == "cosine":
            faiss.normalize_L2(vectors)
        return vectors
    
    def add_vectors(
        self,
        vectors: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Add vectors to the store.
        
        Args:
            vectors: List of embedding vectors.
            metadatas: List of metadata dicts for each vector (must include at least 'book_id').
        
        Returns:
            List of assigned IDs for each vector.
        """
        if len(vectors) != len(metadatas):
            raise ValueError("Number of vectors and metadatas must match")
        
        if len(vectors) == 0:
            return []
        
        # Convert to numpy array
        vec_array = np.array(vectors, dtype=np.float32)
        if self.metric == "cosine":
            vec_array = self._normalize(vec_array)
        
        # Generate IDs
        ids = list(range(self.next_id, self.next_id + len(vectors)))
        
        # Add to FAISS
        self.index.add(vec_array)
        
        # Store metadata
        for idx, (vid, meta) in enumerate(zip(ids, metadatas)):
            # Ensure required fields
            if 'book_id' not in meta:
                meta['book_id'] = f"unknown_{vid}"
            self.id_to_meta[vid] = meta
        
        self.next_id += len(vectors)
        self._save()
        
        logger.info(f"Added {len(vectors)} vectors, new total={self.index.ntotal}, next_id={self.next_id}")
        return ids
    
    def search(
        self,
        query_vector: List[float],
        k: int = 10,
        filter_book_ids: Optional[List[str]] = None,
        exclude_deleted: bool = True
    ) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        """
        Search for nearest neighbors.
        
        Args:
            query_vector: Query embedding.
            k: Number of results to return.
            filter_book_ids: If provided, only return vectors whose book_id is in this list.
            exclude_deleted: If True, skip deleted entries.
        
        Returns:
            Tuple of (ids, distances, metadatas) for top-k results.
        """
        if self.index.ntotal == 0:
            return [], [], []
        
        # Prepare query vector
        q = np.array([query_vector], dtype=np.float32)
        if self.metric == "cosine":
            self._normalize(q)
            
        # Search more than k to allow filtering
        search_k = k * 5 if filter_book_ids else k
        distances, indices = self.index.search(q, search_k)
        
        # Collect results
        ids = []
        scores = []
        metadatas = []
        
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            if idx not in self.id_to_meta:
                continue
            if exclude_deleted and idx in self.deleted_ids:
                continue
            meta = self.id_to_meta[idx]
            if filter_book_ids and meta.get('book_id') not in filter_book_ids:
                continue
            # Convert distance to similarity score (cosine: higher is better, L2: lower is better)
            score = float(dist) if self.metric == "cosine" else 1.0 / (1.0 + float(dist))
            ids.append(int(idx))
            scores.append(score)
            metadatas.append(meta)
            if len(ids) >= k:
                break
        
        logger.debug(f"Search returned {len(ids)} results (k={k}, filter={filter_book_ids is not None})")
        return ids, scores, metadatas
    
    def delete_vectors(self, ids: List[int]) -> int:
        """
        Soft delete vectors by ID (mark as deleted). 
        Does not physically remove from FAISS index to avoid expensive rebuild.
        
        Args:
            ids: List of vector IDs to delete.
        
        Returns:
            Number of IDs successfully marked deleted.
        """
        count = 0
        for vid in ids:
            if vid in self.id_to_meta and vid not in self.deleted_ids:
                self.deleted_ids.add(vid)
                count += 1
        self._save()
        logger.info(f"Soft deleted {count} vectors")
        return count
    
    def delete_by_book_id(self, book_id: str) -> int:
        """Delete all vectors associated with a given book_id."""
        ids_to_delete = [
            vid for vid, meta in self.id_to_meta.items()
            if meta.get('book_id') == book_id and vid not in self.deleted_ids
        ]
        return self.delete_vectors(ids_to_delete)
    
    def update_vector(self, vector_id: int, new_vector: List[float], new_metadata: Dict[str, Any]):
        """
        Update a vector and its metadata (requires rebuild of index entry).
        FAISS does not support in-place update, so we add a new vector and soft delete the old one.
        
        Args:
            vector_id: ID of vector to replace.
            new_vector: New embedding.
            new_metadata: New metadata.
        
        Returns:
            New ID of the updated vector.
        """
        # Soft delete old
        self.delete_vectors([vector_id])
        # Add new
        new_ids = self.add_vectors([new_vector], [new_metadata])
        logger.info(f"Updated vector {vector_id} -> new id {new_ids[0]}")
        return new_ids[0]
    
    def get_vector(self, vector_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a vector ID if not deleted."""
        if vector_id in self.deleted_ids:
            return None
        return self.id_to_meta.get(vector_id)
    
    def total_active(self) -> int:
        """Number of active (non-deleted) vectors."""
        return self.index.ntotal - len(self.deleted_ids)
    
    def rebuild(self, force: bool = False):
        """
        Rebuild the FAISS index by removing soft-deleted vectors.
        Call this periodically to clean up.
        """
        # Implement force flag checking
        if not force and len(self.deleted_ids) < self.index.ntotal * 0.1:
            logger.info("Skipping rebuild because deleted count < 10%")
            return
            
        # Collect active vectors and metadata
        active_ids = [vid for vid in self.id_to_meta if vid not in self.deleted_ids]
        
        # We need to retrieve actual vectors from somewhere. Option: store vectors? Not stored.
        # To rebuild, we'd need to recompute embeddings. Instead, we can just keep soft delete.
        # For simplicity, we warn that rebuild is not implemented without storing vectors.
        logger.warning("Rebuild requires storing original vectors or recomputing. Not implemented.")
        raise NotImplementedError("Rebuild requires access to original vectors or recomputed embeddings.")


class SummaryVectorStore(FAISSVectorStore):
    """Specialized store for summary vectors (one per book)."""
    def __init__(self, index_path: Path, dimension: int):
        super().__init__(index_path, dimension=dimension, metric="cosine")
    
    def add_book_summary(self, book_id: str, title: str, summary_text: str, vector: List[float]) -> int:
        """Add a single book summary."""
        meta = {
            'book_id': book_id,
            'title': title,
            'text': summary_text,  # the summary itself
            'type': 'summary'
        }
        ids = self.add_vectors([vector], [meta])
        return ids[0]


class FulltextVectorStore(FAISSVectorStore):
    """Specialized store for fulltext chunks."""
    def __init__(self, index_path: Path, dimension: int):
        super().__init__(index_path, dimension=dimension, metric="cosine")
    
    def add_chunks(self, book_id: str, chunks: List[Dict[str, Any]], vectors: List[List[float]]) -> List[int]:
        """
        Add multiple chunks from a book.
        Each chunk dict should contain 'text', 'start', 'end', 'index', etc.
        """
        metadatas = []
        for chunk in chunks:
            meta = {
                'book_id': book_id,
                'chunk_text': chunk.get('text', ''),
                'chunk_index': chunk.get('index'),
                'start_char': chunk.get('start'),
                'end_char': chunk.get('end'),
                'type': 'fulltext'
            }
            # Add any extra metadata from chunk
            for k, v in chunk.items():
                if k not in meta:
                    meta[k] = v
            metadatas.append(meta)
        
        return self.add_vectors(vectors, metadatas)