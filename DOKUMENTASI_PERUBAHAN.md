## 📄 Dokumentasi Perubahan Sistem

### Latar Belakang Perubahan
Sistem *RAG Backend* Rumah Literasi Tambaksogra sebelumnya diatur dengan `CHUNK_SIZE` yang terlalu besar, yakni **30.000 karakter**. Karena lapisan reranking sistem menggunakan Jina AI (`jina-reranker-v3`) yang memberlakukan batas konteks masukan maksimum yang sangat ketat sebesar **8.192 token**, ukuran chunk sebelumnya terpotong secara paksa di batas API dan gagal diproses maknanya.

Hal ini mengakibatkan banyak data hilang yang tidak terbaca oleh sistem Reranking ("Lost in the Middle"). Dengan memigrasikan ukuran menjadi **2.048 karakter**, lapisan vektor dapat mencakup data secara sangat *granular* yang dijamin terbaca utuh dan harmonis oleh limit token dari Jina AI, serta diproses sempurna oleh *Gemini Embedding* untuk perhitungan kosinus similaritas yang presisi.

### Spesifikasi Teknis Baru

| Parameter | Versi Lama | Versi Baru (Optimal) |
| --- | --- | --- |
| **Chunk Size** | 30.000 karakter | **2.048 karakter** |
| **Chunk Overlap** | 1.000 karakter | **250 karakter** |
| **Min Chunk Length** | 1.000 karakter | **500 karakter** |
| **Min Paragraph Length**| 30 karakter | 30 karakter |
| **Vector Output Path** | `data/faiss/fulltext_index.faiss` | **`data/faiss/chunks_index.faiss`** |

### Dampak Performa
-   **Akurasi Pencarian (*Retrieval Accuracy*)**: Meningkat signifikan karena Reranker menerima teks yang padat, utuh, dan relevan di mana relasi antara kata secara utuh bisa diukur tanpa terkena pemotongan token pada batas API layer Jina.
-   **Latensi (*Latency*)**: Pencarian menjadi lebih cepat secara komputasi reranker karena data yang disuplai per chunk sudah bersih dan sesuai porsinya.
-   **Jejak Memori (*Memory Footprint*)**: Terdapat pertambahan penggunaan file index secara ukuran (`.faiss` lebih besar mengingat vektor indeks memuat lebih banyak chunk baru). Namun, untuk antisipasi OOM pada *embedding*, script migrasi diproses dalam pola *chunk batching* berisi 100 elemen sehingga penggunaan RAM tetap mendatar (flat) dan tidak meledak di tengah *runtime*.

### Panduan Maintenance Offline
Bila ingin memicu atau meriset ulang proses pembentukan Indeks Vektor secara offline di kemudian hari, ikuti langkah berikut:
1. Pastikan Anda memiliki *virtual environment* Python yang sudah aktif (`source .venv/bin/activate`).
2. Masukkan dan sediakan API Keys secara valid ke dalam environment (`.env`).
3. Jalankan script migrasi secara manual via *Command Line / Bash*:
   ```bash
   python3 scripts/rechunk_fulltext.py
   ```
4. Script secara mandiri akan memuat (`load`) metadata JSONL dari `data/raw/sibi_books.jsonl`, membentuk indeks vektor secara modular (terhindar dari rate-limits), dan mengunci database FAISS akhir Anda secara atomik (*Atomic Swap*) menimpa *live-index* dengan nama `chunks_index.faiss` dan metadatanya `chunks_index.meta.pkl`. Status berhasil akan tertulis di log pada folder `logs/rechunk_migration.log`.
## 📄 Dokumentasi Perubahan Sistem: Phase 2

### Latar Belakang & Masalah Utama
Pada fase sebelumnya, sistem memiliki dua titik kelemahan krusial:
1. **Empty Search Results (Post-Filtering Hazard):** Metode retrieval awal (`Retriever.search_summary()`) hanya menarik sejumlah kecil dokumen (top 20) secara _raw_ dari _vector store_ FAISS sebelum tahap filtering metadata (jenjang, kelas, mata pelajaran). Jika 20 dokumen teratas ini gagal memenuhi kriteria metadata pengguna, pencarian akan mengembalikan daftar kosong meskipun buku relevan lainnya tersedia lebih jauh di dalam database.
2. **Coupled UI Data & Text Response:** Respons `answer` dari API `/api/recommend` digunakan sebagai muatan penuh dari LLM yang merangkum keseluruhan data JSON. Hal ini menghabiskan token (inefisien), berisiko _hallucination_, dan mengunci frontend sehingga tidak bisa me-render komponen visual antarmuka/UI yang modular dan elegan.

### Spesifikasi Arsitektur Logika Baru
Untuk mengatasi masalah tersebut, berikut aliran pemrosesan yang dipisahkan:
1. **Ekspansi Pooling FAISS:** Fungsi `search_summary` dan `search_fulltext` telah diatur untuk menarik `initial_k = 100` dokumen. Hal ini menjamin variabilitas dan ketersediaan kandidat pre-filter yang lebih luas bagi reranker.
2. **Reranker Otomatis dengan Threshold Dinamis:** Alih-alih mengembalikan `top_5` secara statis, rekomendasi disaring (post-rerank) secara dinamis menggunakan nilai minimum kecocokan skor `relevance_score >= 0.60`.
3. **Decoupling Data JSON & Narasi:** Proses REST API memetakan langsung data internal (seperti `link_sampul` pada indeks menjadi `cover_image`) di dalam array `recommendations`.
4. **Instruksi Rigid LLM:** LLM Prompt pada `AnswerGenerator` diperintahkan secara absolut untuk tidak merepetisi kerangka (_bullet points_, daftar pustaka, dsb.), dan hanya fokus menjadi perantara komunikasi sapaan ramah (_chat interface_).

### Tabel Spesifikasi Payload API

| Elemen Request (POST `/recommend`) | Tipe | Contoh / Keterangan |
| --- | --- | --- |
| `query` | string | "Buku fisika SMA kelas 10" |

**Contoh Struktur JSON Response Berhasil (200 OK):**
```json
{
  "answer": "Halo Sobat Belajar! ✨ Wah, kamu sedang mencari materi tentang Fisika, ya? Aku sudah menemukan buku keren yang pas dengan kriteria kamu. Yuk, dipelajari! 😊",
  "recommendations": [
    {
      "book_id": "848a47b...",
      "title": "Fisika Dasar 1",
      "author": "Anonim",
      "cover_image": "https://url.ke/gambar.jpg",
      "summary": "Buku yang komprehensif...",
      "similarity_score": 0.82,
      "relevance_score": 0.95
    }
  ]
}
```

### Panduan Integrasi Frontend
Bagi pengembang UI/Frontend:
1. Kunci `answer` murni berisi pesan naratif penyemangat. Anda dapat menampilkan pesan ini di dalam _chat bubble_ pengguna/AI.
2. Kunci `recommendations` adalah sebuah *array of objects*. Jika *array* tidak kosong, lakukan _mapping_ (`.map()`) terhadap data ini untuk menampilkan komponen kartu buku/Katalog Produk. Gunakan parameter `cover_image` sebagai properti `src` untuk label gambar.
3. Nilai `relevance_score` dapat difungsikan sebagai lencana akurasi di setiap sudut kartu.
