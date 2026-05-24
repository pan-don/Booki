# LAYER EMBEDDING DAN VECTOR STORE

**Dokumentasi Teknis: Vector Embeddings dan FAISS-based Similarity Search**

---

## Ikhtisar

Layer ini bertanggung jawab untuk:
1. **Text-to-Vector Conversion**: Konversi teks ke dense vectors menggunakan embedding models
2. **Vector Indexing**: Penyimpanan vectors dalam FAISS untuk efficient similarity search
3. **Metadata Management**: Pemetaan vector IDs ke metadata (book_id, chunk_id, text, dll)
4. **Soft Delete Support**: Marking vectors as deleted tanpa menghapus dari index

---

## 📁 Folder: `embedding/`

**Fungsi**: Embedding generation dan vector store management untuk retrieval.

---

### File: `embedder.py`

**Tujuan**: Wrapper around Google Gemini Embedding API dengan key rotation dan retry logic.

#### Kelas: `GeminiEmbedder`

```python
class GeminiEmbedder:
    def __init__(
        self,
        key_manager: Optional[APIKeyManager] = None,
        model: str = "gemini-embedding-2",
        output_dim: int = 3072,
        max_retries: int = 3
    )
    
    def embed_text(
        self,
        text: str,
        task_type: Optional[str] = None
    ) -> Optional[List[float]]
```

**Initialization Parameters**:

| Parameter | Type | Default | Deskripsi |
|-----------|------|---------|-----------|
| `key_manager` | APIKeyManager | Auto-created | Manager untuk multiple API keys |
| `model` | str | `gemini-embedding-2` | Embedding model identifier |
| `output_dim` | int | `3072` | Output dimensionality dari embedding |
| `max_retries` | int | `3` | Max retry attempts per request |

**Key Methods**:

#### `embed_text(text, task_type=None) -> Optional[List[float]]`

**Fungsi**: Embed single text ke dense vector dengan automatic retry dan key rotation.

**Parameters**:
- `text` (str): Teks yang akan di-embed
- `task_type` (Optional[str]): Task type untuk embedding (`retrieval_document`, `retrieval_query`, `semantic_similarity`, dll)

**Return**: List of floats (embedding vector) atau None jika semua retries gagal

**Behavior**:
1. ✅ Skip jika text kosong
2. ✅ Create Gemini client dengan current API key
3. ✅ Call `models.embed_content()` dengan output dimensionality
4. ✅ Jika error:
   - Report error ke key_manager
   - Rotate ke key berikutnya
   - Retry dengan exponential backoff
5. ✅ Return embedding vector jika sukses, atau None setelah max_retries

**Contoh Usage**:
```python
embedder = GeminiEmbedder()

# Embed single query
query_vector = embedder.embed_text("Fisika gelombang SMA kelas X")
# Returns: [0.123, -0.456, 0.789, ..., 0.234]  (3072 dimensions)

# Embed dengan task type
summary_vector = embedder.embed_text(
    "Gelombang adalah... (ringkasan 400 kata)",
    task_type="retrieval_document"
)
```

**API Integration**:
```
Google Gemini Embedding API
- Model: gemini-embedding-2
- Endpoint: models.embed_content()
- Output Dimension: 3072
- Max tokens per request: ~10,000
- Rate limit: Tergantung quota API key
```

**Error Handling Strategy**:
```
Loop up to max_retries × num_keys attempts:
    try:
        embed_via_gemini()
        return embedding
    except Exception as e:
        report_error(current_key, error_msg)
        rotate_key()
        sleep(exponential_backoff)
        retry()

if all_attempts_fail:
    log_error()
    return None
```

**Performance Characteristics**:
- **Latency per request**: ~200-500ms (network-bound)
- **Throughput**: ~2-5 requests/second per API key
- **Total dimension**: 3072 (high-dimensional, good semantic representation)

---

#### `get_completed_ids(output_path) -> Set[str]`

**Fungsi**: Get set dari IDs yang sudah berhasil di-embed (untuk resume batch processing).

**Use Case**: Pada batch embedding besar, track progress dan resume jika interrupted.

---

### File: `vector_store.py`

**Tujuan**: FAISS-based vector store dengan metadata mapping dan soft delete support.

#### Kelas: `FAISSVectorStore`

```python
class FAISSVectorStore:
    """
    FAISS-based vector store dengan metadata mapping dan soft delete.
    
    Attributes:
        index: FAISS index (FlatIP atau FlatL2)
        id_to_meta: dict mapping internal int id -> metadata dict
        next_id: int counter untuk next available id
        deleted_ids: set of ids marked sebagai deleted (soft delete)
    """
    
    def __init__(
        self,
        index_path: Union[str, Path],
        dimension: Optional[int] = None,
        metric: str = "cosine",
        use_gpu: bool = False
    )
```

**Constructor Parameters**:

