```
capstone-rag-buku/
│
├── .env                                 # API keys (GEMINI, OPENROUTER, JINA, dll)
├── .gitignore
├── requirements.txt
├── README.md
│
├── config/
│   ├── __init__.py
│   └── settings.py                      # baca .env, konfigurasi path, parameter model
│
├── data/                                # semua data disimpan di sini (ignore dari git)
│   ├── raw/                             # PDF hasil scraping
│   ├── processed/                       # teks hasil parsing per buku (txt)
│   ├── summaries/                       # ringkasan per buku (json/csv)
│   ├── metadata/                        # metadata buku (json/csv)
│   ├── chunks/                          # chunk teks lengkap per buku (json per buku)
│   ├── faiss/                           # FAISS index & mapping
│   │   ├── summary_index.faiss
│   │   ├── summary_id_map.pkl
│   │   ├── fulltext_index.faiss
│   │   └── fulltext_id_map.pkl
│   └── ground_truth/                    # dataset evaluasi (query, relevan books)
│
├── scraping/                            # ambil data dari SIBI
│   ├── __init__.py
│   ├── sibi_scraper.py                  # crawling daftar buku & download PDF
│   └── metadata_extractor.py            # ekstrak judul, kelas, jenjang, dll
│
├── parsing/                             # ekstrak teks dari PDF
│   ├── __init__.py
│   └── pdf_parser.py                    # PyMuPDF -> teks bersih
│
├── chunking/                            # bagi teks panjang untuk mode pendalaman
│   ├── __init__.py
│   └── text_chunker.py                  # sliding window, overlap, token-aware
│
├── summarization/                       # ringkas buku per buku (300-400 kata)
│   ├── __init__.py
│   └── gemini_summarizer.py             # panggil Gemini 2.5 Flash API
│
├── embedding/                           # generate vektor & kelola FAISS
│   ├── __init__.py
│   ├── embedder.py                      # wrapper Gemini embedding 2
│   └── vector_store.py                  # FAISS: add, search, update, delete (soft/hard)
│
├── retrieval/                           # pencarian & reranking
│   ├── __init__.py
│   ├── retriever.py                     # search FAISS + filter by book_ids (untuk fulltext)
│   └── reranker.py                      # Jina AI atau HuggingFace local
│
├── generation/                          # jawaban akhir dengan LLM
│   ├── __init__.py
│   └── answer_generator.py              # OpenRouter (Qwen3) + fallback model
│
├── api/                                 # Flask backend (deploy ke HF Spaces)
│   ├── __init__.py
│   ├── app.py                           # inisialisasi Flask, load komponen
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── recommend.py                 # POST /recommend
│   │   ├── deep.py                      # POST /deep (buku terpilih 1-5)
│   │   └── admin.py                     # POST /update (tambah/edit/hapus)
│   └── utils/
│       ├── __init__.py
│       └── session_cache.py             # simpan sementara pilihan buku (in-memory)
│
├── evaluation/                          # RAGAS & precision@k
│   ├── __init__.py
│   ├── ragas_eval.py                    # faithfulness, answer relevancy
│   └── precision_k.py                   # hitung precision@k rekomendasi
│
├── scripts/                             # pipeline offline & maintenance
│   ├── ingest_all.py                    # dari scraping sampai build FAISS (full ingest)
│   ├── update_book.py                   # tambah/edit/hapus satu buku
│   └── run_evaluation.py                # jalankan evaluasi dengan ground truth
│
├── utils/                               # fungsi bantu lintas modul
│   ├── __init__.py
│   ├── logger.py                        # logging setup
│   ├── file_utils.py                    # baca/tulis json, pkl, txt
│   └── text_cleaner.py                  # normalisasi teks hasil PDF
│
└── tests/                               # unit test (opsional)
    ├── test_retrieval.py
    ├── test_reranker.py
    └── test_embedding.py
```