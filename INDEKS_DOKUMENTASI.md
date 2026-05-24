# INDEKS DOKUMENTASI LENGKAP

**Sistem Rekomendasi Buku Berbasis Retrieval-Augmented Generation (RAG)**

*Generated: Mei 2026*

---

## 📑 Daftar Dokumentasi

Dokumentasi ini terdiri dari **7 file markdown terstruktur** yang dapat disimpan secara terpisah:

| # | File | Topik | Bagian |
|---|------|-------|--------|
| 1 | [DOKUMENTASI_ARSITEKTUR.md](DOKUMENTASI_ARSITEKTUR.md) | Ringkasan Sistem & Konfigurasi | Overview, Config, Utils |
| 2 | [DOKUMENTASI_PIPELINE_INGESTION.md](DOKUMENTASI_PIPELINE_INGESTION.md) | Data Ingestion & Processing | Parsing, Chunking, Summarization |
| 3 | [DOKUMENTASI_EMBEDDING_VECTORSTORE.md](DOKUMENTASI_EMBEDDING_VECTORSTORE.md) | Embeddings & Vector Search | Embedder, FAISS, Indexing |
| 4 | [DOKUMENTASI_RETRIEVAL_RERANKING.md](DOKUMENTASI_RETRIEVAL_RERANKING.md) | Retrieval & Reranking | Retriever, Reranker, Filtering |
| 5 | [DOKUMENTASI_GENERATION.md](DOKUMENTASI_GENERATION.md) | Answer Generation | LLM, Prompting, Guardrails |
| 6 | [DOKUMENTASI_API.md](DOKUMENTASI_API.md) | REST API & Endpoints | Flask, Routes, Deployment |
| 7 | [DOKUMENTASI_EVALUASI.md](DOKUMENTASI_EVALUASI.md) | Evaluation Framework | RAGAS, Precision@K, Testing |
| 8 | [DOKUMENTASI_SCRIPTS_INTERFACE.md](DOKUMENTASI_SCRIPTS_INTERFACE.md) | Scripts & Interface | Admin, UI, Processing |

---

## 🗺️ Navigasi Berdasarkan Use Case

### Untuk Developer Backend

```
Mulai dari:
1. DOKUMENTASI_ARSITEKTUR.md
   └─ Pahami stack teknologi & konfigurasi

2. DOKUMENTASI_EMBEDDING_VECTORSTORE.md
   └─ Mengerti cara vectors disimpan & di-search

3. DOKUMENTASI_RETRIEVAL_RERANKING.md
   └─ Implementasi retrieval logic

4. DOKUMENTASI_GENERATION.md
   └─ LLM integration & answer generation

5. DOKUMENTASI_API.md
   └─ REST endpoint implementation

6. DOKUMENTASI_EVALUASI.md
   └─ Testing & monitoring
```

### Untuk Data/ML Engineer

```
Mulai dari:
1. DOKUMENTASI_ARSITEKTUR.md
   └─ Teknis stack & overview

2. DOKUMENTASI_PIPELINE_INGESTION.md
   └─ ETL pipeline & data preparation

3. DOKUMENTASI_EMBEDDING_VECTORSTORE.md
   └─ Embedding models & vector indexing

4. DOKUMENTASI_EVALUASI.md
   └─ RAGAS metrics & evaluation

5. DOKUMENTASI_RETRIEVAL_RERANKING.md
   └─ Retrieval quality optimization
```

### Untuk Sistem Administrator

```
Mulai dari:
1. DOKUMENTASI_ARSITEKTUR.md
   └─ Konfigurasi & API keys

2. DOKUMENTASI_SCRIPTS_INTERFACE.md
   └─ Batch processing & maintenance

3. DOKUMENTASI_API.md
   └─ Deployment & monitoring

4. DOKUMENTASI_EVALUASI.md
   └─ Performance monitoring
```

### Untuk Frontend Developer