| Parameter | Type | Default | Deskripsi |
|-----------|------|---------|-----------|
| `index_path` | str \| Path | Required | Path untuk save/load FAISS index file |
| `dimension` | Optional[int] | None | Embedding dimensionality (required untuk new index) |
| `metric` | str | `"cosine"` | Distance metric (`"cosine"` atau `"l2"`) |
| `use_gpu` | bool | False | GPU support (false untuk HF Spaces compatibility) |

**Initialization Logic**:
1. Cek jika index file sudah exists
   - **Ya**: Load existing index + metadata
   - **Tidak**: Create new FAISS index

**Internal State**:
```python
self.index: faiss.IndexFlatIP          # FAISS index untuk cosine similarity
self.id_to_meta: Dict[int, Dict]       # ID → metadata mapping
self.next_id: int                       # Counter untuk next internal ID
self.deleted_ids: Set[int]              # Soft-deleted IDs
self.index_path: Path                   # Path ke FAISS file
self.meta_path: Path                    # Path ke metadata pickle file
```

**Key Methods**:

#### `add(vectors: List[List[float]], metadata_list: List[Dict]) -> List[int]`

**Fungsi**: Tambahkan vectors dan metadata ke index.

**Parameters**:
- `vectors`: List of embedding vectors (setiap vector adalah list of floats)
- `metadata_list`: List of metadata dicts (sama length dengan vectors)

**Return**: List of assigned internal IDs

**Implementation**:
```python
def add(self, vectors, metadata_list):
    vectors_array = np.array(vectors, dtype=np.float32)
    # Normalize untuk cosine similarity
    faiss.normalize_L2(vectors_array)
    
    ids = []
    for vector, metadata in zip(vectors, metadata_list):
        internal_id = self.next_id
        self.index.add(np.array([vector], dtype=np.float32))
        self.id_to_meta[internal_id] = metadata
        self.next_id += 1
        ids.append(internal_id)
    
    self.save()  # Persist changes
    return ids
```

**Contoh Usage**:
```python
store = FAISSVectorStore("data/faiss/summary_index.faiss", dimension=3072)

vectors = [
    [0.123, -0.456, ..., 0.789],  # embedding dari summary book 1
    [0.234, -0.567, ..., 0.890],  # embedding dari summary book 2
]

metadata = [
    {
        'book_id': 'book_123',
        'title': 'Fisika SMA Kelas X',
        'summary_text': 'Gelombang adalah...',
        'jenjang': 'SMA/MA/SMK/MAK'
    },
    {
        'book_id': 'book_124',
        'title': 'Fisika SMA Kelas XI',
        'summary_text': 'Listrik dan magnet adalah...',
        'jenjang': 'SMA/MA/SMK/MAK'
    }
]

assigned_ids = store.add(vectors, metadata)
# Returns: [0, 1]
```

#### `search(query_vector: List[float], top_k: int = 10) -> List[Dict]`

**Fungsi**: Search FAISS index dan return top-k hasil dengan metadata.

**Parameters**:
- `query_vector`: Single embedding vector (list of floats)
- `top_k`: Jumlah top results yang dikembalikan

**Return**: List of result dicts, sorted by relevance (highest first)

**Result Structure**:
```python
[
    {
        'id': 0,                      # internal FAISS ID
        'similarity_score': 0.89,      # cosine similarity (0-1)
        'book_id': 'book_123',
        'title': 'Fisika SMA Kelas X',
        'summary_text': 'Gelombang adalah...',
        'jenjang': 'SMA/MA/SMK/MAK'
    },
    {
        'id': 2,
        'similarity_score': 0.85,
        'book_id': 'book_456',
        'title': 'Matematika SMA Kelas X',
        ...
    }
]
```

**Implementation Details**:
- ✅ Skip deleted IDs (soft delete)
- ✅ Normalize query vector untuk cosine
- ✅ Return metadata dari `id_to_meta` mapping
- ✅ Sort by similarity score descending

#### `delete(internal_id: int, soft: bool = True)`

**Fungsi**: Hapus vector dari index (soft atau hard delete).

**Parameters**:
- `internal_id`: Internal FAISS ID yang akan di-delete
- `soft`: True untuk soft delete (mark as deleted), False untuk hard delete

**Soft Delete** (recommended):
- Mark ID dalam `deleted_ids` set
- Vector tetap ada di FAISS tapi di-skip dalam search results
- Fast operation, dapat di-undo

**Hard Delete** (maintenance only):
- Remove vector dari FAISS index
- Tidak dapat di-undo
- Expensive operation (rebuild index)

---

#### Kelas: `SummaryVectorStore` dan `FulltextVectorStore`

**Tujuan**: Specialized subclasses dari `FAISSVectorStore` untuk two-tier retrieval.

```python
class SummaryVectorStore(FAISSVectorStore):
    """FAISS store untuk summary-level search (1 vector per book)"""
    pass

class FulltextVectorStore(FAISSVectorStore):
    """FAISS store untuk chunk-level search (multiple vectors per book)"""
    pass
```

**Key Differences**:

