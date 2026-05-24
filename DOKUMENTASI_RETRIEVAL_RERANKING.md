# LAYER RETRIEVAL DAN RERANKING

**Dokumentasi Teknis: Semantic Search dan Relevance-Based Reranking**

---

## Ikhtisar

Layer retrieval dan reranking menangani:
1. **Query Embedding**: Konversi user query ke vector
2. **Vector Similarity Search**: Cari top-k similar documents di FAISS
3. **Metadata Filtering**: Filter hasil berdasarkan jenjang, kelas, mata pelajaran
4. **Reranking**: Re-order hasil menggunakan semantic relevance scoring

---

## 📁 Folder: `retrieval/`

**Fungsi**: Retrieval operations dari FAISS indices dengan filtering dan reranking support.

---

### File: `retriever.py`

**Tujuan**: Query FAISS vector stores dengan intelligent filtering dan multi-index search.

#### Kelas: `Retriever`

```python
class Retriever:
    """
    Retrieves relevant items dari FAISS vector stores.
    
    Attributes:
        summary_store: FAISSVectorStore untuk book summaries
        fulltext_store: FAISSVectorStore untuk text chunks
    """
    
    def __init__(
        self,
        summary_store: FAISSVectorStore,
        fulltext_store: FAISSVectorStore
    )
```

**Initialization**:
```python
retriever = Retriever(summary_store, fulltext_store)
```

---

#### Method: `search_summary()`

```python
def search_summary(
    self,
    query: str,
    query_vector: List[float],
    top_k: int = 20,
    filter_book_ids: Optional[List[str]] = None,
    filter_jenjang: Optional[List[str]] = None,
    filter_kelas: Optional[List[str]] = None,
    filter_mapel: Optional[List[str]] = None
) -> List[Dict[str, Any]]
```

**Fungsi**: Cari top-k similar book summaries dengan optional metadata filtering.

**Parameters**:

| Parameter | Type | Default | Deskripsi |
|-----------|------|---------|-----------|
| `query` | str | Required | User's original query text (for context/logging) |
| `query_vector` | List[float] | Required | Pre-embedded query vector dari GeminiEmbedder |
| `top_k` | int | 20 | Number of top results to return |
| `filter_book_ids` | Optional[List[str]] | None | Only search dalam specific book IDs |
| `filter_jenjang` | Optional[List[str]] | None | Filter by jenjang (SD/MI, SMP/MTs, SMA/MA/SMK) |
| `filter_kelas` | Optional[List[str]] | None | Filter by kelas (1-12) |
| `filter_mapel` | Optional[List[str]] | None | Filter by mata pelajaran |

**Return**: List of book results, sorted by similarity score

**Result Structure**:
```python
[
    {
        'book_id': 'book_123',
        'title': 'Fisika SMA Kelas X',
        'summary_text': 'Ringkasan buku...',
        'similarity_score': 0.89,
        'jenjang': 'SMA/MA/SMK/MAK',
        'kelas': ['X'],
        'mata_pelajaran': 'Fisika',
        'author': 'Tim Gemilang',
        'num_pages': 456,
        'is_active': true
    },
    ...
]
```

**Algorithm**:
```
1. Call summary_store.search(query_vector, top_k=top_k)
   → Return top_k raw results dari FAISS
   
2. For each result, check metadata filters:
   if filter_book_ids and book_id not in filter_book_ids:
       skip
   if filter_jenjang and jenjang not in filter_jenjang:
       skip
   if filter_kelas and no overlap dengan kelas:
       skip
   if filter_mapel and mata_pelajaran not in filter_mapel:
       skip
       
3. Return filtered results (may be < top_k if filters are strict)
```