```
Mulai dari:
1. DOKUMENTASI_API.md
   └─ REST endpoint specifications

2. DOKUMENTASI_SCRIPTS_INTERFACE.md
   └─ Frontend architecture & JavaScript modules

3. DOKUMENTASI_GENERATION.md
   └─ Response format & LLM output
```

---

## 🔍 Panduan Pencarian Cepat

### Mencari Informasi Tentang...

| Topik | File | Bagian |
|-------|------|--------|
| **Konfigurasi API keys** | DOKUMENTASI_ARSITEKTUR.md | `config/settings.py` |
| **Cara embed teks** | DOKUMENTASI_EMBEDDING_VECTORSTORE.md | `GeminiEmbedder.embed_text()` |
| **FAISS index operations** | DOKUMENTASI_EMBEDDING_VECTORSTORE.md | `FAISSVectorStore` class |
| **Query filtering** | DOKUMENTASI_RETRIEVAL_RERANKING.md | `_extract_filters_from_query()` |
| **Reranking dengan Jina** | DOKUMENTASI_RETRIEVAL_RERANKING.md | `Reranker.rerank()` |
| **System prompt Gemini** | DOKUMENTASI_GENERATION.md | `AnswerGenerator.__init__()` |
| **POST /api/recommend** | DOKUMENTASI_API.md | `recommend.py` |
| **POST /api/deep** | DOKUMENTASI_API.md | `deep.py` |
| **RAGAS metrics** | DOKUMENTASI_EVALUASI.md | `RagasEvaluator` |
| **Batch ingestion** | DOKUMENTASI_SCRIPTS_INTERFACE.md | `ingest_all.py` |
| **Metadata schema** | DOKUMENTASI_SCRIPTS_INTERFACE.md | `data/metadata/books.json` |

---

## 📊 Arsitektur High-Level

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERFACE (Web/Mobile)                  │
│              interface/index.html + js/api.js                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ┌──────▼─────────┐
                    │   FLASK API    │
                    │  api/app.py    │
                    │                │
                    │ POST /recommend│
                    │ POST /deep     │
                    │ POST /admin    │
                    └────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐   ┌──────▼──────┐
   │EMBEDDER │      │ RETRIEVER   │   │ RERANKER    │
   │(Gemini) │      │ (FAISS)     │   │ (Jina AI)   │
   └────┬────┘      └──────┬──────┘   └──────┬──────┘
        │                  │                  │
        │           ┌──────▼──────────┐      │
        │           │  VECTOR STORE   │      │
        │           │ (Summary Index  │      │
        │           │  Fulltext Index)│      │
        │           └─────────────────┘      │
        │                                    │
        └────────────────┬───────────────────┘
                         │
              ┌──────────▼──────────┐
              │ ANSWER GENERATOR    │
              │ (Gemini LLM)        │
              └─────────────────────┘
```

---

## 🔄 Data Flow Utama

### Recommendation Pipeline

```
User Input (Natural Language Query)
         ↓
[GeminiEmbedder] Embed Query → 3072-dim vector
         ↓
[Retriever.search_summary()] FAISS search → top-20 books
         ↓
[Retriever._extract_filters_from_query()] Extract metadata filters
         ↓
[Reranker.rerank_results()] Jina reranking → top-5 books
         ↓
[AnswerGenerator.generate_recommendation()] Generate friendly answer
         ↓
Return JSON: {recommendations: [...], answer: "..."}
```

### Deep Dive Pipeline

```
User Input (Selected Books + Question)
         ↓
[GeminiEmbedder] Embed Question → 3072-dim vector
         ↓
[Retriever.search_fulltext_by_book_ids()] FAISS search in selected books → top-20 chunks
         ↓
[Reranker.rerank_results()] Jina reranking → top-5 chunks
         ↓
[AnswerGenerator.generate_deep_answer()] Generate answer with context
         ↓
