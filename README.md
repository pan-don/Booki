# 📚 Sistem Rekomendasi Buku Edukasi RAG (Rumah Literasi Tambaksogra)

## 1. Ringkasan Eksekutif (Executive Summary)

Proyek ini merupakan **Sistem Backend _Retrieval-Augmented Generation_ (RAG)** yang dirancang dengan arsitektur _decoupled_ untuk melayani platform Rumah Literasi Tambaksogra. Infrastruktur ini dibangun secara eksklusif menggunakan kerangka kerja (framework) **Flask** dengan bahasa pemrograman Python 3.13, dan disiapkan untuk _deployment_ tingkat produksi (production-grade) pada lingkungan **Hugging Face Spaces**. Sistem ini menangani komputasi _Artificial Intelligence_ berat seperti ekstraksi vektor (embedding) dari dokumen PDF buku pelajaran, pencarian kemiripan semantik menggunakan **FAISS**, peringkatan ulang hierarkis menggunakan **Jina AI Reranker**, dan sintesis jawaban naratif komprehensif menggunakan _Large Language Model_ (LLM) **Google Gemini**.

Arsitektur backend ini diisolasi sepenuhnya dari antarmuka pengguna (Frontend). Akses data, rekomendasi kecerdasan buatan, dan kontrol operasional administratif difasilitasi seluruhnya melalui kumpulan REST API berkinerja tinggi yang diamankan oleh _Cross-Origin Resource Sharing_ (CORS) yang sangat ketat. Skema komunikasi diregulasi melalui variabel `FRONTEND_URL` untuk mengamankan sambungan ke layanan integrasi (seperti Cloudflare Pages).

Sistem ini memastikan ketahanan dan efisiensi melalui manajemen konsumsi sumber daya kunci API secara isolatif, di mana lalu lintas _ingestion_ (ekstraksi data) dan _query_ pengguna (Sesi Tanya Jawab Chatbot) berjalan melalui dua _pool_ yang diregulasi oleh mekanisme failover internal, secara drastis menurunkan risiko _rate limiting_ yang fatal secara silang.

---

## 2. Pemetaan Arsitektur Direktori (ASCII Tree Diagram)

Struktur repositori ini menggunakan pola _domain-driven design_ berbasis komponen, di mana setiap folder dan abstraksi mewakili lapisan eksekusi yang spesifik dan terkendali.

```text
├── api/                        # Lapisan Rute Aplikasi Utama (Application Routing Layer)
│   ├── app.py                  # Factory Inisialisasi Flask, injeksi dependensi, dan konfigurasi origin CORS.
│   └── routes/                 # Blueprint registrasi setiap Domain Endpoint.
│       ├── admin.py            # Rute untuk manajemen Ledger CRUD.
│       ├── deep.py             # Rute untuk eksplorasi halaman detail spesifik dari isi dokumen PDF.
│       └── recommend.py        # Rute tanya-jawab dinamis berbasis preferensi pengguna.
├── chunking/                   # Lapisan Pemrosesan Partisi Dokumen (Document Chunking Layer)
│   └── text_chunker.py         # Logika partisi dokumen 2048-token dengan metode rolling overlap.
├── config/                     # Lapisan Pengaturan Global (Global Configuration Layer)
│   └── settings.py             # Pusat sinkronisasi .env, fallback URL, file path statis, dan API Key Allocations.
├── data/                       # Lapisan Penyimpanan Data Internal (Internal Data Persistence Layer)
│   ├── faiss/                  # Direktori metrik basis data Vektor lokal.
│   │   ├── chunks_index_new.faiss  # Basis data Index untuk teks panjang (Deep Chunk).
│   │   ├── chunks_index_new.meta.pkl # Meta piksel penggabung untuk Deep Chunk.
│   │   ├── rec_index.faiss     # Basis data Index metrik pendek untuk pencarian rekomendasi.
│   │   └── rec_index.meta.pkl  # Meta piksel penggabung untuk Summary Vector.
│   └── raw/                    # Lapisan Ledger Utama berbasis File-System.
│       └── sibi_books.jsonl    # Satu-satunya Single Source of Truth bagi metadata buku.
├── embedding/                  # Lapisan Representasi Numerik AI (Vector Representation Layer)
│   ├── embedder.py             # Fasilitator pemanggilan koneksi Google Gemini Embeddings SDK (google.genai).
│   └── vector_store.py         # Abstraksi class pembaca/penulis index FAISS secara disk-based.
├── generation/                 # Lapisan Generator Sintesis (Synthesis Generation Layer)
│   └── answer_generator.py     # Orkestrator koneksi kepada Gemini LLM untuk membangun respons dialog naratif.
├── logs/                       # Lapisan Jejak Kesalahan & Status (Audit Logging Layer)
│   ├── api.log                 # Log utama terkait kegagalan transaksi, rotasi key manager, atau 400 Bad Requests.
│   └── ...                     # File log spesifik modul worker (add_book.log, delete_book.log, dll).
├── parsing/                    # Lapisan Pengekstraksi Dokumen Mentah (Document Extraction Layer)
│   ├── pdf_cleaner.py          # Utilitas RegExp untuk menghilangkan anomali teks hasil parsing.
│   └── pdf_parser.py           # Eksekutor pembaca format multi-page PDF menjadi single-string data mentah.
├── retrieval/                  # Lapisan Metrik Pencari Kembali (Retrieval & Reranking Layer)
│   ├── reranker.py             # Klien konektor menuju Jina AI Rerank API (v3) dengan threshold 0.60.
│   └── retriever.py            # Logika perhitungan Top-K dari FAISS, memadukan meta-filter JSONL dan Cosine Similarity.
├── scripts/                    # Lapisan Worker Automasi & Skrip Latar Belakang (Automation Worker Scripts)
│   ├── add_book.py             # Logika injeksi sinkron buku baru dan pembentukan indeks vektor.
│   ├── delete_book.py          # Logika pencabutan baris spesifik dan "soft delete" dari FAISS.
│   ├── update_book.py          # Logika pembaruan mutasi metadata yang menjaga integritas vektor deskriptif.
│   └── vacuum_vectorstore.py   # Pengutip sampah (Garbage Collector) untuk memampatkan FAISS setelah operasi delete.
├── utils/                      # Lapisan Perangkat Universal (Universal Utilities Layer)
│   ├── api_key_manager.py      # Pengelola siklus API dengan deteksi rate-limit dan _round-robin failover_.
│   ├── file_utils.py           # Operasi baca-tulis IO sederhana.
│   └── logger.py               # Konfigurator infrastruktur logging yang menstandarisasi output log Python.
├── pyproject.toml              # Definisi meta lingkungan sistem python.
├── requirements.txt            # Manifest ketergantungan (dependencies) eksplisit untuk proses bangun (build process).
├── run_api.py                  # Pintu gerbang utama eksekusi untuk meluncurkan Server WSGI Flask lokal.
└── uv.lock                     # Versi paket spesifik resolusi dependensi stabil untuk UV resolver.
```