**Contoh Usage**:
```python
# Basic search (tanpa filter)
results = retriever.search_summary(
    query="Buku fisika tentang gelombang",
    query_vector=query_vector,
    top_k=20
)

# Search dengan filter jenjang
results_sma = retriever.search_summary(
    query="Buku fisika tentang gelombang",
    query_vector=query_vector,
    top_k=20,
    filter_jenjang=['SMA/MA/SMK/MAK']
)

# Search dalam selected books only
results_selected = retriever.search_summary(
    query="Apa rumus gaya sentripetal?",
    query_vector=query_vector,
    top_k=10,
    filter_book_ids=['book_123', 'book_456']
)
```

---

#### Method: `search_fulltext_by_book_ids()`

```python
def search_fulltext_by_book_ids(
    self,
    query: str,
    query_vector: List[float],
    book_ids: List[str],
    top_k: int = 20
) -> List[Dict[str, Any]]
```

**Fungsi**: Cari chunks hanya dari specified books untuk deep dive questions.

**Parameters**:
- `query`: User's question text
- `query_vector`: Pre-embedded question vector
- `book_ids`: List of book IDs to search within (1-5 books)
- `top_k`: Number of top chunks to return

**Return**: List of chunk results from specified books only

**Result Structure**:
```python
[
    {
        'book_id': 'book_123',
        'title': 'Fisika SMA Kelas X',
        'chunk_id': 'chunk_0',
        'chunk_text': 'Teks dari chunk ini...',
        'chunk_index': 0,
        'similarity_score': 0.87,
        'start': 0,
        'end': 30000
    },
    {
        'book_id': 'book_123',
        'title': 'Fisika SMA Kelas X',
        'chunk_id': 'chunk_2',
        'chunk_text': 'Teks chunk berikutnya...',
        'chunk_index': 2,
        'similarity_score': 0.85,
        'start': 29000,
        'end': 59000
    }
]
```

**Algorithm**:
```
1. Call fulltext_store.search(query_vector, top_k=top_k × len(book_ids))
   → Get more results to ensure we have k results from specified books
   
2. Filter to only include chunks where book_id in book_ids
   
3. Return top_k filtered results
```

**Use Case**: Deep dive questions dalam selected books

---

#### Helper: `_extract_filters_from_query()`

```python
def _extract_filters_from_query(self, query: str) -> Dict[str, List[str]]
```

**Fungsi**: Extract metadata filters dari natural language query menggunakan keyword matching.

**Example Extractions**:

| Query | Extracted Filters |
|-------|------------------|
| "Buku fisika SMA kelas 10" | `{'jenjang': ['SMA/MA/SMK/MAK'], 'kelas': ['10', 'X'], 'mapel': ['Fisika']}` |
| "Matematika SD" | `{'jenjang': ['SD/MI'], 'mapel': ['Matematika']}` |
| "IPA SMP kelas 7" | `{'jenjang': ['SMP/MTs'], 'kelas': ['7', 'VII'], 'mapel': ['IPA']}` |

**Keyword Mappings**:

```python
# Jenjang keywords
"SD", "sekolah dasar", "MI", "madrasah ibtidaiyah" → "SD/MI"
"SMP", "sekolah menengah pertama", "MTs", "madrasah tsanawiyah" → "SMP/MTs"
"SMA", "SMK", "sekolah menengah atas", "MA", "madrasah aliyah" → "SMA/MA/SMK/MAK"

# Kelas keywords
"kelas 1" atau "kelas I" → ["1", "I"]
"kelas 2" atau "kelas II" → ["2", "II"]
... sampai kelas 12

# Mata Pelajaran keywords
"matematika", "mtk", "hitung" → "matematika"
"ipa", "sains", "ilmu pengetahuan alam", "biologi", "fisika", "kimia" → "IPA"
"ips", "ilmu pengetahuan sosial", "sejarah", "geografi" → "IPS"
"bahasa indonesia", "b.indo", "b indo" → "bahasa indonesia"
"bahasa inggris", "b.inggris", "english" → "bahasa inggris"
"pkn", "pancasila", "pendidikan kewarganegaraan" → "PKN"
"agama islam", "pai", "pendidikan agama islam" → "agama islam"
... dan lainnya
```