Return JSON: {answer: "...", sources: [...]}
```

### Batch Ingestion Pipeline

```
Raw PDF Files
         ↓
[PDFParser] Extract text → pages
         ↓
[TextCleaner] Normalize whitespace
         ↓
[BookSummarizer] Generate 300-400 word summary
         ↓
[text_chunker] Split to 30KB chunks with 1KB overlap
         ↓
[GeminiEmbedder] Embed summary + all chunks
         ↓
[SummaryVectorStore.add()] Add summary vector + metadata
         ↓
[FulltextVectorStore.add()] Add chunk vectors + metadata
         ↓
FAISS indices ready for retrieval
```

---

## 📈 Performance Targets

| Metrik | Target | Actual | Notes |
|--------|--------|--------|-------|
| **Recommendation Latency** | < 1.5s | 1.0-1.5s | Embed + Search + Rerank + LLM |
| **Deep Dive Latency** | < 2.0s | 1.5-2.0s | More context → slower |
| **Throughput** | 30-60 req/min | 30-60 req/min | API key rate limit |
| **Memory Footprint** | < 500 MB | ~400 MB | FAISS indices + metadata |
| **Search Latency** | < 50ms | 10-50ms | FAISS local operation |
| **RAGAS Score** | > 0.80 | 0.84 | Faithfulness + relevancy |
| **Precision@5** | > 0.70 | 0.76 | Recommendation accuracy |

---

## 🔑 Key Technologies

### Models & APIs

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Embedding** | Google Gemini 2.5 (gemini-embedding-2) | Text → 3072-dim vectors |
| **Reranking** | Jina AI (Reranker v3) | Semantic relevance scoring |
| **Answer Generation** | Google Gemini 2.5 Pro | LLM-based answer generation |
| **Fallback LLM** | OpenRouter (Qwen3) | Backup untuk answer generation |
| **Vector Database** | FAISS (IndexFlatIP) | Similarity search |
| **PDF Processing** | PyMuPDF (fitz) | Extract text dari PDF |

### Frameworks & Libraries

| Component | Library | Version |
|-----------|---------|---------|
| **Web Framework** | Flask | 3.1.3 |
| **Vector Store** | FAISS | 1.13.2+ |
| **Embeddings** | google-genai | 1.73.1+ |
| **Reranking** | HTTP API (requests) | - |
| **Text Processing** | PyMuPDF | 1.27.2+ |
| **Evaluation** | RAGAS | 0.4.3+ |
| **Config Management** | python-dotenv | 1.2.2+ |

---

## 📁 File Structure Summary

```
RAG Book System/
│
├── 📄 Dokumentasi files (.md)
│   ├── DOKUMENTASI_ARSITEKTUR.md
│   ├── DOKUMENTASI_PIPELINE_INGESTION.md
│   ├── DOKUMENTASI_EMBEDDING_VECTORSTORE.md
│   ├── DOKUMENTASI_RETRIEVAL_RERANKING.md
│   ├── DOKUMENTASI_GENERATION.md
│   ├── DOKUMENTASI_API.md
│   ├── DOKUMENTASI_EVALUASI.md
│   ├── DOKUMENTASI_SCRIPTS_INTERFACE.md
│   └── INDEKS_DOKUMENTASI.md (this file)
│
├── 📁 config/                  # Konfigurasi terpusat
│   └── settings.py
│
├── 📁 embedding/               # Embeddings & vector store
│   ├── embedder.py
│   └── vector_store.py
│
├── 📁 retrieval/               # Search & reranking
│   ├── retriever.py
│   └── reranker.py
│
├── 📁 generation/              # LLM answer generation
│   └── answer_generator.py
│
├── 📁 api/                     # REST API
│   ├── app.py
│   └── routes/
│       ├── recommend.py
│       ├── deep.py
│       └── admin.py
│
├── 📁 parsing/                 # PDF parsing
│   └── pdf_parser.py
│
├── 📁 chunking/                # Text chunking
│   └── text_chunker.py
│
├── 📁 summarization/           # Book summarization
│   └── book_summarizer.py
│
├── 📁 evaluation/              # RAGAS & metrics
│   ├── ragas.py
│   ├── precision_k.py
│   └── run_evaluation.py
│
├── 📁 utils/                   # Utility functions
│   ├── logger.py
│   ├── file_utils.py
│   └── api_key_manager.py
│
├── 📁 scripts/                 # Maintenance scripts
│   ├── ingest_all.py
│   ├── add_book.py
│   ├── update_book.py
│   ├── delete_book.py
│   └── run_interface.ps1
│
├── 📁 interface/               # Web UI
│   ├── index.html
│   └── js/
│       ├── api.js
│       ├── chat.js
│       └── admin.js
│
├── 📁 data/                    # Data storage (gitignored)
│   ├── raw/                    # Raw PDFs
│   ├── metadata/               # books.json
│   ├── faiss/                  # FAISS indices
│   ├── ground_truth/           # Evaluation datasets
│   └── logs/                   # Runtime logs
│
├── 📁 tests/                   # Unit tests
│   ├── conftest.py
│   ├── test_embedder.py
│   ├── test_retriever.py
│   └── ...
│
├── 📁 logs/                    # Runtime logs (gitignored)
│
├── 📄 pyproject.toml           # Project config
├── 📄 requirements.txt         # Dependencies
├── 📄 .env                     # API keys (gitignored)
├── 📄 .gitignore              # Git ignore patterns
├── 📄 README.md               # Project README
└── 📄 run_api.py              # Entry point untuk API
```

---

## 🚀 Quick Start untuk Developers

### 1. Setup Environment

```bash
# Clone/navigate to project
cd /path/to/RAG\ Book

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Create .env file
cp .env.example .env

