# 📄 Dokumentasi Sinkronisasi REST API (Backend - Frontend)

Dokumen ini adalah satu-satunya **Source of Truth** mengenai integrasi pertukaran data (kontrak API) antara sistem Backend Flask (_Hugging Face Spaces_) dan sistem Frontend UI Next.js (_Cloudflare Pages_). Pengembang Frontend diwajibkan menyesuaikan konfigurasi Axios / Fetch API mereka menggunakan metrik spesifikasi skema JSON yang ada di bawah.

---

## 1. Spesifikasi Sistem Jaringan & Keamanan

### Pembatasan Asal-Usul Silang (CORS Protocol)
Backend memberlakukan peraturan _Cross-Origin Resource Sharing_ yang ketat. Permintaan HTTP `OPTIONS` akan dievaluasi untuk mencocokkan asal domain peramban secara absolut dengan varibabel lingkungan yang disetel di server `FRONTEND_URL`.
- **Method yang Diizinkan:** `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`.
- **Headers yang Diizinkan:** `Content-Type`, `Authorization`.

### Decoupled Rendering (UI Data vs Naratif LLM)
Seluruh respons Tanya-Jawab (`/api/recommend` dan `/api/deep`) secara logis dipisahkan antara string `answer` bergaya paragraf ceria yang ditujukan bagi pengguna akhir (pelajar), serta senarai properti JSON `recommendations` (yang diperuntukkan agar UI sanggup melakukan rendering _Bento Grid_ secara mandiri). Hindari mem-parsing metadata kaku langsung dari dalam string teks LLM.

---

## 2. Tabel Pemetaan Kontrak Endpoint

### 🟢 A. Modul Ketersediaan Sistem (Health Check)
Memastikan instance Flask tidak berada dalam posisi tertidur pada cloud hosting atau mengalami malfungsi mesin internal (Crash).

#### **`GET /health`** (atau `/api/health`)
- **Headers Required:** `Content-Type: application/json`
- **Tujuan:** Verifikasi waktu aktif peladen sederhana.
- **Payload Request:** `(None)`

**Responses:**
- **Success (HTTP 200)**:
```json
{
    "status": "healthy",
    "message": "RAG system is running"
}
```

---

### 🔵 B. Modul Komunikasi Chatbot Interaktif (End User)
Pengguna meminta sistem menganalisis RAG berdasarkan pertanyaan pencarian alami yang dikirim, dilengkapi parameter penyaringan secara terpisah.

#### **`POST /api/recommend`**
- **Headers Required:** `Content-Type: application/json`
- **Tujuan:** Analisa kalimat masukan natural pengguna untuk meluncurkan buku rekomendasi terbaik berskor > 0.60.
- **Payload Request:**
```json
{
    "query": "Saya butuh buku matematika yang membahas aljabar",
    "filter_jenjang": "SMA",           // Opsional
    "filter_kelas": "Kelas 10",        // Opsional
    "filter_mapel": "Matematika"       // Opsional
}
```

**Responses:**
- **Success (HTTP 200)**:
```json
{
    "status": "success",
    "query": "Saya butuh buku matematika yang membahas aljabar",
    "answer": "Wah hebat sekali belajarmu hari ini kawan! Coba pelajari buku berikut yang penuh dengan tantangan angka yang asik... 📚✨",
    "recommendations": [
        {
            "book_id": "8f37a5b1c...",
            "title": "Buku Matematika SMA Kurikulum Merdeka",
            "author": "Tim Ahli Kemdikbud",
            "jenjang": "SMA",
            "kelas": "10",
            "mata_pelajaran": "Matematika",
            "summary": "Ini adalah rangkuman dari buku tersebut...",
            "cover_image": "https://url-sampul-cloudflare.com/img.png",
            "similarity_score": 0.89,
            "relevance_score": 0.92
        }
    ]
}
```
- **Kesalahan Validasi (HTTP 400)**:
```json
{"error": "Missing 'query' field"}
```

---

### 🟠 C. Modul Layanan Administratif (Administrator Dashboard CRUD)

Digunakan oleh Administrator Rumah Literasi untuk memanipulasi _Source of Truth_ pada file `sibi_books.jsonl` sekaligus basis vektor pada FAISS secara asinkron.

#### **1. Memanggil Direktori Buku (Catalog Pagination)**
#### **`GET /api/admin/books`**
- **Headers Required:** `Content-Type: application/json`
- **Tujuan:** Menyuplai struktur Layout UI Dashboard 4x5 Grid secara efisien tanpa harus merender seluruh berkas database buku yang berat.
- **Query Params Required:** `page` (Int), `limit` (Int).
- **Contoh Request:** `/api/admin/books?page=1&limit=20`

**Responses (HTTP 200)**:
```json
{
    "books": [
        {
            "book_id": "a92jd8...",
            "judul_buku": "Biologi Dasar",
            "jenjang": "SD",
            ...
        }
    ],
    "current_page": 1,
    "total_books": 200,
    "total_pages": 10
}
```

#### **2. Injeksi Data PDF (Tambah Data)**
#### **`POST /api/admin/add`**
- **Headers Required:** **TIDAK ADA.** (Jangan menyetel Content-Type secara statis. Gunakan object Native `FormData` agar batasan byte (Boundary) dari browser berhasil diurai backend Flask).
- **Tujuan:** Mengekstrak isi PDF panjang, mentransformasi teks, melakukan chunking, meluncurkannya menuju LLM melalui _Embedding Pool Manager_, serta menyimpan hasilnya pada memori RAG.
- **Payload Request (Native FormData JS):**
```javascript
// Contoh Logika Request Tim Frontend
const form = new FormData();
form.append('file', fileObjectFromInput); // PDF Ext
form.append('title', 'Biologi Molekuler Dasar');
form.append('summary', 'Ringkasan kurasi staf...');
form.append('jenjang', 'SMA');
form.append('kelas', 'Kelas 12');
form.append('mata_pelajaran', 'Biologi');

fetch('/api/admin/add', { method: 'POST', body: form });
```

**Responses:**
- **Success (HTTP 201)**:
```json
{
    "status": "ok",
    "message": "Book ingested successfully",
    "book_id": "8f37a5b1c..."
}
```

#### **3. Manipulasi Data Meta (Pembaruan Deskripsi Tanpa Menghancurkan Basis RAG)**
#### **`PUT /api/admin/update/<book_id>`**
- **Headers Required:** `Content-Type: application/json`
- **Tujuan:** Pembaruan komponen deskriptif. Jika `title` atau `summary_text` teridentifikasi termodifikasi di JSON, backend secara aman hanya melakukan proses penyegaran `SummaryVectorStore` tanpa perlu mengulang algoritma penarikan file PDF utuh yang rumit.
- **Payload Request:**
```json
{
    "title": "Biologi Molekuler Dasar Edisi Revisi 2025",
    "jenjang": "SMA"
}
```

**Responses:**
- **Success (HTTP 200)**:
```json
{
    "status": "ok",
    "message": "Book updated successfully",
    "book_id": "<book_id>"
}
```

#### **4. Eliminasi Baris (Penghapusan Total Arsip RAG)**
#### **`DELETE /api/admin/delete/<book_id>`**
- **Headers Required:** `Content-Type: application/json`
- **Tujuan:** Menerjang basis _Source of Truth_ `.jsonl` dan melakukan _Soft Delete_ ke komponen Vektor Store.
- **Payload Request:** `(None)`

**Responses:**
- **Success (HTTP 200)**:
```json
{
    "status": "ok",
    "message": "Book deleted successfully",
    "book_id": "<book_id>"
}
```
