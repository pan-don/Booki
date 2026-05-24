# SKRIP MAINTENANCE DAN INTERFACE

**Dokumentasi Teknis: Batch Processing, Management Scripts, dan User Interface**

---

## Ikhtisar

Folder `scripts/` menyediakan tools untuk:
1. **Batch Ingestion**: Ingest semua PDF sekaligus ke FAISS
2. **Book Management**: Tambah/update/hapus buku individual
3. **Evaluation Running**: Jalankan RAGAS + Precision@K tests
4. **Interface Serving**: Serve web frontend

---

## 📁 Folder: `scripts/`

**Fungsi**: Offline processing dan system administration scripts.

---

### File: `ingest_all.py`

**Tujuan**: Full pipeline ingestion dari raw PDFs ke FAISS indices (initial setup atau rebuild).

#### Function: `ingest_all_pipeline()`

```python
def ingest_all_pipeline(
    pdf_directory: Path = DATA_DIR / "raw",
    output_faiss_dir: Path = FAISS_DIR,
    batch_size: int = 5,
    max_books: Optional[int] = None
) -> Dict[str, Any]
```

**Fungsi**: Process semua PDFs dalam folder, generate embeddings, build FAISS indices.

**Processing Steps**:

```
For each PDF in pdf_directory:
    1. Parse PDF → extract text (PDFParser)
    2. Summarize full text → 300-400 words (BookSummarizer)
    3. Chunk fulltext → overlapping chunks (text_chunker)
    4. Embed summary → vector (GeminiEmbedder)
    5. Embed all chunks → vectors (batched)
    6. Add summary to SummaryVectorStore
    7. Add chunks to FulltextVectorStore
    8. Save metadata to JSON
    9. Log progress
```

**Parameters**:
- `pdf_directory`: Folder containing raw PDF files
- `output_faiss_dir`: Where to save FAISS indices
- `batch_size`: Number of PDFs to process in parallel
- `max_books`: Limit untuk testing (None = process all)

**Return**:
```python
{
    "status": "success" | "partial" | "failed",
    "total_books_processed": 45,
    "successful": 44,
    "failed": 1,
    "summary_index_size": 44,
    "fulltext_index_size": 1980,  # 44 books × ~45 chunks
    "failed_books": ["corrupted.pdf"],
    "duration_seconds": 1234.5,
    "metadata_file": "data/metadata/books.json"
}
```

**Error Handling**:
```python
for pdf_file in pdf_files:
    try:
        # Full processing pipeline
        process_single_book(pdf_file)
    except PDFParseError as e:
        logger.error(f"Failed to parse {pdf_file}: {e}")
        failed_books.append(pdf_file)
    except EmbeddingError as e:
        logger.error(f"Failed to embed {pdf_file}: {e}")
        failed_books.append(pdf_file)
    except Exception as e:
        logger.error(f"Unexpected error processing {pdf_file}: {e}")
        failed_books.append(pdf_file)

# Continue dengan remaining books despite errors
```

**Usage**:
```bash
python scripts/ingest_all.py \
  --pdf_dir data/raw \
  --batch_size 5 \
  --max_books 50  # For testing
```

---

### File: `add_book.py`

**Tujuan**: Add single book ke collection (atau update if exists).

#### Function: `add_single_book()`

```python
def add_single_book(
    pdf_path: Path | str,
    title: str,
    author: Optional[str] = None,
    jenjang: str = "SMA/MA/SMK/MAK",
    kelas: Optional[List[str]] = None,
    mata_pelajaran: str = "Umum"
) -> Dict[str, Any]
```

**Processing**:
```
1. Validate PDF exists
2. Check if book already in collection (by title)
   - If exists: offer update or skip
   - If new: proceed dengan add
3. Parse PDF → summarize
4. Chunk + embed
5. Add to FAISS indices
6. Update metadata JSON
7. Return success with book_id
```

**Return**:
```python
{
    "status": "success" | "already_exists" | "error",
    "book_id": "book_xyz",
    "title": "...",
    "num_chunks": 45,
    "summary_length": 387,
    "message": "Book added successfully"
}
```

**Usage**:
```bash
python scripts/add_book.py \
  --pdf "data/raw/buku_baru.pdf" \
  --title "Kimia SMA Kelas XI" \
  --author "Dr. Sains" \
  --jenjang "SMA/MA/SMK/MAK" \
  --kelas "11,XI" \
  --mapel "Kimia"
```

---

### File: `update_book.py`

**Tujuan**: Update metadata atau content buku yang sudah ada.

