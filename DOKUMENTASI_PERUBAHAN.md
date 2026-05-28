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


## 📄 Dokumentasi Perubahan Sistem: Phase 3

### Latar Belakang & Analisis Token Ekonomi
Sebelumnya, sistem membangun konteks _prompt_ dengan melakukan penggabungan string (string concatenation) panjang dari `DEFAULT_SYSTEM_PROMPT` ke setiap pertanyaan kueri baru yang masuk. Pendekatan primitif ini membuat API Gemini terus-menerus memproses ulang muatan prompt instruksional yang sama pada setiap panggilannya, yang menyebabkan beban token _input_ yang boros dan _cost_ API yang melonjak. Selain itu, respons AI (chat) masih dirasa statis dan kurang terstruktur bagi pelajar.
Fase 3 merestrukturisasi Prompt menjadi format penandaan XML (XML tag format), menggunakan caching bawaan dari Google GenAI SDK agar biaya eksekusi jauh lebih ringan, dan memberikan sampel kueri (_Few-Shot Prompting_) terarah agar LLM merespons dengan narasi edukatif, empatik, dan interaktif.

### Spesifikasi Prompting Baru
Sistem prompt dipangkas menjadi blok penanda `<xml>` agar Gemini memproses aturan (guardrails) lebih efisien:
```xml
<role>Asisten Pintar Rumah Literasi Tambaksogra yang sangat ramah, ceria, dan suportif untuk anak sekolah (SD, SMP, SMA).</role>
<allowed_topics>Materi pendidikan, buku pelajaran, ilmu pengetahuan, tips belajar, identitas sistem, dan statistik perpustakaan.</allowed_topics>
<rejection_rule>Jika pertanyaan di luar allowed_topics, jawab: "Maaf ya, teman! Aku dirancang khusus untuk membantu kamu mengeksplorasi buku pelajaran dan ilmu pengetahuan. Yuk, kita kembali bahas buku atau materi sekolah saja! 📚✨"</rejection_rule>
<formatting>JANGAN PERNAH menuliskan ulang daftar metadata buku menggunakan poin-poin kaku (seperti list judul, penulis, halaman). Sebutkan judul buku secara natural dan mengalir di dalam paragraf analisis naratif Anda.</formatting>
```

### Tabel Perbandingan Parameter Runtime

| Parameter | Versi Lama | Versi Baru (Optimal) |
| --- | --- | --- |
| **System Instruction Injection** | Manual String Concatenation (`+`) | SDK Konfigurasi Native (`types.GenerateContentConfig`) |
| **Penyimpanan Instruksi Dasar** | Tidak Ada (Re-computed constantly) | **Context Cache** (`client.caches.create()`) |
| **Siklus Hidup (TTL) Cache** | N/A | **3600 detik (1 Jam)** |
| **Suhu Sampling (Temperature)** | 0.7 | **0.8 (Lebih ekspresif & naratif)** |
| **Gaya Keluaran (Output)** | Konkatenasi Kaku & Fragmen Pendek | **Naratif Elok (3-4 paragraf) + Tips Belajar Interaktif** |

### Struktur Few-Shot Context Array
Pada file `answer_generator.py`, sekarang terdapat konstanta statis global di _module scope_ bernama `FEW_SHOT_EXAMPLES` yang berisi _list of dictionaries_. Struktur ini disisipkan bersama System Prompt saat inisialisasi modul Cache:
```json
[
    {"role": "user", "parts": [{"text": "Saya butuh buku matematika aljabar"}]},
    {"role": "model", "parts": [{"text": "Wah, hebat sekali semangat belajarmu, Sobat Belajar! Aljabar itu seru lho... [Konteks Narasi Panjang yang Menginspirasi] 📚✨"}]}
]
```
Objek `cache_contents` disatukan seperti ini di Python dan di-_upload_ ke server Gemini:
`[{"role": "system", "parts": [{"text": self.system_prompt}]}] + FEW_SHOT_EXAMPLES`

### Panduan Maintenance & Troubleshooting Cache
Proses Caching berpotensi terganggu jika _key_ kedaluwarsa atau terjadi pemadaman koneksi pada Google AI. Script telah dilengkapi penanganan yang _fault-tolerant_:
1. Saat Kelas (`AnswerGenerator`) diinisialisasi, sistem mencoba memanggil `client.caches.create()`.
2. Jika pembuatan Cache Gagal (menghasilkan _Exception_), variabel kelas `self.cache_id = None`.
3. Di dalam logika pemanggilan utama (`_call_gemini`), sistem memvalidasi keberadaan `self.cache_id`. Jika kosong atau pemanggilan cache gagal di tengah eksekusi (seperti Cache telah hangus), sistem otomatis melewati langkah ini (**Graceful Degradation Fallback Path**).
4. Mode _Fallback_ bekerja dengan memanggil konfigurasi klasik API (_raw system instruction_) dan merangkai `FEW_SHOT_EXAMPLES` di bagian atas daftar pesan interaksi secara manual, sehingga RAG selalu beroperasi dengan masa pakai 100%.
