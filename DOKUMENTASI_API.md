# API BACKEND DAN REST ENDPOINTS

**Dokumentasi Teknis: Flask Application Architecture dan Endpoint Specifications**

---

## Ikhtisar

API layer menyediakan REST endpoints untuk:
1. **Rekomendasi Buku**: `/api/recommend` - Query-based recommendations
2. **Pencarian Mendalam**: `/api/deep` - Detailed Q&A dalam selected books
3. **Admin Operations**: `/api/admin` - Book management (add/update/delete)
4. **Health Check**: `/api/health` - System monitoring

---

## 📁 Folder: `api/`

**Fungsi**: Flask application factory, global component initialization, dan blueprint registration.

---

### File: `app.py`

**Tujuan**: Flask app factory dengan automatic component loading dan blueprint registration.

#### Function: `create_app()`

```python
def create_app() -> Flask:
    """
    Application factory for Flask.
    Loads all global components and registers blueprints.
    """
```

**Initialization Flow**:

```
create_app()
    ├─ Initialize Flask app
    ├─ Enable CORS (allow all origins for now)
    │
    ├─ Load Global Components:
    │   ├─ GeminiEmbedder()
    │   ├─ SummaryVectorStore() 
    │   ├─ FulltextVectorStore()
    │   ├─ Retriever()
    │   ├─ Reranker()
    │   └─ AnswerGenerator()
    │
    ├─ Store components in app.config:
    │   app.config['embedder'] = embedder
    │   app.config['retriever'] = retriever
    │   app.config['reranker'] = reranker
    │   app.config['answer_generator'] = answer_generator
    │
    ├─ Register Blueprints:
    │   ├─ recommend_bp (routes/recommend.py)
    │   ├─ deep_bp (routes/deep.py)
    │   └─ admin_bp (routes/admin.py)
    │
    └─ Register Health Check Endpoints:
        ├─ GET /health
        └─ GET /api/health
```

**Component Initialization**:

| Component | Library | Initialization | Config Storage |
|-----------|---------|-----------------|-----------------|
| GeminiEmbedder | google.genai | Load API keys, init client | `app.config['embedder']` |
| SummaryVectorStore | FAISS | Load from `SUMMARY_INDEX_PATH` | Part of retriever |
| FulltextVectorStore | FAISS | Load from `FULLTEXT_INDEX_PATH` | Part of retriever |
| Retriever | Custom | Init with both stores | `app.config['retriever']` |
| Reranker | Custom | Load Jina API key | `app.config['reranker']` |
| AnswerGenerator | google.genai | Load API keys, set system prompt | `app.config['answer_generator']` |

**Error Handling**:
```python
try:
    # Load components
    embedder = GeminiEmbedder()
    logger.info("GeminiEmbedder initialized")
    
    # Get embedding dimension from dummy call
    dummy_vector = embedder.embed_text("test")
    dimension = len(dummy_vector)
    logger.info(f"Embedding dimension: {dimension}")
    
    # Vector stores
    summary_store = SummaryVectorStore(SUMMARY_INDEX_PATH, dimension=dimension)
    fulltext_store = FulltextVectorStore(FULLTEXT_INDEX_PATH, dimension=dimension)
    
    # ... rest of initialization
    logger.info("All global components loaded successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize global components: {e}", exc_info=True)
    raise  # Re-raise untuk fail-fast
```

**CORS Configuration**:
```python
CORS(app, origins=["*"])  # Allow all origins (dev mode)
# Production: Specify allowed domains
# CORS(app, origins=["https://rumah-literasi.com", "https://app.rumah-literasi.com"])
```

---

### Folder: `routes/`

**Fungsi**: Individual blueprints untuk setiap API endpoint.

---

#### File: `recommend.py`

**Tujuan**: `/api/recommend` endpoint untuk book recommendations.

```python
@recommend_bp.route('/recommend', methods=['POST'])
def recommend():
    """
    Receive user query, return book recommendations.
    Expected JSON: {"query": "saya butuh buku fisika sma tentang gelombang"}
    """
```

**HTTP Endpoint**:
- **Method**: POST
- **URL**: `/api/recommend`
- **Content-Type**: `application/json`