| Aspek | SummaryVectorStore | FulltextVectorStore |
|-------|-------------------|-------------------|
| **Vektor per buku** | 1 | Multiple (1 per chunk) |
| **Use case** | Quick overview recommendations | Detailed question answering |
| **Typical size** | 100-1000 vectors | 10,000-100,000+ vectors |
| **Search latency** | Very fast (~10ms) | Moderate (~50-100ms) |
| **Metadata** | book_id, title, summary, jenjang, kelas | book_id, chunk_id, chunk_text, start, end |
| **Top-k typical** | 5-20 results | 10-30 results |

**Initialization**:
```python
# Load atau create indices
summary_store = SummaryVectorStore(
    "data/faiss/summary_index.faiss",
    dimension=3072
)

fulltext_store = FulltextVectorStore(
    "data/faiss/fulltext_index.faiss",
    dimension=3072
)

print(f"Summary index size: {summary_store.index.ntotal}")     # ~500
print(f"Fulltext index size: {fulltext_store.index.ntotal}")   # ~50000
```

---

## FAISS Index Mechanics

### IndexFlatIP (Inner Product / Cosine Similarity)

```
FAISS IndexFlatIP:
- Metric: Inner product (untuk normalized vectors = cosine similarity)
- Search: Brute-force exhaustive search (O(n) complexity)
- Pros: Exact results, simple, good untuk small-medium datasets
- Cons: Tidak scalable untuk millions of vectors

Untuk cosine similarity:
1. Normalize semua vectors ke unit length: ||v|| = 1
2. Inner product(u, v) = cos(θ)
3. FAISS IndexFlatIP return results sorted by inner product score
```

### Persistence & Loading

**Save**:
```python
# Automatically called after add/delete
faiss.write_index(self.index, str(self.index_path))
with open(self.meta_path, 'wb') as f:
    pickle.dump(self.id_to_meta, f)
```

**Load**:
```python
self.index = faiss.read_index(str(self.index_path))
with open(self.meta_path, 'rb') as f:
    self.id_to_meta = pickle.load(f)
```

---

## Integration dalam RAG Pipeline

### Recommendation Flow
```
User Query
    ↓
GeminiEmbedder.embed_text(query)
    → query_vector (3072-dim)
    ↓
SummaryVectorStore.search(query_vector, top_k=20)
    → Top 20 most similar book summaries
    ↓
Reranker (next step)
    → Top 5 after reranking
```

### Deep Dive Flow
```
User Question
    ↓
GeminiEmbedder.embed_text(question)
    → question_vector (3072-dim)
    ↓
FulltextVectorStore.search(question_vector, top_k=20)
    → Top 20 most similar chunks (from selected books)
    ↓
Reranker
    → Top 5 most relevant chunks
    ↓
Answer Generator (use chunks as context)
```

---

## Performance & Scalability

### Index Sizes

| Index | Typical # Vectors | FAISS File Size | Metadata File Size |
|-------|------------------|-----------------|-------------------|
| Summary (500 books) | 500 | ~6 MB | ~2 MB |
| Fulltext (500 books × 45 chunks) | 22,500 | ~270 MB | ~50 MB |
| Summary (5000 books) | 5,000 | ~60 MB | ~20 MB |
| Fulltext (5000 books × 45 chunks) | 225,000 | ~2.7 GB | ~500 MB |

### Search Latency

| Operation | Dataset Size | Latency | Notes |
|-----------|--------------|---------|-------|
| Embed text (Gemini API) | - | 200-500ms | Network-bound |
| Search 500 vectors | 500 | ~5ms | FAISS local |
| Search 5000 vectors | 5,000 | ~10ms | FAISS local |
| Search 22,500 vectors | 22,500 | ~50ms | Fulltext typical case |
| Total /recommend flow | - | ~700-800ms | Embed + search + rerank + LLM |

### Memory Footprint

```
Single Summary Vector: 3072 floats × 4 bytes = ~12 KB
Single Fulltext Vector: 3072 floats × 4 bytes = ~12 KB
500-book summary store: ~6 MB (FAISS) + ~2 MB (metadata) = ~8 MB RAM
22,500-chunk fulltext store: ~270 MB (FAISS) + ~50 MB (metadata) = ~320 MB RAM
```

---

## Best Practices

### Adding Vectors
1. ✅ Always normalize vectors sebelum add (jika using cosine metric)
2. ✅ Batch add untuk efficiency (jangan 1 by 1)
3. ✅ Include comprehensive metadata (book_id, chunk_id, text, dll)
4. ✅ Call `save()` setelah batch add untuk persistence

### Searching
1. ✅ Normalize query vector sebelum search
2. ✅ Use reasonable top_k (20-30 untuk summary, 20-50 untuk fulltext)
3. ✅ Post-filter results by metadata jika diperlukan (e.g., filter by jenjang)
4. ✅ Cache query embeddings jika pertanyaan sama diulang

### Soft Delete vs Hard Delete
1. ✅ Use **soft delete** untuk normal operations (mark `is_active=false`)
2. ✅ Use **hard delete** hanya untuk maintenance/cleanup (rebuild index)
3. ✅ Soft delete cost minimal (~O(1) lookup), hard delete expensive

---

