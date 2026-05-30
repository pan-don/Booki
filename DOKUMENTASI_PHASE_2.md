# 📄 Dokumentasi Perubahan Sistem: Phase 2 (Sistem Admin CRUD Data RAG)

## Latar Belakang Arsitektur CRUD Admin
Fase ke-2 bertujuan untuk memfasilitasi panel administratif dalam manajemen data buku. Dikarenakan aplikasi ditenagai oleh mesin pencari RAG (_Retrieval-Augmented Generation_), seluruh injeksi dokumen baru (Add) maupun mutasi data (Update/Delete) harus memengaruhi dua (2) sisi penyimpanan secara paralel:
1. **Source-of-Truth Ledger**: Penyimpanan teks raw (`data/raw/sibi_books.jsonl`).
2. **Vector Stores**: Penyimpanan metrik AI (FAISS - Summary & Fulltext Index).

**Penting:** Seluruh operasi komputasi _embedding_ selama proses injeksi telah diposisikan secara ketat pada **Embedding Pool Manager** (Keys 1-10) untuk mematuhi aturan perlindungan isolasi dari Phase 1 agar sesi chatbot (QA) berjalan stabil tanpa gangguan pembatasan rate limit.

---

## Spesifikasi Kontrak REST API (Endpoint Blueprint Table)

Semua rute berjalan dengan proteksi CORS yang didefinisikan secara global.

| Method | Endpoint Path | Payload Type | Request Payload Structure | Response Payload (Success) |
|---|---|---|---|---|
| `GET` | `/api/admin/books?page=1&limit=20` | Query Params | `?page=X&limit=Y` | HTTP 200: `{"books": [...], "total_books": N, "total_pages": Z, "current_page": X}` |
| `POST` | `/api/admin/add` | Multipart Form | `file` (PDF), `title`, `summary`, `jenjang`, `kelas`, `mata_pelajaran` | HTTP 201: `{"status": "ok", "message": "Book ingested successfully", "book_id": "uuid..."}` |
| `PUT` | `/api/admin/update/<book_id>` | JSON | `{"title": "...", "jenjang": "...", ...}` | HTTP 200: `{"status": "ok", "message": "Book updated successfully", "book_id": "uuid..."}` |
| `DELETE`| `/api/admin/delete/<book_id>` | URL Param | `None` | HTTP 200: `{"status": "ok", "message": "Book deleted successfully", "book_id": "uuid..."}` |

> *Catatan Error:* Server akan merespon dengan `HTTP 400` untuk parameter yang kurang, dan `HTTP 500` apabila terjadi kegagalan injeksi model atau parsing I/O file `jsonl`.

---

## Panduan Integrasi Tim Frontend (Next.js UI Repository 2)

**1. Membaca Grid Layout (Pagination)**
Gunakan parameter `page` dan `limit` untuk memanggil API lalu baca properti `books` untuk iterasi komponen kartu grid 4x5.

```javascript
const fetchBooks = async (page = 1) => {
    // Akan menghasilkan batas data pas untuk grid 4x5 (20 items)
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/books?page=${page}&limit=20`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' } // Pastikan Content-Type disetel sesuai whitelist CORS
    });
    const data = await response.json();
    return data;
};
```

**2. Form Injeksi Buku (Multi-part Upload)**
Karena proses penambahan (`/add`) membutuhkan file PDF sekaligus teks metadata, Anda **wajib** menggunakan object `FormData` dan **TIDAK** mengatur `Content-Type` secara manual pada fetch header (biarkan browser mengatur boundary multipart).

```javascript
const uploadBook = async (file, metadata) => {
    const formData = new FormData();
    formData.append('file', file); // Objek File PDF dari input HTML
    formData.append('title', metadata.title);
    formData.append('summary', metadata.summary);
    formData.append('jenjang', metadata.jenjang);
    formData.append('kelas', metadata.kelas);
    formData.append('mata_pelajaran', metadata.mata_pelajaran);

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/add`, {
        method: 'POST',
        // JANGAN SET HEADER 'Content-Type' DI SINI SAAT MENGGUNAKAN FORMDATA
        body: formData
    });

    return await response.json();
};
```
