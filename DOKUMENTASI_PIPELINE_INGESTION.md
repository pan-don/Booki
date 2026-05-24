# PIPELINE INGESTION DATA DAN PEMROSESAN

**Dokumentasi Teknis: Data Ingestion, Parsing, dan Chunking**

---

## Ikhtisar

Pipeline ingestion bertanggung jawab untuk:
1. **Parsing PDF**: Ekstraksi teks mentah dari file PDF
2. **Text Cleaning**: Normalisasi dan pembersihan teks
3. **Chunking**: Pembagian teks panjang menjadi chunks yang dapat diembed
4. **Metadata Extraction**: Ekstraksi metadata buku (judul, kelas, mata pelajaran, dll)

---

## 📁 Folder: `parsing/`

**Fungsi**: Ekstraksi teks dari file PDF dan konversi ke format terstruktur.

### File: `pdf_parser.py`

**Tujuan**: Parse PDF menggunakan PyMuPDF, ekstrak teks per halaman dengan struktur rapi.

#### Kelas: `PDFParser`

```python
class PDFParser:
    """Ekstrak teks dari PDF menggunakan PyMuPDF, output format ramping."""
    
    def __init__(self, pdf_path: str | Path)
    def parse() -> Dict[str, Any]
    def save_json(self, output_path: str | Path) -> None
```

**Method Details**:

| Method | Signature | Deskripsi | Return |
|--------|-----------|-----------|--------|
| `__init__` | `(pdf_path: str \| Path)` | Inisialisasi parser dengan path PDF | - |
| `parse()` | `() -> Dict` | Ekstrak semua teks per halaman | Dict dengan keys: `source`, `file_name`, `num_pages`, `pages` |
| `save_json()` | `(output_path: str \| Path)` | Simpan hasil parse ke JSON | - |

**Output Structure** (dari `parse()`):
```json
{
  "source": "absolute/path/to/file.pdf",
  "file_name": "buku_fisika_sma.pdf",
  "num_pages": 456,
  "pages": [
    {
      "page_num": 1,
      "text": "BAB 1: GELOMBANG\n\nGelombang adalah..."
    },
    {
      "page_num": 2,
      "text": "Dalam fisika, gelombang dapat..."
    }
  ]
}
```

**Helper Functions**:
- `parse_pdf_to_json(pdf_path, json_output)`: One-shot parsing ke JSON
- `parse_pdf_to_text(pdf_path) -> str`: Ekstrak seluruh teks sebagai string

**Teknologi**: PyMuPDF (fitz) untuk robust PDF handling

**Error Handling**:
- Validasi path file ada sebelum parsing
- Logging setiap tahap proses
- Graceful handling untuk PDF korup

---

## 📁 Folder: `chunking/`

**Fungsi**: Pembagian teks panjang menjadi overlapping chunks untuk embedding.

### File: `text_chunker.py`

**Tujuan**: Implement character-based sliding window chunking dengan support untuk overlap dan natural boundaries.

#### Function: `chunk_text()`

```python
def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,          # default 30,000 chars
    overlap: int = CHUNK_OVERLAP,          # default 1,000 chars
    metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]
```

**Parameters**:
- `text`: Teks input yang akan di-chunk
- `chunk_size`: Maksimal karakter per chunk (default 30KB)
- `overlap`: Jumlah karakter overlap antara chunks (untuk konteks)
- `metadata`: Dictionary metadata base yang akan ditambahkan ke setiap chunk

**Output Structure** (List of chunks):
```python
[
    {
        'text': 'Teks dari chunk ini...',
        'start': 0,                    # starting char index dalam original text
        'end': 30000,                  # ending char index (exclusive)
        'index': 0,                    # chunk order (0-based)
        'book_id': 'book_123',         # dari metadata
        'title': 'Fisika SMA Kelas X'  # dari metadata
    },
    {
        'text': 'Teks chunk berikutnya...',
        'start': 29000,                # overlap sebesar 1000 chars
        'end': 59000,
        'index': 1,
        'book_id': 'book_123',
        'title': 'Fisika SMA Kelas X'
    }
]
```

**Algoritma Chunking**:
1. **Character-based sliding window**: Loop dengan increment `chunk_size - overlap`
2. **Natural boundary detection**: Jika bukan akhir teks, cari space/newline dalam 20% terakhir chunk untuk menghindari cutting mid-word
3. **Empty chunk filtering**: Skip chunks kosong setelah strip

**Contoh Pseudocode**:
```
start = 0
chunk_index = 0

while start < text_length:
    end = min(start + chunk_size, text_length)
    
    if end < text_length:
        # Find natural boundary (space/newline) dalam last 20% of chunk
        for pos in range(end, end - lookback_range, -1):
            if text[pos] in (' ', '\n', '\t'):
                end = pos + 1
                break
    
    chunk = text[start:end].strip()
    if chunk not empty:
        chunks.append({
            'text': chunk,
            'start': start,
            'end': end,
            'index': chunk_index,
            **metadata
        })
        chunk_index += 1
    
    start = start + chunk_size - overlap
```