**Implementation**:
```python
def _extract_filters_from_query(self, query: str):
    query_lower = query.lower()
    filters = {"jenjang": [], "kelas": [], "mata_pelajaran": []}
    
    # Check jenjang keywords
    if any(word in query_lower for word in ["sd", "sekolah dasar", "mi", ...]):
        filters["jenjang"].append("SD/MI")
    # ... more jenjang checks
    
    # Check kelas keywords
    for class_int, class_roman in [(1, "I"), (2, "II"), ..., (12, "XII")]:
        if f"kelas {class_int}" in query_lower or f"kelas {class_roman.lower()}" in query_lower:
            filters["kelas"].extend([str(class_int), class_roman])
    
    # Check mata_pelajaran keywords
    # (comprehensive mapping untuk 20+ subject keywords)
    
    return filters
```

**Robustness**:
- ✅ Case-insensitive matching
- ✅ Partial word matching (e.g., "IPA" matches "ipa", "IPA", "SAINS")
- ✅ Multiple keyword synonyms per subject
- ✅ Handles both numeric (1) dan roman (I) class numbers

---

### File: `reranker.py`

**Tujuan**: Rerank search results menggunakan semantic relevance scoring via Jina AI API.

#### Kelas: `Reranker`

```python
class Reranker:
    """
    Reranks documents menggunakan Jina AI's reranking API.
    
    Attributes:
        api_key_manager: Manages API keys
        model: Name of reranker model
        api_url: Endpoint URL untuk Jina rerank API
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "jina-reranker-v3",
        api_url: str = "https://api.jina.ai/v1/rerank"
    )
```

**Initialization**:
```python
reranker = Reranker()  # uses JINA_API_KEY from config
```

---

#### Method: `rerank()`

```python
def rerank(
    self,
    query: str,
    documents: List[str],
    top_n: Optional[int] = None
) -> List[Dict[str, Any]]
```

**Fungsi**: Rerank documents berdasarkan relevance ke query menggunakan Jina API.

**Parameters**:
- `query`: User query atau question
- `documents`: List of document texts to rerank
- `top_n`: Max top documents to return (if None, return all)

**Return**: List of reranked results

**Result Structure**:
```python
[
    {
        'index': 3,                    # original index dalam input list
        'text': 'Teks dokumen 3...',   # original document text
        'relevance_score': 0.92        # float score (higher = more relevant)
    },
    {
        'index': 1,
        'text': 'Teks dokumen 1...',
        'relevance_score': 0.87
    },
    # Sorted by relevance_score descending
]
```

**API Payload**:
```python
payload = {
    "model": "jina-reranker-v3",
    "query": query,
    "documents": documents,
    "top_n": top_n or len(documents)
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

**Error Handling**:
- ✅ Validate inputs (query and documents not empty)
- ✅ HTTP error handling (retry, log failures)
- ✅ Timeout handling (default 30 seconds)

---

#### Method: `rerank_results()`

```python
def rerank_results(
    self,
    query: str,
    retrieval_results: List[Dict[str, Any]],
    text_field: str,                    # 'summary_text' atau 'chunk_text'
    top_n: int = 5
) -> List[Dict[str, Any]]
```

**Fungsi**: Helper method untuk rerank hasil retrieval dengan preservation metadata.

**Parameters**:
- `query`: User query
- `retrieval_results`: Results dari FAISS search (dengan metadata)
- `text_field`: Which field contains the document text ('summary_text' atau 'chunk_text')
- `top_n`: Top N results after reranking

**Return**: Top-N reranked results dengan original metadata intact

**Example Usage**:
```python
# Recommendation flow
summary_results = retriever.search_summary(query, query_vector, top_k=20)
reranked = reranker.rerank_results(
    query=query,
    retrieval_results=summary_results,
    text_field='summary_text',
    top_n=5
)
# reranked = [
#     {
#         'index': 3,
#         'book_id': 'book_456',
#         'title': 'Fisika SMA Kelas X',
#         'summary_text': '...',
#         'relevance_score': 0.92,
#         'similarity_score': 0.85  # original FAISS score preserved
#     },
#     ...
# ]