**Request Schema**:
```json
{
    "query": "string",  // User's search query (required)
    "filter_jenjang": "array of strings (optional)",  // ['SD/MI', 'SMP/MTs', ...]
    "filter_kelas": "array of strings (optional)",    // ['1', '2', ...] atau ['I', 'II', ...]
    "filter_mapel": "array of strings (optional)"     // ['Matematika', 'IPA', ...]
}
```

**Request Example**:
```bash
curl -X POST http://localhost:5000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Saya butuh buku fisika tentang gelombang untuk SMA kelas 10"
  }'
```

**Response Schema (Success)**:
```json
{
    "status": "success",
    "query": "...",
    "recommendations": [
        {
            "book_id": "book_123",
            "title": "Fisika SMA Kelas X",
            "author": "Tim Gemilang",
            "jenjang": "SMA/MA/SMK/MAK",
            "kelas": ["X"],
            "mata_pelajaran": "Fisika",
            "summary": "Ringkasan 400 kata dari buku...",
            "similarity_score": 0.89,    // FAISS score
            "relevance_score": 0.92,     // Reranker score
            "num_pages": 456
        },
        // ... up to 5 results
    ],
    "answer": "Wah, pertanyaan yang bagus sekali, Sobat Belajar! Saya menemukan 5 buku yang sangat cocok untuk kamu..."
}
```

**Response Schema (Error)**:
```json
{
    "status": "error",
    "error": "Missing 'query' field" | "Query cannot be empty" | "Internal server error",
    "code": 400 | 500
}
```

**HTTP Status Codes**:
| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Recommendations found |
| 400 | Bad Request | Missing query field |
| 404 | Not Found | No recommendations found |
| 500 | Server Error | API initialization failed |

**Processing Pipeline**:
```
1. Validate request (query not empty)
2. Get components dari app.config
3. Embed query (GeminiEmbedder)
4. Search summary index (Retriever.search_summary, top_k=20)
5. Rerank results (Reranker.rerank_results, top_n=5)
6. Generate recommendation answer (AnswerGenerator.generate_recommendation)
7. Format response dengan metadata
8. Return JSON
```

**Error Scenarios**:
- ✅ Missing 'query' field → 400 Bad Request
- ✅ Empty query → 400 Bad Request
- ✅ Embedding failed → 500 Internal Server Error
- ✅ No results found → 200 OK with empty recommendations + fallback message

---

#### File: `deep.py`

**Tujuan**: `/api/deep` endpoint untuk detailed Q&A dalam selected books.

```python
@deep_bp.route('/deep', methods=['POST'])
def deep_dive():
    """
    Receive selected book_ids and a question, return detailed answer.
    Expected JSON: {"book_ids": ["book_123", "book_456"], "question": "Apa rumus gaya sentripetal?"}
    """
```

**HTTP Endpoint**:
- **Method**: POST
- **URL**: `/api/deep`
- **Content-Type**: `application/json`

**Request Schema**:
```json
{
    "book_ids": "array of strings (required)",  // 1 to 5 book IDs
    "question": "string (required)"             // User's detailed question
}
```

**Request Example**:
```bash
curl -X POST http://localhost:5000/api/deep \
  -H "Content-Type: application/json" \
  -d '{
    "book_ids": ["book_123", "book_456"],
    "question": "Apa rumus gaya sentripetal dan bagaimana aplikasinya?"
  }'
```

**Response Schema (Success)**:
```json
{
    "status": "success",
    "book_ids": ["book_123", "book_456"],
    "question": "...",
    "answer": "Gaya sentripetal adalah gaya yang menarik benda menuju pusat lingkaran... F_s = m × v² / r",
    "sources": [
        {
            "book_id": "book_123",
            "title": "Fisika SMA Kelas X",
            "chunk_id": "chunk_0",
            "chunk_text": "Teks konteks dari chunk ini...",
            "relevance_score": 0.92
        },
        // ... up to 5 source chunks
    ]
}
```

**Response Schema (Error)**:
```json
{
    "status": "error",
    "error": "Missing 'book_ids' or 'question' field" | "book_ids must be a list with 1 to 5 items" | "Question cannot be empty",
    "code": 400 | 500
}
```

**Processing Pipeline**:
```
1. Validate request:
   - book_ids is list with 1-5 items
   - question not empty
2. Get components dari app.config
3. Embed question (GeminiEmbedder)
4. Search fulltext index for selected books (Retriever.search_fulltext_by_book_ids, top_k=20)
5. Rerank chunks (Reranker.rerank_results, top_n=5)
6. Generate detailed answer with context (AnswerGenerator.generate_deep_answer)
7. Format response dengan sources
8. Return JSON
```