#### Function: `update_book_metadata()`

```python
def update_book_metadata(
    book_id: str,
    new_title: Optional[str] = None,
    new_author: Optional[str] = None,
    new_jenjang: Optional[str] = None,
    new_kelas: Optional[List[str]] = None,
    new_mapel: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Dict[str, Any]
```

**Processing**:
```
1. Find book by book_id in metadata
2. Validate book exists
3. Update specified fields
4. If content changed: re-generate summary + re-embed
5. Save to JSON
6. Return success
```

---

### File: `delete_book.py`

**Tujuan**: Soft delete atau hard delete buku dari collection.

#### Function: `delete_book()`

```python
def delete_book(
    book_id: str,
    hard_delete: bool = False
) -> Dict[str, Any]
```

**Processing**:
- **Soft Delete** (default): Mark `is_active=false` in metadata
- **Hard Delete**: Remove dari FAISS + metadata

---

### File: `run_interface.ps1`

**Tujuan**: PowerShell script untuk start web interface locally.

**Content**:
```powershell
# run_interface.ps1
# Start Flask API server + serve frontend

Write-Host "Starting RAG Book Recommendation System..." -ForegroundColor Green

# Start Flask backend
Write-Host "Starting Flask backend on port 5000..." -ForegroundColor Cyan
Start-Process python -ArgumentList "run_api.py" -NoNewWindow

# Wait untuk Flask startup
Start-Sleep -Seconds 3

# Start simple HTTP server untuk frontend
Write-Host "Starting frontend server on port 8000..." -ForegroundColor Cyan
Push-Location interface
python -m http.server 8000
Pop-Location
```

**Usage**:
```bash
.\scripts\run_interface.ps1
# Frontend: http://localhost:8000
# Backend API: http://localhost:5000
```

---

## 📁 Folder: `interface/`

**Fungsi**: Web-based user interface untuk RAG system.

---

### File: `index.html`

**Tujuan**: Main web page dengan 2 modes: Recommendation dan Deep Dive.

**Components**:
1. **Header**: Logo, title, about
2. **Mode Selector**: Toggle antara `/recommend` dan `/deep`
3. **Recommendation Mode**:
   - Query input field
   - Filter options (jenjang, kelas, mapel)
   - Submit button
   - Results display (top 5 books)
4. **Deep Dive Mode**:
   - Book selector (multi-select)
   - Question input field
   - Submit button
   - Answer + sources display

**Responsive Design**:
- ✅ Mobile-friendly (responsive CSS)
- ✅ Dark mode support
- ✅ Accessibility (WCAG compliance)

---

### Folder: `js/`

**JavaScript modules untuk frontend logic.**

#### File: `api.js`

```javascript
// api.js - API client untuk communicate dengan backend

async function makeRecommendationRequest(query, filters = {}) {
    const response = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: query,
            filter_jenjang: filters.jenjang || [],
            filter_kelas: filters.kelas || [],
            filter_mapel: filters.mapel || []
        })
    });
    
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return await response.json();
}

async function makeDeepDiveRequest(bookIds, question) {
    const response = await fetch('/api/deep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            book_ids: bookIds,
            question: question
        })
    });
    
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return await response.json();
}
```

#### File: `chat.js`

```javascript
// chat.js - UI handlers untuk chat-like experience

const chatContainer = document.getElementById('chat-container');

async function handleUserQuery(query) {
    // Add query to chat
    displayMessage(query, 'user');
    
    // Get recommendation
    try {
        const result = await makeRecommendationRequest(query);
        displayRecommendations(result.recommendations);
        displayMessage(result.answer, 'assistant');
    } catch (error) {
        displayMessage(`Error: ${error.message}`, 'error');
    }
}

function displayMessage(text, role) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.textContent = text;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}
```

#### File: `admin.js`

```javascript
// admin.js - Admin panel untuk book management

async function addBook(formData) {
    const response = await fetch('/api/admin/add', {
        method: 'POST',
        body: new FormData(formData)
    });
    return await response.json();
}

async function deleteBook(bookId) {
    const response = await fetch('/api/admin/delete', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ book_id: bookId })
    });
    return await response.json();
}
```

---

## 📁 Folder: `data/`

**Data storage dengan subdirectories untuk different artifact types.**

### Struktur:

