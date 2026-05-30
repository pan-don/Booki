# 📄 Dokumentasi Perubahan Sistem: Phase 2 Health-Check (Verifikasi Backend)

Dokumen ini merangkum spesifikasi pengujian otomatis dan konfigurasi infrastruktur pasca-implementasi isolasi beban kerja, khusus untuk memastikan _resilience_ sistem ketika terhubung dengan Frontend Next.js.

## 1. Migrasi Database Full-text
Pada tahap ini, _Full-text Vector Index_ telah diubah menunjuk ke `chunks_index_new.faiss` untuk mengakomodir chunking dokumen 2048-token yang lebih optimal bagi model Jina AI.

> **Catatan Penting:** Backend dirancang untuk memiliki _graceful degradation_. Jika file ini belum disinkronkan secara lokal (ukuran 0 byte), sistem **TIDAK AKAN CRASH** (_Error 500_). Rute administratif tetap akan me-render data melalui `sibi_books.jsonl`.

## 2. Struktur Payload Kontrak Endpoint

### A. Endpoint Health Check
- **Rute:** `GET /health` & `GET /api/health`
- **Tujuan:** Verifikasi uptime dari mesin Flask.
- **Respons Sukses:**
```json
{
  "status": "healthy",
  "message": "RAG system is running"
}
```

### B. Endpoint Rekomendasi (CORS Secured)
- **Rute:** `POST /api/recommend`
- **Tujuan:** Memberikan jawaban naratif chat dan list buku secara terpisah (Decoupled Payload).
- **Respons Sukses:**
```json
{
  "status": "success",
  "query": "...",
  "recommendations": [
    {
      "book_id": "...",
      "title": "...",
      "summary": "...",
      ...
    }
  ],
  "answer": "Halo! Berikut adalah ..."
}
```

## 3. Matriks Pemecahan Masalah (Troubleshooting CORS & Network)

Gunakan tabel ini jika tim Frontend (Next.js) mengalami isu koneksi (Network Blockages) saat melakukan HTTP requests.

| Gejala / Error Browser | Kemungkinan Penyebab | Solusi Tim Frontend |
|-------------------------|----------------------|----------------------|
| **CORS Policy: No 'Access-Control-Allow-Origin'** | Domain _deploy_ Frontend tidak terdaftar di backend `FRONTEND_URL`. | Pastikan `.env` Cloudflare memiliki URL yang sama dengan variabel backend, lalu hubungi DevOps untuk mendaftarkan nama domain baru jika berubah. |
| **Method NOT ALLOWED (405)** | Menggunakan _method_ HTTP selain `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`. | Ubah konfigurasi Axios / Fetch agar sesuai standar kontrak arsitektur di atas. |
| **Failed to fetch (Pre-flight OPTIONS failed)** | Custom header yang dikirim tidak terdapat di dalam whitelist (`Content-Type`, `Authorization`). | Hapus custom headers dari fetch. Saat melakukan upload multipart/form-data, biarkan browser menyetel `Content-Type` secara otomatis. |
| **500 Internal Server Error (Rate Limit)** | _Key pool exhaustion_ (batas API Google Gemini tercapai). | Sistem sudah dilengkapi fitur Auto-Rotation. Jika ini terjadi persisten, artinya seluruh 17 API key dalam sistem telah hangus secara massal (sangat jarang). Hubungi Administrator untuk mengganti array Keys di `config/settings.py`. |