**Rationale dari Design**:
- **30KB chunk size**: Balance antara context size dan search efficiency
- **1000 char overlap**: Memastikan konteks berguna di boundary chunks
- **Natural boundary**: Menghindari cutting di tengah kalimat/kata

**Use Cases di RAG**:
- Untuk mode `/deep` (pencarian mendalam), chunks disimpan di fulltext index
- Untuk mode `/recommend`, hanya summary per buku yang disimpan

---

## 📁 Folder: `summarization/`

**Fungsi**: Pembuatan ringkasan otomatis per buku menggunakan LLM.

### File: `book_summarizer.py`

**Tujuan**: Ringkas setiap buku menjadi 300-400 kata menggunakan Google Gemini.

#### Kelas: `BookSummarizer`

**Komponen Utama**:
- Input: Full text of book
- LLM: Google Gemini 2.5 Flash
- Output: Structured JSON dengan summary dan metadata

**Key Methods**:
- `summarize(text, title, max_words=350)`: Generate summary
- `batch_summarize(book_list)`: Process multiple books
- Handling untuk token limits dan API rate limiting

**Prompt Template**:
```
Buatlah ringkasan singkat (300-400 kata) dari buku/materi pelajaran ini dalam bahasa Indonesia yang mudah dipahami.
Fokus pada:
1. Konsep utama
2. Topik yang dibahas
3. Manfaat/aplikasi praktis

Buku: {title}

[FULL TEXT HERE]

Ringkasan:
```

**Output Format**:
```json
{
    "book_id": "book_123",
    "title": "Fisika SMA Kelas X",
    "summary": "Ringkasan 300-400 kata dari buku...",
    "generated_at": "2026-05-23T10:30:00Z",
    "api_model": "gemini-2.5-flash"
}
```

**Integration Point**:
- Summary disimpan di database metadata
- Summary text di-embed dan disimpan di `summary_index.faiss`

---

## Pipeline Lengkap: Dari PDF ke Vector Store

### Diagram Alur

```
Raw PDF File
    ↓
PDFParser.parse()
    → Extract text per halaman
    → Output: JSON structure
    ↓
Text Cleaning (normalisasi whitespace, remove metadata halaman)
    ↓
BookSummarizer.summarize()
    → Generate 300-400 word summary
    → Output: Summary text
    ↓
Split into TWO pipelines:
    │
    ├─→ Summary Pipeline:
    │   ├─ Embed summary (Gemini Embedder)
    │   ├─ Add to summary_index.faiss
    │   └─ Store metadata (book_id, title, jenjang, kelas, dll)
    │
    └─→ Fulltext Pipeline:
        ├─ chunk_text() dengan 30KB chunks
        ├─ Embed setiap chunk
        ├─ Add to fulltext_index.faiss
        └─ Store chunk metadata (chunk_id, book_id, chunk_text, dll)
    
Result: Dua FAISS indices siap untuk retrieval
```

### Metadata yang Tersimpan per Buku

```
{
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
```

---

## Error Handling & Validation

### PDF Parsing
- ✅ Validasi file exists sebelum parse
- ✅ Handling untuk PDF dengan encoding berbeda
- ✅ Skip halaman kosong atau corrupted

### Chunking
- ✅ Validasi `chunk_size > 0`
- ✅ Warning jika `overlap >= chunk_size` dan auto-adjust
- ✅ Filter out empty chunks setelah text processing

### Summarization
- ✅ Retry logic dengan exponential backoff untuk API failures
- ✅ Fallback ke shorter summary jika token limit exceeded
- ✅ Error logging untuk books yang gagal di-summarize

---

## Performance Considerations

| Operasi | Kompleksitas | Waktu Estimasi | Notes |
|---------|-------------|-----------------|-------|
| Parse PDF (456 halaman) | O(n_pages) | ~2 detik | Linear dengan jumlah halaman |
| Text Cleaning | O(n_chars) | ~1 detik | Regex-based normalization |
| Chunking (200KB text) | O(n_chars) | ~0.5 detik | Single pass, character-based |
| Summarization (Gemini) | O(1) API call | ~5-10 detik | Network-bound |
| Embedding 1 summary | O(1) API call | ~0.5 detik | Gemini embedding API |
| Embedding 45 chunks | O(n_chunks) | ~20 detik | Batched API calls dengan retry |
| **Total per buku** | - | **~30-40 detik** | Parallelizable parts |

---

## Implementasi di Production

### Batch Processing Script

Pipeline ini dijalankan via `scripts/ingest_all.py` atau `scripts/add_book.py`:

```
For each PDF in data/raw/:
    1. Parse PDF → JSON
    2. Summarize → Summary text
    3. Chunk fulltext
    4. Embed all chunks + summary
    5. Add to FAISS indices
    6. Store metadata di JSON
    7. Log progress
```

### Soft Delete & Update

- **Soft Delete**: Mark `is_active=false` tanpa remove dari FAISS (ID tetap reserved)
- **Update**: Modify metadata + re-embed summary, fulltext chunks tetap (atau re-chunk jika content berubah)
- **Hard Delete**: Remove dari FAISS index (operasi maintenance offline)

---