```
data/
├── raw/                    # Raw PDFs (dari scraping atau manual upload)
│   ├── buku_1.pdf
│   ├── buku_2.pdf
│   └── ...
│
├── metadata/               # Book metadata JSON
│   └── books.json          # {book_id → metadata dict}
│
├── faiss/                  # FAISS indices
│   ├── summary_index.faiss
│   ├── summary_index.meta.pkl
│   ├── fulltext_index.faiss
│   └── fulltext_index.meta.pkl
│
├── ground_truth/           # Evaluation datasets
│   ├── ragas_queries.jsonl
│   └── precision_queries.jsonl
│
└── logs/                   # API logs (gitignored)
    ├── api.log
    └── processing.log
```

### `metadata/books.json` Schema:

```json
{
    "book_123": {
        "book_id": "book_123",
        "title": "Fisika SMA Kelas X",
        "author": "Tim Gemilang",
        "jenjang": "SMA/MA/SMK/MAK",
        "kelas": ["X"],
        "mata_pelajaran": "Fisika",
        "summary": "Ringkasan 300-400 kata...",
        "num_pages": 456,
        "num_chunks": 45,
        "is_active": true,
        "created_at": "2026-05-23T10:30:00Z",
        "updated_at": "2026-05-23T10:30:00Z"
    }
}
```

---

## 📁 Folder: `logs/`

**Runtime logs dari API dan processing.**

**Tidak di-track dalam git** (add ke `.gitignore`).

**Log Files**:
- `api.log`: Flask request/response logs
- `processing.log`: Batch processing logs
- `error.log`: Error logs (consolidated)

**Rotation Strategy**:
```python
# Using Python logging handlers
RotatingFileHandler(
    filename="logs/api.log",
    maxBytes=10_000_000,  # 10 MB
    backupCount=5         # Keep 5 old files
)
```

---

## Notebook untuk Exploration

### File: `notebook.ipynb`

**Tujuan**: Jupyter notebook untuk interactive exploration dan debugging.

**Typical Cells**:

```python
# Cell 1: Setup & imports
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))

from embedding.embedder import GeminiEmbedder
from embedding.vector_store import SummaryVectorStore, FulltextVectorStore
from retrieval.retriever import Retriever
from retrieval.reranker import Reranker
from generation.answer_generator import AnswerGenerator

# Cell 2: Initialize components
embedder = GeminiEmbedder()
summary_store = SummaryVectorStore("data/faiss/summary_index.faiss", dimension=3072)
fulltext_store = FulltextVectorStore("data/faiss/fulltext_index.faiss", dimension=3072)
retriever = Retriever(summary_store, fulltext_store)
reranker = Reranker()
answer_gen = AnswerGenerator()

# Cell 3: Test recommendation flow
query = "Buku fisika tentang gelombang SMA"
query_vector = embedder.embed_text(query)
results = retriever.search_summary(query, query_vector, top_k=20)
reranked = reranker.rerank_results(query, results, text_field='summary_text', top_n=5)
print(f"Top recommendation: {reranked[0]['title']}")

# Cell 4: Test deep dive
question = "Apa rumus gaya sentripetal?"
question_vector = embedder.embed_text(question)
chunks = retriever.search_fulltext_by_book_ids(question, question_vector, 
                                                book_ids=['book_123'], top_k=20)
reranked_chunks = reranker.rerank_results(question, chunks, 
                                          text_field='chunk_text', top_n=5)
answer = answer_gen.generate_deep_answer(question, 
                                         selected_books=[{'book_id': 'book_123', 'title': '...'}],
                                         retrieved_chunks=reranked_chunks)
print(answer)
```

---

## Best Practices untuk Scripts & Maintenance

### Data Management

1. ✅ **Backup Before Operations**: Backup FAISS indices sebelum rebuild
2. ✅ **Soft Delete Default**: Gunakan soft delete untuk undo capability
3. ✅ **Version Metadata**: Track metadata versions untuk audit trail
4. ✅ **Clean Up Logs**: Rotate logs untuk prevent disk space issues

### Processing Safety

1. ✅ **Error Recovery**: Continue processing despite individual book failures
2. ✅ **Progress Tracking**: Log progress regularly untuk monitor long-running tasks
3. ✅ **Validation**: Validate inputs sebelum processing
4. ✅ **Atomic Operations**: Either fully succeeds atau fully reverts

### Performance

1. ✅ **Batch Processing**: Process multiple books together untuk efficiency
2. ✅ **Parallel Embedding**: Embed multiple chunks simultaneously
3. ✅ **Connection Pooling**: Reuse API connections untuk reduce latency
4. ✅ **Caching**: Cache commonly used data (metadata, embeddings)

---