---

## 3. Rincian Teknis & Fungsionalitas Operasional

### A. Rincian Infrastruktur Utama & Keamanan
Sistem ini memusatkan keamanan dengan mencegah **_Cross-Workload Exhaustion_**. `utils/api_key_manager.py` didesain untuk merotasi secara dinamis 17 API Key milik infrastruktur Rumah Literasi berdasarkan konfigurasi di `config/settings.py`. Terdapat pemisahan tegas di tingkat _dependency injection_ pada `api/app.py`:
- `create_gemini_embedding_key_manager()` dialokasikan kepada `GeminiEmbedder` pada indeks lingkungan (1-10) untuk injeksi file PDF.
- `create_gemini_qa_key_manager()` dialokasikan kepada `AnswerGenerator` pada indeks lingkungan (11-17) semata-mata untuk melayani pengalaman dialog responsif bagi _End User_ secara seketika (_Real Time_).
Di dalam `api/app.py`, integrasi CORS dengan ketat memberlakukan validasi `Origin` terhadap varibabel `FRONTEND_URL`, dan mengunci verb HTTP kepada operasi terdaftar (GET, POST, PUT, DELETE, OPTIONS). Permintaan dari domain tidak terdaftar akan gagal melewati _pre-flight_ standar peramban.

### B. Ledger RAG (File-Based Transactional Database)
Pusat dari _Source of Truth_ seluruh aplikasi dideklarasikan di dalam file `data/raw/sibi_books.jsonl`. Keputusan untuk menggunakan ekstensi berbasis baris (`JSON Lines`) dimaksudkan agar sistem Flask dapat melakukan eksekusi mutasi (CRUD) melalui skrip administrasi latar belakang (`scripts/*.py`) secara stabil dan ramah memori (tidak melahap RAM untuk memuat list JSON secara seutuhnya) sambil menolerir pemotongan (slicing) cepat bagi mekanisme Pagination halaman _frontend dashboard_. Vektor hasil turunan dari baris mentah ini diproyeksikan dan diindeksasi menggunakan teknologi FAISS ke path yang baru, yaitu `chunks_index_new.faiss`.

### C. Mekanisme Graceful Degradation
Seluruh alur pipa RAG di backend, mulai dari `api/app.py` hingga konektor REST, dirancang menggunakan arsitektur blok `try-except` berlapis (graceful degradation). Apabila terjadi kasus sistem yang meresahkan seperti hilangnya file vektor atau file metadata yang berada dalam masa transisi transfer dari sistem komputasi lokal menuju Hugging Face Spaces secara sinkronus, server merespons HTTP `200` atau memulihkan konteks LLM menggunakan fallback jawaban yang ramah, menghindarkan aplikasi dari keadaan macet pada HTTP `500 Server Error`.

---

## 4. Panduan Operasional Skrip Utama (Server Backend)

### Menginstalasi Lingkungan dan Dependensi Python
Struktur repositori direkayasa agar sinkron dengan pengelola virtual environment berkinerja tinggi, **uv**.
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Meluncurkan Lingkungan Server Lokal
Terdapat dua cara untuk meluncurkan antarmuka peladen REST API, bergantung pada kebutuhan konfigurasi lingkungan Anda:
**Via WSGI Flask (Port 5000):**
```bash
python run_api.py
```
**Atau menggunakan Gunicorn (Skala Produksi Lanjut):**
```bash
gunicorn -w 4 -b 0.0.0.0:7860 api.app:create_app()
```

### Mengelola Dataset Metadata
Sistem membebankan administrasi CRUD utama pada antarmuka rute REST API, akan tetapi pengembang _Back End_ dapat memanggil skrip manipulasi secara absolut melalui antar-muka Command Line. Sebagai contoh (injeksi sinkron tanpa UI):
```bash
python scripts/add_book.py --id <book_id>
```

Silakan menuju `DOKUMENTASI_SINKRONISASI.md` untuk perincian Payload Schema dan petunjuk integrasi penuh untuk tim Pengembang Antarmuka Next.js.