**Constraints & Validations**:
- ✅ book_ids must be list: 1-5 items
- ✅ question cannot be empty
- ✅ Filter chunks to only from specified books
- ✅ Return empty answer jika no relevant chunks found (graceful fallback)

---

#### File: `admin.py`

**Tujuan**: `/api/admin` endpoint untuk book management operations.

```python
@admin_bp.route('/admin/add', methods=['POST'])
@admin_bp.route('/admin/update', methods=['PUT'])
@admin_bp.route('/admin/delete', methods=['DELETE'])
def admin_operations():
    """
    Manage books: add new, update existing, or delete from collection.
    """
```

**HTTP Endpoints**:

| Method | URL | Operation |
|--------|-----|-----------|
| POST | `/api/admin/add` | Add new book |
| PUT | `/api/admin/update` | Update existing book |
| DELETE | `/api/admin/delete` | Delete book (soft delete) |

#### `/api/admin/add` - Add New Book

**Request Schema**:
```json
{
    "pdf_path": "string (required)",      // Path to PDF file
    "title": "string (required)",
    "author": "string (optional)",
    "jenjang": "string (required)",       // SD/MI, SMP/MTs, SMA/MA/SMK/MAK
    "kelas": "array of strings",          // ['1', '2', ...] atau ['I', 'II', ...]
    "mata_pelajaran": "string (required)" // Matematika, IPA, IPS, dll
}
```

**Processing**:
```
1. Validate PDF exists
2. Parse PDF → extract text
3. Summarize text → generate 300-400 word summary
4. Embed summary → vector
5. Chunk fulltext → vectors
6. Add summary to SummaryVectorStore
7. Add chunks to FulltextVectorStore
8. Save metadata to JSON
9. Return success with book_id
```

**Response**:
```json
{
    "status": "success",
    "book_id": "book_uuid_generated",
    "title": "...",
    "num_chunks": 45,
    "message": "Book added successfully"
}
```

#### `/api/admin/update` - Update Existing Book

**Request Schema**:
```json
{
    "book_id": "string (required)",
    "title": "string (optional)",
    "author": "string (optional)",
    "jenjang": "string (optional)",
    "kelas": "array (optional)",
    "mata_pelajaran": "string (optional)",
    "is_active": "boolean (optional)"
}
```

**Processing**:
```
1. Find book_id in metadata
2. Update metadata fields
3. Re-embed summary jika title/content changed
4. Save changes to JSON
5. Return success
```

#### `/api/admin/delete` - Delete Book

**Request Schema**:
```json
{
    "book_id": "string (required)",
    "hard_delete": "boolean (optional, default: false)"
}
```

**Processing**:
- **Soft Delete** (default): Mark `is_active=false` in metadata
- **Hard Delete**: Remove dari FAISS indices (expensive, use sparingly)

**Response**:
```json
{
    "status": "success",
    "book_id": "...",
    "message": "Book deleted successfully"
}
```

---

### Health Check Endpoints

**Endpoints**:
- `GET /health` → Status healthy
- `GET /api/health` → Status healthy (alias)

**Response**:
```json
{
    "status": "healthy",
    "message": "RAG system is running"
}
```

**Use Cases**:
- ✅ Kubernetes health probes
- ✅ Load balancer checks
- ✅ Monitoring & alerting

---

## Configuration & Deployment

### Environment Setup

Create `.env` file:
```
# Gemini API Keys (multiple for load balancing)
GEMINI_API_KEY_1=...
GEMINI_API_KEY_2=...
... (up to 17 keys)
GEMINI_MODEL=gemini-2.5-flash
ANSWER_MODEL=gemini-2.5-pro

# Jina Reranker
JINA_API_KEY=...
JINA_RERANK_MODEL=jina-reranker-v3

# OpenRouter (fallback LLM)
OPENROUTER_API_KEY=...
LLM_MODEL=openrouter/qwen-3-7b

# Chunking
CHUNK_SIZE=30000
CHUNK_OVERLAP=1000
```

### Running the API

**Development**:
```bash
python run_api.py
# Runs on localhost:5000
```