# Deep dive flow
chunk_results = retriever.search_fulltext_by_book_ids(question, query_vector, book_ids=['book_123'])
reranked_chunks = reranker.rerank_results(
    query=question,
    retrieval_results=chunk_results,
    text_field='chunk_text',
    top_n=5
)
```

**Algorithm**:
```
1. Extract text field dari setiap result:
   documents = [result[text_field] for result in retrieval_results]

2. Call rerank(query, documents, top_n):
   reranked_with_scores = reranker.rerank(query, documents, top_n)
   
3. Map reranked results kembali ke original metadata:
   For each reranked_result:
       index = reranked_result['index']
       original_result = retrieval_results[index]
       merge (reranked_result + original_result metadata)
       
4. Return merged results (sorted by relevance_score)
```

---

## Integrated Retrieval + Reranking Flow

### Recommendation Pipeline
```
User Query: "Buku fisika tentang gelombang SMA"
    ↓
GeminiEmbedder.embed_text(query)
    → query_vector
    ↓
Retriever.search_summary(query, query_vector, top_k=20)
    Extract filters: {jenjang: ['SMA/MA/SMK/MAK'], mapel: ['Fisika']}
    → 20 results dengan similarity scores
    ↓
Reranker.rerank_results(query, results, text_field='summary_text', top_n=5)
    → 5 reranked results dengan relevance scores
    ↓
AnswerGenerator.generate_recommendation_answer(query, top_5_books)
    → Final recommendation text
    ↓
Return to Frontend:
{
    "recommendations": [
        {"book_id": "...", "title": "...", "similarity": 0.89, "relevance": 0.92},
        ...
    ],
    "answer": "Berikut rekomendasi buku fisika untuk kamu..."
}
```

### Deep Dive Pipeline
```
Selected Books: ['book_123', 'book_456']
Question: "Apa rumus gaya sentripetal?"
    ↓
GeminiEmbedder.embed_text(question)
    → question_vector
    ↓
Retriever.search_fulltext_by_book_ids(question, question_vector, book_ids, top_k=20)
    → 20 chunks dari selected books dengan similarity scores
    ↓
Reranker.rerank_results(question, chunks, text_field='chunk_text', top_n=5)
    → 5 most relevant chunks dengan relevance scores
    ↓
AnswerGenerator.generate_deep_answer(question, selected_books, top_5_chunks)
    Use chunks as context untuk answer generation
    ↓
Return:
{
    "answer": "Rumus gaya sentripetal adalah F = m × v² / r, dimana...",
    "sources": [
        {"book_id": "book_123", "chunk": "Teks konteks dari chunk..."},
        ...
    ]
}
```

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| `search_summary(top_k=20)` | ~10-20ms | FAISS local search |
| `search_fulltext_by_book_ids(top_k=20)` | ~30-50ms | Larger index |
| `rerank(20 documents)` | ~500-1000ms | API call to Jina |
| **Total /recommend flow** | ~700-1100ms | Excluding LLM generation |

---

## Best Practices

### Filtering
1. ✅ Respect user intent: Extract filters dan gunakan untuk constraint search
2. ✅ Graceful degradation: Jika filter terlalu strict (0 results), retry tanpa filter
3. ✅ Transparency: Return info tentang filters yang diapply

### Reranking
1. ✅ Always rerank untuk better UX (jangan rely purely pada FAISS similarity)
2. ✅ Keep top-k reasonable (5-10 untuk recommendations, 3-5 untuk deep dive)
3. ✅ Preserve original similarity scores untuk debugging
4. ✅ Monitor Jina API quota dan costs

### Error Handling
1. ✅ Graceful fallback jika Jina API down (return FAISS results as-is)
2. ✅ Retry logic untuk transient API errors
3. ✅ Log API failures untuk monitoring

---

