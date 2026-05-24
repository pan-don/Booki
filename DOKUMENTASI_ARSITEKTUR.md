# DOKUMENTASI ARSITEKTUR SISTEM REKOMENDASI BUKU BERBASIS RAG

**Sistem Rekomendasi Buku Berbasis Retrieval-Augmented Generation (RAG) pada Koleksi Buku**

*Rumah Literasi Tambaksogra*

**Tanggal Dokumentasi**: Mei 2026  
**Status Proyek**: Capstone  
**Target Audience**: Data Science Student (Python, LLM Architecture, Advanced Concepts)

---

## 📋 DAFTAR ISI

1. [Ringkasan Eksekutif](#ringkasan-eksekutif)
2. [Arsitektur Sistem Secara Keseluruhan](#arsitektur-sistem-secara-keseluruhan)
3. [Modul Konfigurasi dan Utilitas](#modul-konfigurasi-dan-utilitas)
4. [Pipeline Ingestion Data](#pipeline-ingestion-data)
5. [Layer Embedding dan Vector Store](#layer-embedding-dan-vector-store)
6. [Layer Retrieval dan Reranking](#layer-retrieval-dan-reranking)
7. [Layer Generasi Jawaban](#layer-generasi-jawaban)
8. [API Backend dan Routes](#api-backend-dan-routes)
9. [Modul Evaluasi](#modul-evaluasi)
10. [Skrip dan Interface](#skrip-dan-interface)

---

## RINGKASAN EKSEKUTIF

### Visi Sistem

Sistem ini dirancang untuk memberikan rekomendasi buku pelajaran yang **akurat dan kontekstual** kepada pengguna (siswa, guru, orang tua) dari komunitas literasi Rumah Literasi Tambaksogra. Dengan memanfaatkan **Retrieval-Augmented Generation (RAG)**, sistem menggabungkan:

- **Pencarian Semantik**: Menggunakan embedding vectors untuk memahami konteks kueri
- **Reranking Berbasis Relevansi**: Menggunakan Jina AI untuk mengurutkan hasil berdasarkan relevansi
- **Generasi Respons Berbasis LLM**: Menggunakan Google Gemini untuk menghasilkan jawaban yang friendly dan edukatif

### Fitur Utama

1. **Rekomendasi Buku Berbasis Preferensi** (`/recommend`): Memberikan rekomendasi top-5 buku berdasarkan query teks pengguna
2. **Pencarian Mendalam (Deep Dive)** (`/deep`): Menjawab pertanyaan spesifik dalam konteks 1-5 buku pilihan
3. **Manajemen Admin** (`/admin`): Menambah, mengedit, atau menghapus buku dari koleksi
4. **Evaluasi Sistem**: Menggunakan RAGAS untuk mengukur faithfulness, answer relevancy, dan precision@k

### Stack Teknologi

| Komponen | Teknologi | Fungsi |
|----------|-----------|--------|
| **Embedding** | Google Gemini 2.5 (gemini-embedding-2) | Konversi teks ke vektor (3072 dimensi) |
| **Vector Database** | FAISS (IndexFlatIP) | Penyimpanan dan pencarian vektor dengan cosine similarity |
| **Reranking** | Jina AI (Reranker v3) | Mengurutkan hasil berdasarkan relevansi semantik |
| **LLM Generasi** | Google Gemini 2.5 Pro (via genai library) | Pembuatan jawaban dan rekomendasi |
| **Backend API** | Flask 3.1.3 | REST API framework |
| **PDF Processing** | PyMuPDF (fitz) | Ekstraksi teks dari file PDF |
| **Logging & Config** | Python-dotenv, Custom Logger | Manajemen konfigurasi dan logging |

---

## ARSITEKTUR SISTEM SECARA KESELURUHAN

### Diagram Alur Data

```
┌─────────────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                                 │
│  (Web Frontend / CLI / Sistem Eksternal)                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   FLASK API      │ (api/app.py)
                    │  ┌────────────┐  │
                    │  │ /recommend │  │ (routes/recommend.py)
                    │  │ /deep      │  │ (routes/deep.py)
                    │  │ /admin     │  │ (routes/admin.py)
                    │  └────────────┘  │
                    └────────────┬─────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
    ┌─────▼──────┐         ┌─────▼──────┐        ┌─────▼──────┐
    │  EMBEDDER  │         │ RETRIEVER  │        │ RERANKER   │
    │ (Gemini)   │         │ (FAISS)    │        │ (Jina AI)  │
    │            │         │            │        │            │
    │ - embed_   │         │ - search_  │        │ - rerank   │
    │   text()   │         │   summary()│        │ ()         │
    │            │         │ - search_  │        │            │
    │ - key      │         │   fulltext │        │ - API call │
    │   rotation │         │   _by_book │        │            │
    │            │         │   _ids()   │        │            │
    └──────┬─────┘         └──────┬─────┘        └──────┬─────┘
           │                      │                     │
           │          ┌───────────┼──────────────┐      │
           │          │                          │      │
           │    ┌─────▼─────────┐         ┌─────▼──────┐
           │    │ VECTOR STORE  │         │ ANSWER     │
           │    │               │         │ GENERATOR  │
           │    │ Summary Index │         │            │
           │    │ Fulltext Index│         │ (Gemini)   │
           │    └───────────────┘         └────────────┘
           │
    ┌──────▼─────────────────────────────────┐
    │ EXTERNAL API SERVICES                  │
    │ - Google Gemini API (Embedding, LLM)   │
    │ - Jina AI Rerank API                   │
    │ - OpenRouter API (fallback LLM)        │
    └────────────────────────────────────────┘
```

### Alur Pipeline RAG

#### Mode 1: Rekomendasi Buku (Recommendation)
```
User Query
    ↓
Embed Query (Gemini Embedder)
    ↓
Search Summary Index (FAISS, k=20)
    ↓
Rerank Results (Jina AI, top=5)
    ↓
Generate Recommendation Answer (Gemini)
    ↓
Return Books + Recommendation Answer
```

#### Mode 2: Pencarian Mendalam (Deep Dive)
```
Selected Book IDs + Question
    ↓
Embed Question (Gemini Embedder)
    ↓
Search Fulltext Index (FAISS, filter by book_ids, k=20)
    ↓
Rerank Chunks (Jina AI, top=5)
    ↓
Generate Detailed Answer (Gemini, dengan konteks chunks)
    ↓
Return Answer + Source References
```

#### Mode 3: Admin Operations
```
Add/Update/Delete Request
    ↓
Validate Book Metadata
    ↓
Update Vector Store (add/soft-delete)
    ↓
Persist Changes (FAISS + Metadata)
    ↓
Return Success/Error Response
```

---

## MODUL KONFIGURASI DAN UTILITAS

### 📁 Folder: `config/`

**Fungsi**: Manajemen konfigurasi terpusat, API keys, dan path file untuk seluruh sistem.

#### File: `settings.py`

**Tujuan**: Load environment variables dari `.env` dan define konfigurasi global.

**Key Components**:

| Variabel | Deskripsi | Default | Tipe |
|----------|-----------|---------|------|
| `GEMINI_API_KEY` | List dari 17 Gemini API keys untuk load balancing | dari `.env` | List[str] |
| `GEMINI_MODEL` | Model untuk summarization dan answer generation | `gemini-2.5-flash` | str |
| `EMBEDDING_MODEL` | Model untuk text embedding | `gemini-embedding-2` | str |
| `EMBEDDING_DIM` | Dimensi output embedding | `3072` | int |
| `ANSWER_MODEL` | Model untuk detailed answer generation | `gemini-2.5-pro` | str |
| `OPENROUTER_API_KEY` | API key untuk fallback LLM (OpenRouter) | dari `.env` | str |
| `LLM_MODEL` | Fallback LLM model di OpenRouter | `openrouter/qwen-3-7b` | str |
| `JINA_API_KEY` | API key untuk Jina Reranker | dari `.env` | str |
| `JINA_RERANK_MODEL` | Model reranker Jina | `jina-reranker-v3` | str |
| `CHUNK_SIZE` | Ukuran chunk teks (karakter) | `30000` | int |
| `CHUNK_OVERLAP` | Overlap antar chunk (karakter) | `1000` | int |
| `MIN_PARAGRAPH_LEN` | Minimal panjang paragraf | `30` | int |
| `MIN_CHUNK_LEN` | Minimal panjang chunk setelah splitting | `1000` | int |

**Paths yang didefinisikan**:
- `BASE_DIR`: Root directory proyek
- `DATA_DIR`: Folder penyimpanan semua data
- `FAISS_DIR`: Folder FAISS indices
- `METADATA_FILE`: JSON file metadata buku

**Inisitalisasi Otomatis**: Membuat direktori yang diperlukan jika belum ada.

---

### 📁 Folder: `utils/`

**Fungsi**: Utilitas lintas modul untuk logging, file management, dan API key management.

#### File: `logger.py`

**Tujuan**: Konfigurasi logging yang konsisten di seluruh aplikasi.

**Komponen Utama**:
- `configure_root_logger()`: Setup root logger dengan file output
- `get_logger(name)`: Mendapatkan logger untuk modul tertentu
- Output format: `[TIMESTAMP] [LEVEL] [MODULE] MESSAGE`

#### File: `file_utils.py`

**Tujuan**: Helper functions untuk operasi file (JSON, JSONL, Pickle).

**Fungsi Utama**:
- `read_json(path)`: Baca file JSON
- `write_json(path, data)`: Tulis file JSON
- `stream_jsonl(path)`: Iterasi JSONL file
- `read_pickle(path)`: Baca file pickle
- `write_pickle(path, data)`: Tulis file pickle

#### File: `api_key_manager.py`

**Tujuan**: Manajemen API keys dengan load balancing dan error recovery.

**Fitur Utama**:
- **Key Rotation**: Mengalihkan ke key berikutnya jika terjadi error
- **Round-Robin Load Balancing**: Distribusi request ke multiple keys
- `get_current_key()`: Ambil key yang saat ini aktif
- `report_error(key, error_msg)`: Laporkan error untuk key tertentu
- Auto-skip key yang sering error

---

