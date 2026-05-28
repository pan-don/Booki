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