**Production** (Hugging Face Spaces):
```bash
# Using Uvicorn for production
uvicorn api.app:app --host 0.0.0.0 --port 7860
```

### CORS Configuration

```python
# Development (allow all)
CORS(app, origins=["*"])

# Production (restrict to specific domains)
CORS(app, origins=[
    "https://rumah-literasi.com",
    "https://app.rumah-literasi.com",
    "https://my-huggingface-space.hf.space"
])
```

---

## Performance & Scalability

### Typical Response Times

| Endpoint | Latency | Components |
|----------|---------|-----------|
| `/recommend` | 1.0-1.5s | Embed (0.3s) + Search (0.05s) + Rerank (0.8s) + LLM (0.2s) |
| `/deep` | 1.5-2.0s | Embed (0.3s) + Search (0.1s) + Rerank (0.8s) + LLM (0.3s) |
| `/health` | 10ms | Direct response |

### Throughput

- **Max concurrent requests**: ~5-10 (limited by LLM API quota)
- **Requests per minute**: ~30-60 (depends on API key rate limits)
- **Max parallel searches**: 100+ (FAISS is fast locally)

### Memory Usage

```
Flask app + loaded components:
- GeminiEmbedder: ~50 MB
- SummaryVectorStore (500 books): ~8 MB
- FulltextVectorStore (22k chunks): ~320 MB
- Metadata cache: ~20 MB
- Total: ~400 MB
```

---

## Error Handling & Resilience

### API Error Responses

| Error | Status | Message |
|-------|--------|---------|
| Invalid JSON | 400 | "Invalid JSON payload" |
| Missing required field | 400 | "Missing 'query' field" |
| Invalid input | 400 | "Query cannot be empty" |
| Embedding failed | 500 | "Embedding failed" |
| No results | 200 | Returns empty recommendations + fallback message |
| API key exhausted | 503 | "Service temporarily unavailable" |
| Internal error | 500 | "Internal server error" |

### Graceful Degradation

```python
# Embedding fails
if not query_vector:
    return {"error": "Embedding failed"}, 500

# No retrieval results
if not summary_results:
    return {
        "recommendations": [],
        "answer": "Maaf, saya tidak menemukan buku yang sesuai..."
    }, 200

# Reranking fails (fallback to FAISS results)
try:
    reranked = reranker.rerank_results(...)
except Exception as e:
    logger.warning(f"Reranking failed, using FAISS results: {e}")
    reranked = summary_results[:5]  # Fallback

# LLM fails (return structured response tanpa generation)
try:
    answer = answer_generator.generate_recommendation(...)
except Exception as e:
    logger.error(f"Answer generation failed: {e}")
    answer = "Buku-buku berikut mungkin relevan dengan pertanyaanmu..."
    # Return results without LLM-generated answer
```

---

## Monitoring & Logging

### Endpoint Logging

Setiap request di-log dengan:
- Timestamp
- Request method + URL
- Query/parameters
- Response status
- Response time
- Errors (jika ada)

**Log Format**:
```
[2026-05-23 10:30:45] POST /api/recommend | query="fisika gelombang sma" | status=200 | time=1.2s
[2026-05-23 10:31:12] POST /api/deep | books=2 | status=200 | time=1.8s
```

### Metrics to Monitor

- ✅ Request count per endpoint
- ✅ Response time (p50, p95, p99)
- ✅ Error rate (4xx, 5xx)
- ✅ API key exhaustion
- ✅ Vector store search latency
- ✅ LLM generation latency

---

## Best Practices

### Request Validation
1. ✅ Validate all required fields present
2. ✅ Validate field types (string, array, etc.)
3. ✅ Validate constraints (1-5 books, etc.)
4. ✅ Sanitize inputs untuk safety

### Response Format
1. ✅ Consistent JSON structure
2. ✅ Always include status field
3. ✅ Clear error messages
4. ✅ Include metadata dalam response

### Error Handling
1. ✅ Never expose internal error details to client
2. ✅ Log full errors internally
3. ✅ Return user-friendly error messages
4. ✅ Implement graceful degradation

### Security
1. ✅ Validate API key dalam headers (if implementing auth)
2. ✅ Rate limiting per IP/API key
3. ✅ Input sanitization untuk prevent injection attacks
4. ✅ HTTPS in production

---