# Edit .env dan fill API keys:
GEMINI_API_KEY_1=...
GEMINI_API_KEY_2=...
JINA_API_KEY=...
OPENROUTER_API_KEY=...
```

### 3. Run Initial Ingestion

```bash
# Place PDFs in data/raw/
cp /path/to/books/*.pdf data/raw/

# Run ingestion pipeline
python scripts/ingest_all.py --batch_size 5
```

### 4. Start API Server

```bash
# Run Flask app
python run_api.py

# Server akan run di http://localhost:5000
```

### 5. Test Endpoints

```bash
# Recommendation
curl -X POST http://localhost:5000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "Buku fisika SMA gelombang"}'

# Deep Dive
curl -X POST http://localhost:5000/api/deep \
  -H "Content-Type: application/json" \
  -d '{"book_ids": ["book_123"], "question": "Apa rumus gaya sentripetal?"}'
```

---

## 📚 Referensi Documentation

### Internal References

- Semua dokumentasi dirancang untuk **modular** dan **self-contained**
- Setiap file bisa dibaca independently
- Cross-references menggunakan relative markdown links
- Code examples dalam pseudocode + actual code

### Conventions

- **Class/Method names**: `CamelCase` untuk class, `snake_case` untuk methods
- **File paths**: Use forward slashes (`/`) dan relative to project root
- **Terminal commands**: Bash syntax (translate ke Windows jika needed)
- **JSON examples**: Pretty-printed dengan indentation
- **Tables**: Markdown format untuk compatibility

---

## ✅ Checklist Implementasi

### Phase 1: Core Infrastructure
- [x] PDF parsing & text extraction
- [x] Text chunking & summarization
- [x] Embedding generation (Gemini API)
- [x] FAISS vector store management
- [x] Configuration management

### Phase 2: Retrieval & Ranking
- [x] FAISS similarity search
- [x] Metadata filtering (jenjang, kelas, mapel)
- [x] Jina AI reranking
- [x] Query filter extraction

### Phase 3: Generation & API
- [x] Answer generation dengan Gemini LLM
- [x] System prompts & guardrails
- [x] Flask API endpoints
- [x] Request/response formatting

### Phase 4: Evaluation & Monitoring
- [x] RAGAS evaluation framework
- [x] Precision@K metrics
- [x] Performance testing
- [x] Logging & monitoring

### Phase 5: Deployment & UI
- [x] Web interface (HTML + JavaScript)
- [x] Admin panel untuk book management
- [x] Docker containerization (optional)
- [x] Hugging Face Spaces deployment

---

## 🎯 Key Metrics to Track

### System Health
- API uptime (target: > 99%)
- Error rate (target: < 1%)
- Average latency (target: < 1.5s)
- Memory usage (target: < 500 MB)

### Quality Metrics
- RAGAS faithfulness score (target: > 0.85)
- Precision@5 untuk recommendations (target: > 0.70)
- User satisfaction (qualitative feedback)

### Usage Metrics
- Daily active users
- Queries per day
- Average queries per user
- API key rate limit utilization

---

## 📞 Support & Troubleshooting

### Common Issues

| Issue | Solution | Reference |
|-------|----------|-----------|
| API key quota exceeded | Rotate ke key lain, atau wait for reset | DOKUMENTASI_ARSITEKTUR.md |
| FAISS index not found | Run `scripts/ingest_all.py` untuk rebuild | DOKUMENTASI_SCRIPTS_INTERFACE.md |
| Slow search | Check FAISS index size, consider hard delete old entries | DOKUMENTASI_EMBEDDING_VECTORSTORE.md |
| Poor recommendation quality | Check RAGAS metrics, improve training data | DOKUMENTASI_EVALUASI.md |
| API 500 errors | Check logs in `logs/api.log` untuk error messages | DOKUMENTASI_API.md |

### Debugging Tips

1. **Enable verbose logging**: Set `LOG_LEVEL=DEBUG` di `.env`
2. **Run notebook**: Use `notebook.ipynb` untuk interactive debugging
3. **Check FAISS indices**: Verify dengan `summary_store.index.ntotal`
4. **Test API directly**: Use curl atau Postman untuk isolate issues
5. **Monitor resources**: Use `htop` atau Task Manager untuk check memory/CPU

---

## 📝 Notes untuk Future Development

### Potential Enhancements

- [ ] **Caching Layer**: Redis cache untuk frequently searched queries
- [ ] **Multi-language Support**: Extend ke languages lain beyond Indonesian
- [ ] **User Personalization**: Track user history untuk personalized recommendations
- [ ] **A/B Testing**: Experiment dengan different reranking models
- [ ] **Batch Processing**: Async task queue untuk long-running operations
- [ ] **Analytics Dashboard**: Real-time metrics visualization
- [ ] **Feedback Loop**: Collect user feedback untuk continuous improvement

### Performance Optimization

- [ ] Implement caching di FAISS search results
- [ ] Use approximate nearest neighbor search (ScaNN/Annoy) untuk 1M+ vectors
- [ ] Batch embedding requests untuk improved throughput
- [ ] Implement connection pooling ke external APIs
- [ ] Database indexing untuk metadata queries

### Security Enhancements

- [ ] API key management dengan rotation
- [ ] Rate limiting per IP/user
- [ ] Input validation & sanitization
- [ ] HTTPS enforcement di production
- [ ] Authentication/authorization layer

---

## 📖 Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Mei 2026 | Initial documentation |
| - | - | - |

---

## 🤝 Kontributor & Feedback

Dokumentasi ini dibuat untuk *Capstone Project* Sistem Rekomendasi Buku Berbasis RAG.

Untuk pertanyaan, klarifikasi, atau saran improvement:
- **Owner**: Student (Rumah Literasi Tambaksogra)
- **Feedback**: Dapat dikomunikasikan via project repository

---

**END OF DOCUMENTATION INDEX**

---
